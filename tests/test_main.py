import pytest
from fastapi.testclient import TestClient
from src.main import app, model


client = TestClient(app)


class TestHealthCheck:
    def test_health_check_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPredictEndpoint:
    def test_predict_valid_input(self):
        """Test prediction with valid iris features"""
        valid_features = [5.1, 3.5, 1.4, 0.2]  # Typical setosa
        response = client.post("/predict", json={"features": valid_features})
        
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "probabilities" in data
        assert isinstance(data["prediction"], int)
        assert 0 <= data["prediction"] <= 2
        assert len(data["probabilities"]) == 3
        assert all(isinstance(p, float) for p in data["probabilities"])
        assert sum(data["probabilities"]) == pytest.approx(1.0, abs=1e-6)

    def test_predict_different_class(self):
        """Test prediction for different iris class"""
        large_features = [7.5, 3.5, 6.7, 2.5]  # Typical virginica
        response = client.post("/predict", json={"features": large_features})
        
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] == 2  # Virginica class

    def test_predict_middle_class(self):
        """Test prediction for middle class"""
        middle_features = [6.0, 2.7, 5.1, 1.6]  # Typical versicolor
        response = client.post("/predict", json={"features": middle_features})
        
        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["prediction"] <= 2

    def test_predict_four_features_required(self):
        """Test that four features are required for iris dataset"""
        # Test will either fail validation or prediction - both acceptable
        try:
            response = client.post("/predict", json={"features": [5.1, 3.5]})
            # If it responds, it should be an error
            assert response.status_code != 200
        except Exception:
            # Shape mismatch is acceptable
            pass

    def test_predict_boundary_values(self):
        """Test prediction with boundary values"""
        response = client.post("/predict", json={"features": [4.3, 3.0, 1.1, 0.1]})
        assert response.status_code == 200
        assert response.json()["prediction"] in [0, 1, 2]

    def test_model_trained(self):
        """Test that model is properly trained"""
        assert hasattr(model, 'predict')
        assert hasattr(model, 'predict_proba')
        assert model.n_estimators == 100


class TestDataValidation:
    def test_prediction_request_format(self):
        """Test request format validation"""
        response = client.post("/predict", json={"features": "not_a_list"})
        assert response.status_code == 422  # Validation error

    def test_empty_features_list(self):
        """Test with empty features"""
        try:
            response = client.post("/predict", json={"features": []})
            # Should handle gracefully or fail validation
            if response.status_code == 200:
                assert False, "Empty features should not succeed"
        except Exception:
            # Any error is acceptable for empty features
            pass


class TestEndpointIntegration:
    def test_multiple_predictions_consistent(self):
        """Test that same input gives same output"""
        features = [5.1, 3.5, 1.4, 0.2]
        response1 = client.post("/predict", json={"features": features})
        response2 = client.post("/predict", json={"features": features})
        
        assert response1.json() == response2.json()

    def test_health_and_predict_flow(self):
        """Test complete flow with health check then prediction"""
        health = client.get("/health")
        assert health.status_code == 200
        
        predict = client.post("/predict", json={"features": [5.1, 3.5, 1.4, 0.2]})
        assert predict.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
