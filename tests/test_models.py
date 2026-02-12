"""Tests for model training and registry."""

import pytest
import numpy as np
import tempfile
import os
from models.trainer import ModelTrainer
from models.registry import ModelRegistry


class TestModelTrainer:
    """Test model training functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        np.random.seed(42)
        X_train = np.random.rand(100, 10)
        y_train = np.sum(X_train[:, :3], axis=1) + np.random.randn(100) * 0.1
        
        X_test = np.random.rand(20, 10)
        y_test = np.sum(X_test[:, :3], axis=1) + np.random.randn(20) * 0.1
        
        return X_train, y_train, X_test, y_test
    
    def test_trainer_initialization(self):
        trainer = ModelTrainer()
        assert len(trainer.models) == 0
        assert trainer.best_model is None
    
    def test_train_linear_model(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, _, _ = sample_data
        
        result = trainer.train_linear_model(X_train, y_train)
        assert 'linear' in trainer.models
        assert result['status'] == 'trained'
    
    def test_train_random_forest(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, _, _ = sample_data
        
        result = trainer.train_random_forest(X_train, y_train)
        assert 'random_forest' in trainer.models
        assert 'feature_importance' in result
    
    def test_train_gradient_boosting(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, _, _ = sample_data
        
        result = trainer.train_gradient_boosting(X_train, y_train)
        assert 'gradient_boosting' in trainer.models
    
    def test_train_xgboost(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, _, _ = sample_data
        
        result = trainer.train_xgboost(X_train, y_train)
        assert 'xgboost' in trainer.models
    
    def test_evaluate_model(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, X_test, y_test = sample_data
        
        trainer.train_linear_model(X_train, y_train)
        metrics = trainer.evaluate_model(trainer.models['linear'], X_test, y_test, 'linear')
        
        assert 'mse' in metrics
        assert 'rmse' in metrics
        assert 'mae' in metrics
        assert 'r2' in metrics
        assert all(v >= 0 for k, v in metrics.items() if k != 'r2')
    
    def test_hyperparameter_tuning(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, _, _ = sample_data
        
        result = trainer.hyperparameter_tuning(X_train, y_train, 'random_forest')
        
        assert 'best_params' in result
        assert 'best_score' in result
        assert 'n_estimators' in result['best_params']
        assert 'max_depth' in result['best_params']
    
    def test_get_best_model(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, X_test, y_test = sample_data
        
        trainer.train_linear_model(X_train, y_train)
        trainer.train_random_forest(X_train, y_train)
        
        best_name, best_model, metrics = trainer.get_best_model(X_test, y_test)
        
        assert best_name is not None
        assert best_model is not None
        assert 'r2' in metrics
    
    def test_save_and_load_model(self, sample_data):
        trainer = ModelTrainer()
        X_train, y_train, _, _ = sample_data
        
        trainer.train_linear_model(X_train, y_train)
        
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            filepath = f.name
        
        try:
            saved = trainer.save_model(trainer.models['linear'], filepath)
            assert saved is True
            assert os.path.exists(filepath)
            
            loaded_model = trainer.load_model(filepath)
            assert loaded_model is not None
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestModelRegistry:
    """Test model registry functionality."""
    
    @pytest.fixture
    def temp_registry_dir(self):
        """Create temporary registry directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_registry_initialization(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        assert os.path.exists(os.path.join(temp_registry_dir, "models"))
    
    def test_register_model(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        
        metrics = {'r2': 0.95, 'mse': 0.05}
        params = {'n_estimators': 100, 'max_depth': 10}
        
        model_id = registry.register_model('price_predictor', 'random_forest', metrics, params)
        
        assert model_id is not None
        assert model_id in registry.metadata
    
    def test_get_model_metadata(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        
        metrics = {'r2': 0.95}
        params = {'n_estimators': 100}
        
        model_id = registry.register_model('test_model', 'xgboost', metrics, params)
        metadata = registry.get_model_metadata(model_id)
        
        assert metadata['name'] == 'test_model'
        assert metadata['type'] == 'xgboost'
    
    def test_list_models(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        
        registry.register_model('model1', 'random_forest', {'r2': 0.90}, {})
        registry.register_model('model2', 'xgboost', {'r2': 0.92}, {})
        
        models = registry.list_models()
        assert len(models) == 2
    
    def test_get_best_model(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        
        registry.register_model('model1', 'random_forest', {'r2': 0.85}, {})
        registry.register_model('model2', 'xgboost', {'r2': 0.95}, {})
        
        best = registry.get_best_model('r2')
        assert best['metrics']['r2'] == 0.95
    
    def test_update_model_status(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        
        model_id = registry.register_model('test_model', 'xgboost', {'r2': 0.90}, {})
        
        success = registry.update_model_status(model_id, 'archived')
        assert success is True
        assert registry.metadata[model_id]['status'] == 'archived'
    
    def test_get_model_history(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        
        registry.register_model('same_model', 'xgboost', {'r2': 0.85}, {}, '1.0.0')
        registry.register_model('same_model', 'xgboost', {'r2': 0.90}, {}, '1.1.0')
        
        history = registry.get_model_history('same_model')
        assert len(history) == 2
    
    def test_registry_stats(self, temp_registry_dir):
        registry = ModelRegistry(temp_registry_dir)
        
        registry.register_model('model1', 'random_forest', {'r2': 0.90}, {})
        registry.register_model('model2', 'xgboost', {'r2': 0.92}, {})
        
        stats = registry.get_registry_stats()
        assert stats['total_models'] == 2
        assert stats['active_models'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
