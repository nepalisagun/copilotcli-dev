"""Production ML API - FastAPI with XGBoost stock prediction."""
import logging
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator

from src.models import get_model, FeatureEngineer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Copilot ML API",
    description="Production ML API for stock price prediction using XGBoost",
    version="2.0.0",
)

# Global model state
model_version = "v2.0"
predictor = get_model()



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


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info(f"API startup: XGBoost model initialized (trained={predictor.is_trained})")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_version": model_version,
        "model_trained": predictor.is_trained,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    if not predictor.is_trained:
        raise HTTPException(status_code=503, detail="Model not trained yet")
    return {"ready": True}


@app.post("/predict")
async def predict(request: PredictionRequest):
    """Single or batch prediction using trained XGBoost model.
    
    Request body:
    {
        "data": [
            {"Open": 100.0, "High": 102.0, "Low": 99.0, "Close": 101.0, "Volume": 1000000},
            ...
        ]
    }
    """
    try:
        if not predictor.is_trained:
            raise HTTPException(status_code=503, detail="Model not trained. Call /train endpoint first.")
        
        # Convert to DataFrame
        df = pd.DataFrame(request.data)
        
        # Get predictions
        predictions = await predictor.predict(df)
        
        logger.info(f"Predictions generated for {len(predictions)} samples")
        
        return JSONResponse({
            "predictions": predictions,
            "count": len(predictions),
            "model_version": model_version,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/batch-predict")
async def batch_predict(request: BatchPredictionRequest):
    """Batch prediction from CSV data.
    
    Request body:
    {
        "csv_data": "Date,Open,High,Low,Close,Volume\\n2023-01-01,100.0,102.0,99.0,101.0,1000000\\n..."
    }
    """
    try:
        if not predictor.is_trained:
            raise HTTPException(status_code=503, detail="Model not trained")
        
        # Parse CSV
        from io import StringIO
        df = pd.read_csv(StringIO(request.csv_data))
        
        # Get predictions
        predictions = await predictor.predict(df)
        
        logger.info(f"Batch predictions for {len(predictions)} samples")
        
        return JSONResponse({
            "predictions": predictions,
            "count": len(predictions),
            "model_version": model_version,
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/train")
async def train(request: TrainingRequest):
    """Train the XGBoost model.
    
    Request body:
    {
        "csv_data": "Date,Open,High,Low,Close,Volume\\n...",
        "target_column": "Close"
    }
    """
    try:
        from io import StringIO
        
        # Parse CSV
        df = pd.read_csv(StringIO(request.csv_data))
        
        if request.target_column not in df.columns:
            raise ValueError(f"Target column '{request.target_column}' not found")
        
        # Create features
        features_df = FeatureEngineer.create_features(df)
        
        # Get target values
        y = features_df[request.target_column].values
        
        # Train model
        metrics = predictor.train(features_df, y)
        
        logger.info(f"Model training complete: {metrics}")
        
        return JSONResponse({
            "status": "trained",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/model-info")
async def model_info():
    """Get detailed model information and feature importance."""
    model_data = predictor.get_model_info()
    
    if predictor.is_trained:
        model_data['feature_importance'] = predictor.get_feature_importance()
    
    return model_data

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if predictor.is_trained:
        feature_importance = predictor.get_feature_importance()
        return {
            "model_trained": True,
            "top_features": list(feature_importance.keys())[:5],
            "n_estimators": predictor.pipeline.named_steps['model'].n_estimators,
        }
    return {"model_trained": False}


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
            "batch_predict": {"path": "/batch-predict", "method": "POST", "description": "Predict from CSV"},
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

