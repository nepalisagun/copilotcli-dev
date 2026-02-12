"""Model training and hyperparameter tuning."""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import GridSearchCV
import joblib
import json
from typing import Dict, Any, Tuple
from datetime import datetime


class ModelTrainer:
    """Train and optimize ML models for price prediction."""
    
    def __init__(self):
        self.models = {}
        self.best_model = None
        self.training_history = {}
    
    def train_linear_model(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict[str, float]:
        """Train linear regression model."""
        model = LinearRegression()
        model.fit(X_train, y_train)
        self.models['linear'] = model
        return {'status': 'trained'}
    
    def train_random_forest(self, X_train: np.ndarray, y_train: np.ndarray,
                           n_estimators: int = 100, max_depth: int = 10) -> Dict[str, Any]:
        """Train random forest regressor."""
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        self.models['random_forest'] = model
        return {
            'status': 'trained',
            'feature_importance': model.feature_importances_.tolist()
        }
    
    def train_gradient_boosting(self, X_train: np.ndarray, y_train: np.ndarray,
                               n_estimators: int = 100, learning_rate: float = 0.1) -> Dict:
        """Train gradient boosting regressor."""
        model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            random_state=42
        )
        model.fit(X_train, y_train)
        self.models['gradient_boosting'] = model
        return {'status': 'trained'}
    
    def train_xgboost(self, X_train: np.ndarray, y_train: np.ndarray,
                     n_estimators: int = 100, learning_rate: float = 0.1) -> Dict:
        """Train XGBoost model."""
        model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        self.models['xgboost'] = model
        return {'status': 'trained'}
    
    def hyperparameter_tuning(self, X_train: np.ndarray, y_train: np.ndarray,
                             model_type: str = 'random_forest') -> Dict[str, Any]:
        """Perform hyperparameter tuning using GridSearch."""
        
        param_grids = {
            'random_forest': {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15],
                'min_samples_split': [2, 5]
            },
            'xgboost': {
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.1, 0.3],
                'max_depth': [3, 5, 7]
            },
            'gradient_boosting': {
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.1, 0.3],
                'max_depth': [3, 5, 7]
            }
        }
        
        if model_type == 'random_forest':
            base_model = RandomForestRegressor(random_state=42, n_jobs=-1)
        elif model_type == 'xgboost':
            base_model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
        else:
            base_model = GradientBoostingRegressor(random_state=42)
        
        grid_search = GridSearchCV(
            base_model,
            param_grids[model_type],
            cv=3,
            n_jobs=-1,
            verbose=0
        )
        
        grid_search.fit(X_train, y_train)
        
        self.models[f'{model_type}_tuned'] = grid_search.best_estimator_
        
        return {
            'best_params': grid_search.best_params_,
            'best_score': grid_search.best_score_,
            'cv_results': {
                'mean_test_score': grid_search.cv_results_['mean_test_score'].tolist(),
                'std_test_score': grid_search.cv_results_['std_test_score'].tolist()
            }
        }
    
    def evaluate_model(self, model, X_test: np.ndarray, y_test: np.ndarray,
                      model_name: str = 'model') -> Dict[str, float]:
        """Evaluate model performance."""
        y_pred = model.predict(X_test)
        
        metrics = {
            'mse': float(mean_squared_error(y_test, y_pred)),
            'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred))),
            'mae': float(mean_absolute_error(y_test, y_pred)),
            'r2': float(r2_score(y_test, y_pred)),
            'mape': float(np.mean(np.abs((y_test - y_pred) / y_test))) if (y_test != 0).all() else 0
        }
        
        self.training_history[model_name] = metrics
        return metrics
    
    def get_best_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Tuple[str, Any, Dict]:
        """Find and return the best performing model."""
        best_r2 = -float('inf')
        best_name = None
        best_model_obj = None
        
        for name, model in self.models.items():
            r2 = self.evaluate_model(model, X_test, y_test, name)['r2']
            if r2 > best_r2:
                best_r2 = r2
                best_name = name
                best_model_obj = model
        
        self.best_model = best_model_obj
        return best_name, best_model_obj, self.training_history.get(best_name, {})
    
    def save_model(self, model, filepath: str) -> bool:
        """Save model to disk."""
        try:
            joblib.dump(model, filepath)
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def load_model(self, filepath: str):
        """Load model from disk."""
        try:
            return joblib.load(filepath)
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
