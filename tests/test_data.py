"""Tests for data loading and feature engineering."""

import pytest
import pandas as pd
import numpy as np
from data.loader import DataLoader
from data.features import FeatureEngineer
from data.eda import EDA


class TestDataLoader:
    """Test data loading functionality."""
    
    def test_loader_initialization(self):
        loader = DataLoader()
        assert loader.stock_data is None
        assert loader.crypto_data is None
    
    def test_get_data_summary(self):
        loader = DataLoader()
        # Create mock data
        dates = pd.date_range('2024-01-01', periods=10)
        data = pd.DataFrame({
            'Close': np.random.rand(10),
            'High': np.random.rand(10),
            'Low': np.random.rand(10),
            'Volume': np.random.randint(100, 1000, 10)
        }, index=dates)
        
        summary = loader.get_data_summary(data)
        assert summary['shape'] == (10, 4)
        assert 'Close' in summary['columns']
        assert summary['date_range'] is not None


class TestFeatureEngineer:
    """Test feature engineering."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=100)
        data = pd.DataFrame({
            'Close': 100 + np.cumsum(np.random.randn(100)),
            'High': 101 + np.cumsum(np.random.randn(100)),
            'Low': 99 + np.cumsum(np.random.randn(100)),
            'Volume': np.random.randint(1000, 5000, 100),
            'Open': 100.5 + np.cumsum(np.random.randn(100))
        }, index=dates)
        return data
    
    def test_technical_indicators(self, sample_data):
        df = FeatureEngineer.calculate_technical_indicators(sample_data)
        
        # Check that new columns were added
        assert 'SMA_5' in df.columns
        assert 'MACD' in df.columns
        assert 'RSI' in df.columns
        assert 'ATR' in df.columns
        
        # Check data integrity
        assert len(df) == len(sample_data)
        assert df['RSI'].min() >= 0 or pd.isna(df['RSI'].min())
        assert df['RSI'].max() <= 100 or pd.isna(df['RSI'].max())
    
    def test_lag_features(self, sample_data):
        df = FeatureEngineer.calculate_technical_indicators(sample_data)
        df = FeatureEngineer.create_lag_features(df)
        
        assert 'Close_Lag_1' in df.columns
        assert 'Close_Lag_5' in df.columns
        assert 'Close_Lag_10' in df.columns
    
    def test_prepare_features(self, sample_data):
        df = FeatureEngineer.calculate_technical_indicators(sample_data)
        df = FeatureEngineer.create_lag_features(df)
        df_clean = df.dropna()
        
        X_train, X_test, y_train, y_test = FeatureEngineer.prepare_features(df)
        
        assert X_train.shape[0] + X_test.shape[0] == len(df_clean)
        assert y_train.shape[0] == X_train.shape[0]
        assert y_test.shape[0] == X_test.shape[0]


class TestEDA:
    """Test exploratory data analysis."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample financial data."""
        dates = pd.date_range('2024-01-01', periods=50)
        data = pd.DataFrame({
            'Close': 100 + np.cumsum(np.random.randn(50) * 0.5),
            'High': 101 + np.cumsum(np.random.randn(50) * 0.5),
            'Low': 99 + np.cumsum(np.random.randn(50) * 0.5),
            'Volume': np.random.randint(1000, 5000, 50),
            'RSI': np.random.uniform(30, 70, 50)
        }, index=dates)
        return data
    
    def test_describe_data(self, sample_data):
        summary = EDA.describe_data(sample_data)
        
        assert summary['shape'] == (50, 5)
        assert 'Close' in summary['columns']
        assert 'numeric_stats' in summary
    
    def test_correlation_analysis(self, sample_data):
        corr = EDA.correlation_analysis(sample_data)
        
        assert 'Close' in corr
        assert -1 <= corr['Close'] <= 1
    
    def test_missing_data_analysis(self, sample_data):
        analysis = EDA.missing_data_analysis(sample_data)
        
        assert 'total_missing' in analysis
        assert 'missing_by_column' in analysis
        assert analysis['total_missing'] >= 0
    
    def test_volatility_analysis(self, sample_data):
        analysis = EDA.volatility_analysis(sample_data)
        
        assert 'daily_volatility' in analysis
        assert 'annual_volatility' in analysis
        assert 'sharpe_ratio' in analysis
        assert analysis['daily_volatility'] >= 0
    
    def test_trend_analysis(self, sample_data):
        analysis = EDA.trend_analysis(sample_data)
        
        assert 'days_above_sma' in analysis
        assert 'current_trend' in analysis
        assert analysis['current_trend'] in ['Uptrend', 'Downtrend']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
