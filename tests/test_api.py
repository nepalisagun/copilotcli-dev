"""Tests for API authentication, monitoring, and endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api_main import app
from src.api.auth import TokenManager
from src.api.monitoring import MetricsCollector, HealthChecker, RateLimiter
from datetime import timedelta


client = TestClient(app)


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_token_generation(self):
        """Test token generation."""
        response = client.post("/auth/token", json={
            "username": "demo",
            "password": "demo"
        })
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    def test_invalid_credentials(self):
        """Test invalid credentials."""
        response = client.post("/auth/token", json={
            "username": "wrong",
            "password": "wrong"
        })
        
        assert response.status_code == 401
    
    def test_token_manager(self):
        """Test TokenManager."""
        token = TokenManager.create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=30)
        )
        
        assert token is not None
        payload = TokenManager.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_full_health_check(self):
        """Test full health check."""
        response = client.get("/health/full")
        assert response.status_code == 200
        data = response.json()
        assert "api" in data
        assert "models" in data
        assert "database" in data
    
    def test_status_endpoint(self):
        """Test status endpoint."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["status"] == "operational"


class TestPredictionEndpoints:
    """Test model prediction endpoints."""
    
    def test_predict_requires_auth(self):
        """Test that predict requires authentication."""
        response = client.post("/predict", json={
            "features": [5.1, 3.5, 1.4, 0.2]
        })
        
        assert response.status_code == 403
    
    def test_predict_with_token(self):
        """Test prediction with valid token."""
        token_response = client.post("/auth/token", json={
            "username": "demo",
            "password": "demo"
        })
        token = token_response.json()["access_token"]
        
        response = client.post(
            "/predict",
            json={"features": [5.1, 3.5, 1.4, 0.2]},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "probabilities" in data
        assert 0 <= data["prediction"] <= 2
    
    def test_predict_batch(self):
        """Test batch prediction."""
        token_response = client.post("/auth/token", json={
            "username": "demo",
            "password": "demo"
        })
        token = token_response.json()["access_token"]
        
        response = client.post(
            "/predict/batch",
            json=[
                {"features": [5.1, 3.5, 1.4, 0.2]},
                {"features": [7.5, 3.5, 6.7, 2.5]}
            ],
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert len(response.json()["results"]) == 2


class TestModelEndpoints:
    """Test model information endpoints."""
    
    def test_model_info(self):
        """Test model info endpoint."""
        response = client.get("/model/info")
        assert response.status_code == 200
        data = response.json()
        assert data["model_type"] == "RandomForestClassifier"
        assert data["n_estimators"] == 100
    
    def test_feature_importance(self):
        """Test feature importance endpoint."""
        response = client.get("/model/feature-importance")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert "importance" in data
        assert "top_features" in data


class TestMetricsCollector:
    """Test metrics collection."""
    
    def test_metrics_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()
        assert collector.request_count == 0
        assert collector.error_count == 0
    
    def test_record_request(self):
        """Test recording requests."""
        collector = MetricsCollector()
        collector.record_request("/predict", 200, 0.05)
        
        assert collector.request_count == 1
        assert collector.error_count == 0
    
    def test_error_tracking(self):
        """Test error tracking."""
        collector = MetricsCollector()
        collector.record_request("/predict", 200, 0.05)
        collector.record_request("/predict", 500, 0.1)
        
        assert collector.request_count == 2
        assert collector.error_count == 1
    
    def test_get_metrics(self):
        """Test getting metrics."""
        collector = MetricsCollector()
        collector.record_request("/predict", 200, 0.05)
        collector.record_request("/predict", 200, 0.03)
        
        metrics = collector.get_metrics()
        assert "uptime_seconds" in metrics
        assert metrics["total_requests"] == 2


class TestHealthChecker:
    """Test health checker."""
    
    def test_check_api_health(self):
        """Test API health check."""
        health = HealthChecker.check_api_health()
        assert health["status"] == "healthy"
        assert "timestamp" in health
    
    def test_check_model_service(self):
        """Test model service check."""
        health = HealthChecker.check_model_service()
        assert health["available"] is True
    
    def test_full_health_status(self):
        """Test full health status."""
        health = HealthChecker.get_full_health_status()
        assert "api" in health
        assert "models" in health
        assert "database" in health
        assert health["overall_status"] == "operational"


class TestRateLimiter:
    """Test rate limiter."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_minute=10)
        assert limiter.requests_per_minute == 10
    
    def test_allow_within_limit(self):
        """Test allowing requests within limit."""
        limiter = RateLimiter(requests_per_minute=5)
        
        for _ in range(5):
            assert limiter.is_allowed("client1") is True
    
    def test_deny_over_limit(self):
        """Test denying requests over limit."""
        limiter = RateLimiter(requests_per_minute=2)
        
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is True
        assert limiter.is_allowed("client2") is False
    
    def test_get_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(requests_per_minute=5)
        
        limiter.is_allowed("client3")
        remaining = limiter.get_remaining("client3")
        assert remaining == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
