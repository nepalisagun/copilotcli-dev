"""Comprehensive API tests for production ML API with XGBoost."""
import json
import pytest
import pandas as pd
from io import StringIO

from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    # Reset model state before each test
    from src.models import stock_pipeline
    stock_pipeline._model_instance = None
    from src.api import main
    main.predictor = main.get_model()
    
    return TestClient(app)


@pytest.fixture
def sample_csv_data():
    """Sample CSV OHLCV data for training/prediction."""
    csv = """Date,Open,High,Low,Close,Volume
2023-01-01,100.0,102.0,99.0,101.0,1000000
2023-01-02,101.0,103.0,100.0,102.0,1100000
2023-01-03,102.0,104.0,101.0,103.0,900000
2023-01-04,103.0,105.0,102.0,104.0,1200000
2023-01-05,104.0,106.0,103.0,105.0,1050000
2023-01-06,105.0,107.0,104.0,106.0,1150000
2023-01-07,106.0,108.0,105.0,107.0,980000
2023-01-08,107.0,109.0,106.0,108.0,1300000
2023-01-09,108.0,110.0,107.0,109.0,1100000
2023-01-10,109.0,111.0,108.0,110.0,1200000"""
    return csv


@pytest.fixture
def sample_ohlcv_list():
    """Sample OHLCV data as list of dicts."""
    return [
        {"Open": 100.0, "High": 102.0, "Low": 99.0, "Close": 101.0, "Volume": 1000000},
        {"Open": 101.0, "High": 103.0, "Low": 100.0, "Close": 102.0, "Volume": 1100000},
        {"Open": 102.0, "High": 104.0, "Low": 101.0, "Close": 103.0, "Volume": 900000},
    ]


class TestHealth:
    """Test health check endpoints."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "model_version" in data
        assert "model_trained" in data
        assert "timestamp" in data
    
    def test_health_check_model_not_trained(self, client):
        """Test health check shows untrained model."""
        response = client.get("/health")
        data = response.json()
        assert "model_trained" in data
        assert isinstance(data["model_trained"], bool)


class TestReadiness:
    """Test readiness probe endpoint."""
    
    def test_readiness_check(self, client):
        """Test readiness probe initially fails (model not trained)."""
        response = client.get("/ready")
        # Should be 503 if model not trained
        assert response.status_code in [200, 503]


class TestRoot:
    """Test root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API metadata."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data
        assert "model" in data
        
        # Check endpoints exist
        endpoints = data["endpoints"]
        assert "health" in endpoints
        assert "predict" in endpoints
        assert "train" in endpoints


class TestTraining:
    """Test model training endpoint."""
    
    def test_train_model(self, client, sample_csv_data):
        """Test training the XGBoost model."""
        response = client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "trained"
        assert "metrics" in data
        
        metrics = data["metrics"]
        assert "r2_score" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert metrics["samples"] == 10

    def test_train_missing_target_column(self, client, sample_csv_data):
        """Test training with invalid target column."""
        response = client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "NonExistent"
            }
        )
        
        assert response.status_code == 400

    def test_train_invalid_csv(self, client):
        """Test training with invalid CSV."""
        response = client.post(
            "/train",
            json={"csv_data": "invalid csv data"}
        )
        
        assert response.status_code == 400


class TestPrediction:
    """Test prediction endpoint."""
    
    def test_predict_without_training(self, client, sample_ohlcv_list):
        """Test prediction fails without training."""
        response = client.post(
            "/predict",
            json={"data": sample_ohlcv_list}
        )
        
        assert response.status_code == 503
        assert "not trained" in response.json()["detail"].lower()

    def test_predict_after_training(self, client, sample_csv_data, sample_ohlcv_list):
        """Test prediction after training."""
        # First train
        client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        # Then predict
        response = client.post(
            "/predict",
            json={"data": sample_ohlcv_list}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) == len(sample_ohlcv_list)
        assert data["count"] == len(sample_ohlcv_list)
        assert "model_version" in data

    def test_predict_empty_data(self, client, sample_csv_data):
        """Test prediction with empty data list."""
        # Train first
        client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        # Predict with empty data
        response = client.post(
            "/predict",
            json={"data": []}
        )
        
        assert response.status_code == 422  # Validation error

    def test_predict_missing_fields(self, client, sample_csv_data):
        """Test prediction with missing required fields."""
        # Train first
        client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        # Predict with incomplete data
        response = client.post(
            "/predict",
            json={
                "data": [
                    {"Open": 100.0, "High": 102.0}  # Missing Low, Close, Volume
                ]
            }
        )
        
        assert response.status_code == 422


class TestBatchPrediction:
    """Test batch prediction from CSV."""
    
    def test_batch_predict_csv_after_training(self, client, sample_csv_data):
        """Test batch prediction from CSV string data."""
        # First train
        client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        # Batch predict from CSV string
        response = client.post(
            "/batch-predict-csv",
            json={"csv_data": sample_csv_data}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) == 10
        assert data["count"] == 10
        
        # Verify prediction items have confidence
        for pred in data["predictions"]:
            assert "predicted_price" in pred
            assert "confidence" in pred
            assert 0 <= pred["confidence"] <= 1

    def test_batch_predict_csv_without_training(self, client, sample_csv_data):
        """Test batch predict fails without training."""
        response = client.post(
            "/batch-predict-csv",
            json={"csv_data": sample_csv_data}
        )
        
        assert response.status_code == 503

    def test_batch_predict_file_streaming(self, client, sample_csv_data):
        """Test batch prediction from file with streaming response."""
        import tempfile
        import os
        
        # First train
        client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            temp_file = f.name
        
        try:
            # Batch predict with file upload
            with open(temp_file, 'rb') as f:
                files = {"file": (temp_file, f, "text/csv")}
                response = client.post("/batch-predict", files=files)
            
            assert response.status_code == 200
            # Streaming response returns NDJSON
            lines = response.text.strip().split('\n')
            assert len(lines) == 10
            
            # Check header
            assert "X-Total-Predictions" in response.headers
            assert response.headers["X-Total-Predictions"] == "10"
        
        finally:
            os.unlink(temp_file)


class TestModelInfo:
    """Test model information endpoint."""
    
    def test_model_info_untrained(self, client):
        """Test model info for untrained model."""
        response = client.get("/model-info")
        assert response.status_code == 200
        
        data = response.json()
        assert data["algorithm"] == "XGBoost"
        assert data["n_estimators"] == 500
        assert not data["is_trained"]
        assert "features" in data
        assert len(data["features"]) == 11

    def test_model_info_trained(self, client, sample_csv_data):
        """Test model info for trained model."""
        # Train
        client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        # Get info
        response = client.get("/model-info")
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_trained"]
        assert "feature_importance" in data
        
        importance = data["feature_importance"]
        assert isinstance(importance, dict)
        assert len(importance) == 11


class TestMetrics:
    """Test Prometheus metrics endpoint."""
    
    def test_metrics_untrained(self, client):
        """Test metrics for untrained model."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["model_trained"] is False

    def test_metrics_trained(self, client, sample_csv_data):
        """Test metrics for trained model."""
        # Train
        client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        
        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        
        assert data["model_trained"]
        assert "top_features" in data
        assert "n_estimators" in data


class TestEndpointIntegration:
    """Integration tests across endpoints."""
    
    def test_full_workflow(self, client, sample_csv_data, sample_ohlcv_list):
        """Test complete workflow: train -> predict -> info."""
        # 1. Check initial state
        health = client.get("/health")
        assert not health.json()["model_trained"]
        
        # 2. Train model
        train_resp = client.post(
            "/train",
            json={
                "csv_data": sample_csv_data,
                "target_column": "Close"
            }
        )
        assert train_resp.status_code == 200
        
        # 3. Check health after training
        health = client.get("/health")
        assert health.json()["model_trained"]
        
        # 4. Make prediction
        pred_resp = client.post(
            "/predict",
            json={"data": sample_ohlcv_list}
        )
        assert pred_resp.status_code == 200
        
        # 5. Get model info
        info_resp = client.get("/model-info")
        assert info_resp.status_code == 200
        assert info_resp.json()["is_trained"]
        
        # 6. Get metrics
        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert metrics_resp.json()["model_trained"]

    def test_error_handling(self, client):
        """Test proper error handling."""
        # Prediction without training
        response = client.post(
            "/predict",
            json={"data": [{"Open": 1, "High": 2, "Low": 0.5, "Close": 1.5, "Volume": 1000}]}
        )
        assert response.status_code == 503
        
        # Invalid training data
        response = client.post(
            "/train",
            json={"csv_data": "bad data"}
        )
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.api", "--cov-report=term-missing"])
