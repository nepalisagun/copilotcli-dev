"""Expanded FastAPI application with model serving, auth, and monitoring."""

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
import numpy as np
from datetime import timedelta
from src.api.auth import TokenManager, get_current_user, RoleBasedAccess
from src.api.monitoring import MetricsCollector, HealthChecker, RateLimiter

app = FastAPI(
    title="ML API Service",
    description="Unified API for model serving, data processing, and monitoring",
    version="2.0.0"
)

# Load and train model
iris = load_iris()
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(iris.data, iris.target)

# Initialize monitoring and rate limiting
metrics = MetricsCollector()
rate_limiter = RateLimiter(requests_per_minute=100)


# Request/Response Models
class PredictionRequest(BaseModel):
    features: list[float]


class PredictionResponse(BaseModel):
    prediction: int
    probabilities: list[float]


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class HealthResponse(BaseModel):
    status: str
    version: str


class MetricsResponse(BaseModel):
    uptime_seconds: float
    total_requests: int
    total_errors: int
    error_rate: float
    avg_response_time_ms: float


# Authentication Endpoints
@app.post("/auth/token", response_model=TokenResponse)
def login(credentials: TokenRequest):
    """Generate access token."""
    if credentials.username == "demo" and credentials.password == "demo":
        access_token = TokenManager.create_access_token(
            data={"sub": credentials.username, "role": "user"},
            expires_delta=timedelta(minutes=30)
        )
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


# Health & Status Endpoints
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/health/full")
def full_health_check():
    """Detailed health status."""
    return HealthChecker.get_full_health_status()


@app.get("/metrics")
def get_metrics(current_user: dict = Depends(get_current_user)):
    """Get API metrics (requires authentication)."""
    return metrics.get_metrics()


@app.get("/status")
def get_status():
    """Get API status."""
    return {
        "service": "ML API",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }


# Prediction Endpoints
@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, current_user: dict = Depends(get_current_user)):
    """Predict iris class from features (requires authentication)."""
    features = np.array(request.features).reshape(1, -1)
    prediction = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0].tolist()
    
    return {
        "prediction": int(prediction),
        "probabilities": probabilities
    }


@app.post("/predict/batch")
def predict_batch(requests: list[PredictionRequest], current_user: dict = Depends(get_current_user)):
    """Batch prediction endpoint."""
    results = []
    
    for req in requests:
        features = np.array(req.features).reshape(1, -1)
        prediction = model.predict(features)[0]
        probabilities = model.predict_proba(features)[0].tolist()
        
        results.append({
            "prediction": int(prediction),
            "probabilities": probabilities
        })
    
    return {"results": results}


# Model Information Endpoints
@app.get("/model/info")
def model_info():
    """Get information about the current model."""
    return {
        "model_type": "RandomForestClassifier",
        "n_estimators": model.n_estimators,
        "max_depth": model.max_depth,
        "random_state": model.random_state,
        "classes": [int(c) for c in model.classes_],
        "feature_count": model.n_features_in_
    }


@app.get("/model/feature-importance")
def feature_importance():
    """Get feature importance from the model."""
    importance = model.feature_importances_.tolist()
    feature_names = ['sepal_length', 'sepal_width', 'petal_length', 'petal_width']
    
    return {
        "features": feature_names,
        "importance": importance,
        "top_features": sorted(
            zip(feature_names, importance),
            key=lambda x: x[1],
            reverse=True
        )[:2]
    }


# Admin Endpoints
@app.post("/admin/reset-metrics")
async def reset_metrics(current_user: dict = Depends(get_current_user)):
    """Reset metrics (requires authentication)."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reset metrics"
        )
    
    metrics.reset_metrics()
    return {"status": "metrics reset"}


@app.get("/admin/health-check")
async def admin_health_check(current_user: dict = Depends(get_current_user)):
    """Detailed health check for admins."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    return HealthChecker.get_full_health_status()


# Rate limiting middleware
@app.middleware("http")
async def add_rate_limit_header(request, call_next):
    """Add rate limit headers to responses."""
    client_id = request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_id):
        return __import__('fastapi').responses.JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"}
        )
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(rate_limiter.get_remaining(client_id))
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
