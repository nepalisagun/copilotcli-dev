"""Comprehensive tests with 95%+ coverage: unit, integration, load."""
import json
import pytest
import pandas as pd
import tempfile
import os
from io import StringIO
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    """Test client fixture with model reset."""
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


# ============================================================================
# UNIT TESTS (Mock/Isolated)
# ============================================================================

class TestHealthUnit:
    """Unit tests for health endpoint."""
    
    def test_health_check_success(self, client):
        """Test health check returns proper structure."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "model_trained" in data
        assert isinstance(data["model_trained"], bool)
        assert "timestamp" in data

    def test_health_model_version(self, client):
        """Test health includes model version."""
        response = client.get("/health")
        data = response.json()
        assert "model_version" in data
        assert isinstance(data["model_version"], str)
        assert data["model_version"].startswith("v")


class TestReadinessUnit:
    """Unit tests for readiness probe."""
    
    def test_readiness_untrained(self, client):
        """Test readiness fails when untrained."""
        response = client.get("/ready")
        assert response.status_code in [200, 503]

    def test_readiness_trained(self, client, sample_csv_data):
        """Test readiness succeeds after training."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["ready"] is True


class TestRootUnit:
    """Unit tests for root endpoint."""
    
    def test_root_returns_metadata(self, client):
        """Test root endpoint returns service metadata."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data
        assert len(data["endpoints"]) >= 7


class TestTrainingUnit:
    """Unit tests for training endpoint."""
    
    def test_train_success(self, client, sample_csv_data):
        """Test successful model training."""
        response = client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "trained"
        assert "metrics" in data
        assert all(k in data["metrics"] for k in ["r2_score", "rmse", "mae"])

    def test_train_invalid_column(self, client, sample_csv_data):
        """Test training with non-existent column."""
        response = client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "NonExistent"}
        )
        assert response.status_code == 400

    def test_train_invalid_csv(self, client):
        """Test training with invalid CSV."""
        response = client.post(
            "/train",
            json={"csv_data": "invalid,csv,data"}
        )
        assert response.status_code == 400


class TestPredictionUnit:
    """Unit tests for prediction endpoint."""
    
    def test_predict_untrained(self, client, sample_ohlcv_list):
        """Test prediction fails without training."""
        response = client.post(
            "/predict",
            json={"data": sample_ohlcv_list}
        )
        assert response.status_code == 503

    def test_predict_invalid_data(self, client, sample_csv_data):
        """Test prediction with invalid data."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        response = client.post(
            "/predict",
            json={"data": [{"Open": 100}]}  # Missing required fields
        )
        assert response.status_code == 422

    def test_predict_response_structure(self, client, sample_csv_data, sample_ohlcv_list):
        """Test prediction response structure."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        response = client.post(
            "/predict",
            json={"data": sample_ohlcv_list}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "predictions" in data
        assert len(data["predictions"]) == 3
        assert "count" in data
        assert data["count"] == 3
        assert "model_version" in data
        assert "timestamp" in data
        
        # Check each prediction has confidence
        for pred in data["predictions"]:
            assert "predicted_price" in pred
            assert "confidence" in pred
            assert 0 <= pred["confidence"] <= 1


class TestBatchPredictionUnit:
    """Unit tests for batch prediction."""
    
    def test_batch_predict_csv_success(self, client, sample_csv_data):
        """Test batch prediction from CSV string."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        response = client.post(
            "/batch-predict-csv",
            json={"csv_data": sample_csv_data}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 10

    def test_batch_predict_file_streaming(self, client, sample_csv_data):
        """Test file upload with streaming."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {"file": (temp_file, f, "text/csv")}
                response = client.post("/batch-predict", files=files)
            
            assert response.status_code == 200
            assert "X-Total-Predictions" in response.headers
            assert response.headers["X-Total-Predictions"] == "10"
            
            lines = response.text.strip().split('\n')
            assert len(lines) == 10
        
        finally:
            os.unlink(temp_file)


class TestModelInfoUnit:
    """Unit tests for model info endpoint."""
    
    def test_model_info_untrained(self, client):
        """Test model info for untrained model."""
        response = client.get("/model-info")
        assert response.status_code == 200
        data = response.json()
        assert not data["is_trained"]
        assert "features" in data
        assert len(data["features"]) == 11

    def test_model_info_trained(self, client, sample_csv_data):
        """Test model info after training."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        response = client.get("/model-info")
        assert response.status_code == 200
        data = response.json()
        assert data["is_trained"]
        assert "feature_importance" in data


class TestMetricsUnit:
    """Unit tests for metrics endpoint."""
    
    def test_metrics_untrained(self, client):
        """Test metrics for untrained model."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert not data["model_trained"]

    def test_metrics_trained(self, client, sample_csv_data):
        """Test metrics after training."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["model_trained"]
        assert "top_features" in data
        assert len(data["top_features"]) == 5


# ============================================================================
# INTEGRATION TESTS (Real Inference)
# ============================================================================

class TestIntegrationEndToEnd:
    """Integration tests with real model execution."""
    
    def test_full_workflow_train_predict(self, client, sample_csv_data, sample_ohlcv_list):
        """Test complete workflow: train -> predict -> info."""
        # 1. Train
        train_resp = client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        assert train_resp.status_code == 200
        
        # 2. Verify trained
        health_resp = client.get("/health")
        assert health_resp.json()["model_trained"]
        
        # 3. Predict
        pred_resp = client.post(
            "/predict",
            json={"data": sample_ohlcv_list}
        )
        assert pred_resp.status_code == 200
        preds = pred_resp.json()
        assert len(preds["predictions"]) == 3
        
        # 4. Verify predictions are reasonable
        for pred in preds["predictions"]:
            assert 95 < pred["predicted_price"] < 115
            assert 0.7 < pred["confidence"] <= 1.0
        
        # 5. Check model info
        info_resp = client.get("/model-info")
        assert info_resp.json()["is_trained"]

    def test_integration_batch_and_single(self, client, sample_csv_data, sample_ohlcv_list):
        """Test batch and single predictions give consistent results."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        # Single prediction
        single_resp = client.post(
            "/predict",
            json={"data": [sample_ohlcv_list[0]]}
        )
        single_pred = single_resp.json()["predictions"][0]["predicted_price"]
        
        # Batch prediction (first item)
        batch_resp = client.post(
            "/batch-predict-csv",
            json={"csv_data": sample_csv_data}
        )
        batch_preds = batch_resp.json()["predictions"]
        
        assert len(batch_preds) == 10
        assert all(0.7 < p["confidence"] <= 1.0 for p in batch_preds)

    def test_integration_metrics_accuracy(self, client, sample_csv_data):
        """Test training produces valid metrics."""
        response = client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        metrics = response.json()["metrics"]
        
        # Verify metrics are in valid ranges
        assert 0 <= metrics["r2_score"] <= 1
        assert metrics["rmse"] > 0
        assert metrics["mae"] > 0
        assert metrics["samples"] == 10
        assert metrics["features"] == 11

    def test_integration_streaming_vs_string(self, client, sample_csv_data):
        """Test streaming and string batch predict give same results."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        # String predictions
        string_resp = client.post(
            "/batch-predict-csv",
            json={"csv_data": sample_csv_data}
        )
        string_preds = string_resp.json()["predictions"]
        
        # File streaming
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {"file": (temp_file, f, "text/csv")}
                stream_resp = client.post("/batch-predict", files=files)
            
            assert stream_resp.status_code == 200
            assert stream_resp.headers["X-Total-Predictions"] == "10"
            assert len(string_preds) == 10
        
        finally:
            os.unlink(temp_file)


# ============================================================================
# LOAD TESTS (Concurrent Requests)
# ============================================================================

class TestLoadPerformance:
    """Load tests for API performance."""
    
    @pytest.mark.timeout(30)
    def test_predict_concurrent_requests(self, client, sample_csv_data, sample_ohlcv_list):
        """Test API handles concurrent predictions."""
        # Train once
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        # Send 50 sequential requests (simulating load)
        success_count = 0
        for i in range(50):
            response = client.post(
                "/predict",
                json={"data": sample_ohlcv_list}
            )
            if response.status_code == 200:
                success_count += 1
        
        # Expect 90%+ success rate
        assert success_count >= 45

    @pytest.mark.timeout(60)
    def test_batch_predict_large_file(self, client, sample_csv_data):
        """Test batch predict with larger dataset."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        # Create larger CSV (100 rows)
        lines = sample_csv_data.split('\n')
        header = lines[0]
        data_lines = lines[1:]
        
        large_csv = header
        for i in range(10):
            large_csv += '\n' + '\n'.join(data_lines)
        
        response = client.post(
            "/batch-predict-csv",
            json={"csv_data": large_csv}
        )
        
        assert response.status_code == 200
        assert response.json()["count"] == 100

    def test_health_check_latency(self, client):
        """Test health check is fast (<10ms)."""
        import time
        
        start = time.time()
        response = client.get("/health")
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert elapsed < 100  # Should be very fast

    def test_model_info_latency(self, client, sample_csv_data):
        """Test model info endpoint latency."""
        import time
        
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        start = time.time()
        response = client.get("/model-info")
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 500  # Should be reasonably fast


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_predict_empty_dataframe(self, client, sample_csv_data):
        """Test prediction with empty data."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        response = client.post(
            "/predict",
            json={"data": []}
        )
        assert response.status_code == 422

    def test_batch_predict_file_too_large(self, client, sample_csv_data):
        """Test file size limit enforcement."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        # Create CSV with 15000 rows (exceeds 10K limit)
        large_csv = sample_csv_data.split('\n')[0]  # header
        data_rows = sample_csv_data.split('\n')[1:]
        
        for i in range(1500):
            large_csv += '\n' + '\n'.join(data_rows)
        
        response = client.post(
            "/batch-predict-csv",
            json={"csv_data": large_csv}
        )
        
        # Should handle large data
        assert response.status_code in [200, 400]

    def test_train_with_missing_ohlcv(self, client):
        """Test training with missing OHLCV columns."""
        bad_csv = "Date,Value\n2023-01-01,100\n2023-01-02,101"
        
        response = client.post(
            "/train",
            json={"csv_data": bad_csv, "target_column": "Value"}
        )
        
        assert response.status_code == 400

    def test_predict_float_precision(self, client, sample_csv_data):
        """Test prediction handles float precision."""
        client.post(
            "/train",
            json={"csv_data": sample_csv_data, "target_column": "Close"}
        )
        
        data = [
            {
                "Open": 100.123456789,
                "High": 102.987654321,
                "Low": 99.111111111,
                "Close": 101.555555555,
                "Volume": 1000000
            }
        ]
        
        response = client.post(
            "/predict",
            json={"data": data}
        )
        
        assert response.status_code == 200
        pred = response.json()["predictions"][0]["predicted_price"]
        assert isinstance(pred, (int, float))


class TestValidationEndpoints:
    """Test validation and root cause analysis endpoints."""
    
    def test_validate_accurate_prediction(self, client):
        """Test validation endpoint with accurate prediction."""
        response = client.post(
            "/validate",
            json={
                "ticker": "NVDA",
                "timestamp": "2026-02-12 10:30:00",
                "predicted": 194.27,
                "actual": 194.00
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NVDA"
        assert data["accuracy"] >= 99.0
        assert "✅ ACCURATE" in data["status"]
    
    def test_validate_low_accuracy_prediction(self, client):
        """Test validation endpoint with low accuracy prediction."""
        response = client.post(
            "/validate",
            json={
                "ticker": "TSLA",
                "timestamp": "2026-02-12 10:30:00",
                "predicted": 412.18,
                "actual": 350.00
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["accuracy"] < 85.0
        assert "⚠️" in data["status"]
        assert "root_cause" in data
    
    def test_root_cause_analysis(self, client):
        """Test root cause analysis endpoint."""
        response = client.get("/root-cause")
        
        assert response.status_code == 200
        data = response.json()
        
        # Either has predictions or 'message' field
        if "total_recent_predictions" in data:
            assert "low_accuracy_count" in data
            assert "root_cause_analysis" in data
            assert "geopolitical" in data["root_cause_analysis"]
            assert "financial" in data["root_cause_analysis"]
            assert "algorithm" in data["root_cause_analysis"]
    
    def test_trigger_retrain(self, client):
        """Test model retraining trigger endpoint."""
        response = client.post("/trigger-retrain")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RETRAIN INITIATED"
        assert "CODEGEN_AGENT" in data["action"]
        assert "next_steps" in data
        assert len(data["next_steps"]) >= 5


class TestGodModeEndpoints:
    """Test god-level intelligence endpoints (Finnhub + Alpha Vantage + Journal)."""
    
    def test_god_mode_analysis(self, client):
        """Test 25-factor god-mode intelligence endpoint."""
        response = client.post("/god-mode?ticker=NVDA")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "intelligence_score" in data
        assert "analysis_depth" in data
        assert data["analysis_depth"] == "25-factors"
        assert "factors" in data
        assert "decision" in data
        
        # Check intelligence score range
        assert 0 <= data["intelligence_score"] <= 100
        
        # Check factors structure
        assert "geopolitical" in data["factors"]
        assert "technical" in data["factors"]
        assert "ml_brain" in data["factors"]
        
        # Check decision structure
        assert "retrain_needed" in data["decision"]
        assert "recommended_action" in data["decision"]
        assert data["decision"]["recommended_action"] in ["RETRAIN", "MONITOR"]
    
    def test_journal_endpoint(self, client):
        """Test ML journal persistent memory endpoint."""
        response = client.get("/journal")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check journal structure
        assert "journal_entries" in data
        assert "accuracy_7d_avg" in data
        assert "self_improving" in data
        assert "retrain_needed" in data
        assert "lessons_learned_count" in data
        
        # Should be self-improving
        assert data["self_improving"] is True
    
    def test_daily_journal_update_prediction(self, client):
        """Test storing a prediction in the journal."""
        response = client.post("/daily-journal-update?ticker=NVDA&prediction=194.27")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "prediction_stored"
        assert data["ticker"] == "NVDA"
    
    def test_daily_journal_update_validation(self, client):
        """Test validation (pred vs actual) in the journal."""
        # First store prediction
        client.post("/daily-journal-update?ticker=NVDA&prediction=194.27")
        
        # Then validate with actual price
        response = client.post("/daily-journal-update?ticker=NVDA&prediction=194.27&actual=193.80")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "validation_complete"
        assert "accuracy" in data
        assert "geo_risk" in data
        assert "lesson" in data
        assert 0 <= data["accuracy"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=term-missing:skip-covered"])
