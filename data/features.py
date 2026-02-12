"""Feature engineering for financial time series data."""

import pandas as pd
import numpy as np
from typing import Tuple


class FeatureEngineer:
    """Create technical indicators and features for ML models."""
    
    @staticmethod
    def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators from OHLCV data.
        
        Args:
            df: DataFrame with 'Close', 'High', 'Low', 'Volume' columns
            
        Returns:
            DataFrame with added technical features
        """
        df = df.copy()
        
        # Simple Moving Averages
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # Exponential Moving Average
        df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']
        
        # RSI (Relative Strength Index)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        sma = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = sma + (std * 2)
        df['BB_Lower'] = sma - (std * 2)
        df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
        
        # ATR (Average True Range)
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        # Volume features
        df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        
        # Price features
        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        df['Price_Change'] = df['Close'].diff()
        
        return df
    
    @staticmethod
    def create_lag_features(df: pd.DataFrame, lags: list = [1, 5, 10, 20]) -> pd.DataFrame:
        """Create lagged features for time series."""
        df = df.copy()
        
        for lag in lags:
            df[f'Close_Lag_{lag}'] = df['Close'].shift(lag)
            df[f'Returns_Lag_{lag}'] = df['Returns'].shift(lag)
            df[f'Volume_Lag_{lag}'] = df['Volume'].shift(lag)
        
        return df
    
    @staticmethod
    def prepare_features(df: pd.DataFrame, target_col: str = 'Close', 
                        test_size: float = 0.2) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare features and target for ML model.
        
        Args:
            df: Preprocessed DataFrame
            target_col: Column to predict
            test_size: Proportion of test set
            
        Returns:
            X_train, X_test, y_train, y_test
        """
        # Drop NaN values
        df = df.dropna()
        
        # Select feature columns (exclude date and target)
        feature_cols = [col for col in df.columns if col not in ['Close', 'High', 'Low', 'Open']]
        
        X = df[feature_cols].values
        y = df[target_col].values
        
        # Split data
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test
