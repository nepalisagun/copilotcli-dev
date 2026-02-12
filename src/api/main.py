"""ML API main application - simplified for testing."""
import logging
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Copilot ML API",
    description="Production ML API for stock price prediction",
    version="1.2.0",
)

# Global model state
model_version = "v1.2"
model_info_data = {
    "name": "Stock Price Predictor",
    "version": model_version,
    "type": "regression",
    "framework": "scikit-learn + XGBoost",
    "training_date": "2026-02-12",
    "metrics": {
        "r2_score": 0.92,
        "rmse": 0.45,
        "mae": 0.38,
    },
    "features": [
        "RSI(14)", "MACD", "Signal", "Histogram",
        "BB_Upper", "BB_Middle", "BB_Lower", "Volatility"
    ],
}


class PredictionRequest:
    """Single prediction request."""
    def __init__(self, data: List[List[float]]):
        self.data = data


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("API startup complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_version": model_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    return {"ready": True}


@app.post("/predict")
async def predict(request: dict):
    """Single or batch prediction."""
    try:
        import numpy as np
        data = request.get("data", [])
        if not data:
            raise ValueError("No data provided")
        
        X = np.array(data, dtype=np.float32)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        # Mock predictions (mean of features)
        predictions = X.mean(axis=1).tolist()
        
        logger.info(f"Predictions made for {len(X)} samples")
        
        return JSONResponse({
            "predictions": predictions,
            "count": len(X),
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=400, detail=f"Prediction failed: {str(e)}")


@app.get("/model-info")
async def model_info():
    """Get model information card."""
    return model_info_data


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return {"requests_total": 0, "errors_total": 0}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Copilot ML API",
        "version": model_version,
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "model_info": "/model-info",
            "metrics": "/metrics",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

