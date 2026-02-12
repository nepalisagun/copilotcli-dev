"""Tests for ML pipeline and stock predictor."""

import pytest
import numpy as np
import pandas as pd
from io import StringIO

from src.models import StockPredictor, FeatureEngineer, TechnicalIndicators


class TestTechnicalIndicators:
    """Test technical indicator calculations."""

    def test_rsi_calculation(self):
        """Test RSI calculation."""
        prices = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
        rsi = TechnicalIndicators.rsi(prices, period=5)
        
        assert len(rsi) == len(prices)
        assert np.all((rsi >= 0) & (rsi <= 100))
        assert rsi[0] == 50.0  # Before period, should be 50

    def test_macd_calculation(self):
        """Test MACD calculation."""
        prices = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 109] * 3)
        macd, signal, histogram = TechnicalIndicators.macd(prices)
        
        assert len(macd) == len(prices)
        assert len(signal) == len(prices)
        assert len(histogram) == len(prices)

    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation."""
        prices = np.array([100 + i*0.5 for i in range(50)])
        upper, middle, lower = TechnicalIndicators.bollinger_bands(prices, period=20)
        
        assert len(upper) == len(prices)
        assert len(middle) == len(prices)
        assert len(lower) == len(prices)
        # For linear trending data, check that bands form correct relationship for most points
        assert np.mean(upper > middle) > 0.8
        assert np.mean(middle > lower) > 0.8

    def test_volatility_calculation(self):
        """Test volatility calculation."""
        prices = np.array([100, 101, 102, 101, 100, 101, 102, 101, 100, 99] * 2)
        volatility = TechnicalIndicators.volatility(prices, period=10)
        
        assert len(volatility) == len(prices)
        assert np.all(volatility >= 0)


class TestFeatureEngineer:
    """Test feature engineering."""

    def test_create_features(self):
        """Test feature creation from OHLCV data."""
        data = {
            'Open': [100, 101, 102, 103, 104] * 5,
            'High': [102, 103, 104, 105, 106] * 5,
            'Low': [99, 100, 101, 102, 103] * 5,
            'Close': [101, 102, 103, 104, 105] * 5,
            'Volume': [1000000, 1100000, 900000, 1200000, 1050000] * 5,
        }
        df = pd.DataFrame(data)
        
        features = FeatureEngineer.create_features(df)
        
        # Check all features created
        expected_features = [
            'RSI_14', 'MACD', 'MACD_Signal', 'MACD_Histogram',
            'BB_Upper', 'BB_Middle', 'BB_Lower', 'Volatility',
            'HL_Ratio', 'Volume_SMA_20', 'Price_SMA_20'
        ]
        
        for feat in expected_features:
            assert feat in features.columns
        
        assert len(features) == len(df)


class TestStockPredictor:
    """Test StockPredictor class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        np.random.seed(42)
        n_samples = 100
        close_prices = 100 + np.cumsum(np.random.randn(n_samples) * 0.5)
        
        data = {
            'Open': close_prices - np.random.rand(n_samples),
            'High': close_prices + np.random.rand(n_samples),
            'Low': close_prices - np.random.rand(n_samples),
            'Close': close_prices,
            'Volume': np.random.randint(500000, 1500000, n_samples),
        }
        return pd.DataFrame(data)

    def test_initialization(self):
        """Test model initialization."""
        model = StockPredictor()
        
        assert not model.is_trained
        assert len(model.feature_names) == 11
        assert model.pipeline is not None

    def test_model_training(self, sample_data):
        """Test model training."""
        model = StockPredictor()
        features = FeatureEngineer.create_features(sample_data)
        y = features['Close'].values
        
        metrics = model.train(features, y)
        
        assert model.is_trained
        assert 'r2_score' in metrics
        assert 'rmse' in metrics
        assert 'mae' in metrics
        assert metrics['samples'] == len(features)
        assert metrics['features'] == 11

    @pytest.mark.asyncio
    async def test_prediction(self, sample_data):
        """Test prediction."""
        model = StockPredictor()
        features = FeatureEngineer.create_features(sample_data)
        y = features['Close'].values
        
        # Train first
        model.train(features, y)
        
        # Then predict
        test_data = sample_data.iloc[:5]
        predictions = await model.predict(test_data)
        
        assert len(predictions) == len(test_data)
        assert all(isinstance(p, (int, float)) for p in predictions)

    def test_feature_importance(self, sample_data):
        """Test feature importance calculation."""
        model = StockPredictor()
        features = FeatureEngineer.create_features(sample_data)
        y = features['Close'].values
        
        model.train(features, y)
        importance = model.get_feature_importance()
        
        assert isinstance(importance, dict)
        assert len(importance) == 11
        assert all(v > 0 for v in importance.values())

    def test_model_info(self):
        """Test model info retrieval."""
        model = StockPredictor()
        info = model.get_model_info()
        
        assert info['algorithm'] == 'XGBoost'
        assert info['n_estimators'] == 500
        assert 'RSI_14' in info['features']
        assert not info['is_trained']

    @pytest.mark.asyncio
    async def test_prediction_without_training(self, sample_data):
        """Test prediction fails without training."""
        model = StockPredictor()
        
        with pytest.raises(ValueError):
            await model.predict(sample_data)

    @pytest.mark.asyncio
    async def test_prediction_with_missing_columns(self, sample_data):
        """Test prediction with missing required columns."""
        model = StockPredictor()
        features = FeatureEngineer.create_features(sample_data)
        y = features['Close'].values
        
        model.train(features, y)
        
        # Remove required column
        invalid_data = sample_data[['Open', 'High', 'Close', 'Volume']].iloc[:5]
        
        with pytest.raises(ValueError, match="Missing columns"):
            await model.predict(invalid_data)

    @pytest.mark.asyncio
    async def test_prediction_empty_data(self, sample_data):
        """Test prediction with empty data."""
        model = StockPredictor()
        features = FeatureEngineer.create_features(sample_data)
        y = features['Close'].values
        
        model.train(features, y)
        
        empty_data = sample_data.iloc[0:0]
        
        with pytest.raises(ValueError, match="empty"):
            await model.predict(empty_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.models", "--cov-report=term-missing"])
