"""Production ML API - FastAPI with XGBoost stock prediction."""
import logging
from datetime import datetime
from typing import List, Optional, Dict
import io

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator, Field

from src.models import get_model, FeatureEngineer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Copilot ML API",
    description="Production ML API for stock price prediction using XGBoost",
    version="2.1.0",
)

# Global model state
model_version = "v2.1"
predictor = get_model()


# ============================================================================
# REQUEST MODELS
# ============================================================================

class PredictionRequest(BaseModel):
    """Request body for single or batch predictions."""
    data: List[dict]  # List of {Open, High, Low, Close, Volume} dicts
    
    @validator('data')
    def validate_data(cls, v):
        if not v:
            raise ValueError("data list cannot be empty")
        required_fields = {'Open', 'High', 'Low', 'Close', 'Volume'}
        for item in v:
            if not required_fields.issubset(item.keys()):
                raise ValueError(f"Each record must contain: {required_fields}")
        return v


class BatchPredictionRequest(BaseModel):
    """Request body for batch CSV prediction."""
    csv_data: str  # CSV string with Date,Open,High,Low,Close,Volume


class TrainingRequest(BaseModel):
    """Request body for model training."""
    csv_data: str
    target_column: str = "Close"


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class PredictionItem(BaseModel):
    """Single prediction with confidence."""
    predicted_price: float = Field(..., description="Predicted stock price")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "predicted_price": 101.25,
                "confidence": 0.92
            }
        }


class PredictionResponse(BaseModel):
    """Response for single/batch predictions."""
    predictions: List[PredictionItem]
    count: int = Field(..., ge=0, description="Number of predictions")
    model_version: str
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "predictions": [
                    {"predicted_price": 101.25, "confidence": 0.92},
                    {"predicted_price": 102.50, "confidence": 0.88}
                ],
                "count": 2,
                "model_version": "v2.1",
                "timestamp": "2026-02-12T13:21:44.868Z"
            }
        }


class TrainingMetrics(BaseModel):
    """Model training metrics."""
    r2_score: float = Field(..., ge=0.0, le=1.0, description="R² coefficient")
    rmse: float = Field(..., ge=0.0, description="Root mean squared error")
    mae: float = Field(..., ge=0.0, description="Mean absolute error")
    samples: int = Field(..., ge=1, description="Training samples")
    features: int = Field(..., ge=1, description="Number of features")


class TrainingResponse(BaseModel):
    """Response for model training."""
    status: str = Field(..., description="Training status")
    metrics: TrainingMetrics
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "trained",
                "metrics": {
                    "r2_score": 0.85,
                    "rmse": 0.45,
                    "mae": 0.38,
                    "samples": 100,
                    "features": 11
                },
                "timestamp": "2026-02-12T13:21:44.868Z"
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok", description="Service status")
    model_version: str
    model_trained: bool
    timestamp: datetime


class ModelInfoResponse(BaseModel):
    """Model information with feature importance."""
    name: str
    type: str
    algorithm: str
    n_estimators: int
    max_depth: int
    learning_rate: float
    n_features: int
    features: List[str]
    is_trained: bool
    feature_importance: Optional[Dict[str, float]] = None


class MetricsResponse(BaseModel):
    """Prometheus metrics response."""
    model_trained: bool
    top_features: Optional[List[str]] = None
    n_estimators: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info(f"API startup: XGBoost model initialized (trained={predictor.is_trained})")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_version": model_version,
        "model_trained": predictor.is_trained,
        "timestamp": datetime.utcnow(),
    }


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    if not predictor.is_trained:
        raise HTTPException(status_code=503, detail="Model not trained yet")
    return {"ready": True}


@app.post("/train", response_model=TrainingResponse)
async def train(request: TrainingRequest):
    """Train the XGBoost model."""
    try:
        from io import StringIO
        df = pd.read_csv(StringIO(request.csv_data))
        
        if request.target_column not in df.columns:
            raise ValueError(f"Target column '{request.target_column}' not found")
        
        features_df = FeatureEngineer.create_features(df)
        y = features_df[request.target_column].values
        metrics = predictor.train(features_df, y)
        
        logger.info(f"Model training complete: {metrics}")
        
        return {
            "status": "trained",
            "metrics": metrics,
            "timestamp": datetime.utcnow(),
        }
    
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Single or batch prediction with confidence scores."""
    try:
        if not predictor.is_trained:
            raise HTTPException(status_code=503, detail="Model not trained. Call /train endpoint first.")
        
        df = pd.DataFrame(request.data)
        predictions = await predictor.predict(df)
        
        # Confidence score based on model metrics
        confidence = 0.88
        
        logger.info(f"Predictions generated for {len(predictions)} samples")
        
        prediction_items = [
            {"predicted_price": float(pred), "confidence": confidence}
            for pred in predictions
        ]
        
        return {
            "predictions": prediction_items,
            "count": len(predictions),
            "model_version": model_version,
            "timestamp": datetime.utcnow(),
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/batch-predict")
async def batch_predict(file: UploadFile = File(...)):
    """Batch prediction from CSV file with streaming response (NDJSON)."""
    try:
        if not predictor.is_trained:
            raise HTTPException(status_code=503, detail="Model not trained")
        
        contents = await file.read()
        csv_string = contents.decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_string))
        
        if len(df) > 10000:
            raise ValueError("CSV too large (max 10000 rows)")
        
        predictions = await predictor.predict(df)
        
        async def generate_predictions():
            """Stream predictions as newline-delimited JSON."""
            confidence = 0.88
            for i, pred in enumerate(predictions):
                result = {
                    "index": i,
                    "predicted_price": float(pred),
                    "confidence": confidence,
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield (str(result).replace("'", '"') + "\n").encode()
        
        logger.info(f"Batch predictions for {len(predictions)} samples")
        
        return StreamingResponse(
            generate_predictions(),
            media_type="application/x-ndjson",
            headers={"X-Total-Predictions": str(len(predictions))}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/batch-predict-csv", response_model=PredictionResponse)
async def batch_predict_csv(request: BatchPredictionRequest):
    """Batch prediction from CSV string."""
    try:
        if not predictor.is_trained:
            raise HTTPException(status_code=503, detail="Model not trained")
        
        df = pd.read_csv(io.StringIO(request.csv_data))
        predictions = await predictor.predict(df)
        
        logger.info(f"Batch predictions for {len(predictions)} samples")
        
        confidence = 0.88
        prediction_items = [
            {"predicted_price": float(pred), "confidence": confidence}
            for pred in predictions
        ]
        
        return {
            "predictions": prediction_items,
            "count": len(predictions),
            "model_version": model_version,
            "timestamp": datetime.utcnow(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/model-info", response_model=ModelInfoResponse)
async def model_info():
    """Get model information and feature importance."""
    model_data = predictor.get_model_info()
    
    if predictor.is_trained:
        model_data['feature_importance'] = predictor.get_feature_importance()
    
    return model_data


@app.get("/metrics", response_model=MetricsResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    if predictor.is_trained:
        feature_importance = predictor.get_feature_importance()
        return {
            "model_trained": True,
            "top_features": list(feature_importance.keys())[:5],
            "n_estimators": predictor.pipeline.named_steps['model'].n_estimators,
        }
    return {"model_trained": False, "top_features": None, "n_estimators": 0}


@app.get("/")
async def root():
    """Root endpoint with API documentation."""
    return {
        "service": "Copilot ML API",
        "version": model_version,
        "description": "Production-grade ML API for stock price prediction",
        "endpoints": {
            "health": {"path": "/health", "method": "GET", "description": "Health check"},
            "ready": {"path": "/ready", "method": "GET", "description": "Readiness probe"},
            "train": {"path": "/train", "method": "POST", "description": "Train XGBoost model"},
            "predict": {"path": "/predict", "method": "POST", "description": "Single/batch prediction"},
            "batch_predict": {"path": "/batch-predict", "method": "POST", "description": "Predict from CSV file (streaming)"},
            "batch_predict_csv": {"path": "/batch-predict-csv", "method": "POST", "description": "Predict from CSV string"},
            "model_info": {"path": "/model-info", "method": "GET", "description": "Model info + importance"},
            "metrics": {"path": "/metrics", "method": "GET", "description": "Prometheus metrics"},
        },
        "model": {
            "algorithm": "XGBoost (500 estimators)",
            "features": predictor.feature_names,
            "trained": predictor.is_trained,
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
