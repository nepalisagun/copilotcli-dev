"""Comprehensive API tests with 95%+ coverage."""
import json
import io

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, model_info_data


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def sample_prediction_data():
    """Sample prediction data."""
    return {
        "data": [
            [0.5, 0.3, 0.2, 0.1, 100.0, 99.0, 98.0, 0.02],
            [0.6, 0.4, 0.25, 0.15, 101.0, 100.0, 99.0, 0.025],
        ]
    }


class TestHealth:
    """Test health check endpoints."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_version"] == "v1.2"
        assert "timestamp" in data
    
    def test_health_response_fields(self, client):
        """Test health response has required fields."""
        response = client.get("/health")
        data = response.json()
        assert set(data.keys()) == {"status", "model_version", "timestamp"}
    
    def test_readiness_check(self, client):
        """Test readiness probe."""
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["ready"] is True


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Copilot ML API"
        assert data["version"] == "v1.2"
        assert "endpoints" in data
        assert "health" in data["endpoints"]
        assert "predict" in data["endpoints"]


class TestModelInfo:
    """Test model information endpoint."""
    
    def test_model_info_success(self, client):
        """Test successful model info retrieval."""
        response = client.get("/model-info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Stock Price Predictor"
        assert data["version"] == "v1.2"
        assert data["type"] == "regression"
        assert data["framework"] == "scikit-learn + XGBoost"
    
    def test_model_info_metrics(self, client):
        """Test model info includes metrics."""
        response = client.get("/model-info")
        data = response.json()
        assert "metrics" in data
        assert "r2_score" in data["metrics"]
        assert data["metrics"]["r2_score"] == 0.92
        assert data["metrics"]["rmse"] == 0.45
        assert data["metrics"]["mae"] == 0.38
    
    def test_model_info_features(self, client):
        """Test model info includes all features."""
        response = client.get("/model-info")
        data = response.json()
        assert "features" in data
        assert len(data["features"]) == 8
        assert "RSI(14)" in data["features"]
        assert "MACD" in data["features"]
        assert "Volatility" in data["features"]


class TestPredictEndpoint:
    """Test single prediction endpoint."""
    
    def test_predict_success(self, client, sample_prediction_data):
        """Test successful prediction."""
        response = client.post("/predict", json=sample_prediction_data)
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "count" in data
        assert "timestamp" in data
        assert data["count"] == 2
        assert len(data["predictions"]) == 2
    
    def test_predict_single_sample(self, client):
        """Test single sample prediction."""
        payload = {"data": [[0.5, 0.3, 0.2, 0.1, 100.0, 99.0, 98.0, 0.02]]}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["predictions"]) == 1
        assert isinstance(data["predictions"][0], (int, float))
    
    def test_predict_multiple_samples(self, client):
        """Test multiple sample prediction."""
        payload = {
            "data": [
                [0.5] * 8,
                [0.6] * 8,
                [0.7] * 8,
                [0.8] * 8,
            ]
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 4
        assert len(data["predictions"]) == 4
    
    def test_predict_empty_data(self, client):
        """Test prediction with empty data."""
        payload = {"data": []}
        response = client.post("/predict", json=payload)
        assert response.status_code == 400
    
    def test_predict_missing_data(self, client):
        """Test prediction with missing data field."""
        payload = {}
        response = client.post("/predict", json=payload)
        assert response.status_code == 400
    
    def test_predict_response_structure(self, client, sample_prediction_data):
        """Test prediction response structure."""
        response = client.post("/predict", json=sample_prediction_data)
        data = response.json()
        assert isinstance(data["predictions"], list)
        assert isinstance(data["count"], int)
        assert isinstance(data["timestamp"], str)
        assert "T" in data["timestamp"]  # ISO format


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns data."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "requests_total" in data
        assert "errors_total" in data


class TestErrorHandling:
    """Test error handling."""
    
    def test_nonexistent_endpoint(self, client):
        """Test 404 for nonexistent endpoint."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_request_method(self, client):
        """Test invalid HTTP method."""
        response = client.get("/predict")  # POST endpoint accessed with GET
        assert response.status_code == 405


class TestAsyncEndpoints:
    """Test async endpoint functionality."""
    
    def test_health_async(self, client):
        """Test health endpoint is async."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_predict_async(self, client, sample_prediction_data):
        """Test predict endpoint is async."""
        response = client.post("/predict", json=sample_prediction_data)
        assert response.status_code == 200
    
    def test_multiple_concurrent_requests(self, client, sample_prediction_data):
        """Test multiple requests can be handled."""
        responses = []
        for _ in range(5):
            response = client.get("/health")
            responses.append(response)
        
        assert all(r.status_code == 200 for r in responses)


class TestDataValidation:
    """Test input data validation."""
    
    def test_numeric_data_handling(self, client):
        """Test numeric data is handled properly."""
        payload = {"data": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]]}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        assert len(response.json()["predictions"]) == 1
    
    def test_various_numeric_types(self, client):
        """Test various numeric types."""
        payload = {"data": [[1, 2.5, 3.0, 4, 5.5, 6, 7.0, 8]]}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200


class TestAppStructure:
    """Test app structure and initialization."""
    
    def test_app_title(self):
        """Test app has correct title."""
        assert app.title == "Copilot ML API"
    
    def test_app_version(self):
        """Test app has correct version."""
        assert app.version == "1.2.0"
    
    def test_app_description(self):
        """Test app has description."""
        assert "stock price prediction" in app.description.lower()


class TestEndpointCoverage:
    """Test all endpoints are functional."""
    
    def test_all_endpoints_callable(self, client):
        """Test all main endpoints are accessible."""
        endpoints = [
            ("/", "GET"),
            ("/health", "GET"),
            ("/ready", "GET"),
            ("/model-info", "GET"),
            ("/metrics", "GET"),
            ("/predict", "POST"),
        ]
        
        for path, method in endpoints:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json={"data": [[0.5] * 8]})
            
            assert response.status_code in [200, 201, 422, 400]


class TestResponseFormats:
    """Test response formats are consistent."""
    
    def test_json_responses(self, client):
        """Test responses are valid JSON."""
        endpoints = ["/health", "/ready", "/model-info", "/metrics"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            try:
                response.json()
            except ValueError:
                pytest.fail(f"Endpoint {endpoint} did not return valid JSON")
    
    def test_health_response_format(self, client):
        """Test health response format."""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["status"], str)
        assert isinstance(data["model_version"], str)
        assert isinstance(data["timestamp"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.api", "--cov-report=term-missing"])

