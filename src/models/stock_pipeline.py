"""Production ML pipeline for stock price prediction using XGBoost."""

import logging
from typing import List, Tuple
import asyncio

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators for feature engineering."""

    @staticmethod
    def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index (RSI).
        
        Args:
            prices: Close prices array
            period: RSI period (default 14)
        
        Returns:
            RSI values array
        """
        if len(prices) < period:
            return np.full(len(prices), 50.0)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        rs_values = []
        for i in range(period, len(prices)):
            if i > period:
                avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
            
            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            rs_values.append(rsi)
        
        rsi_array = np.full(len(prices), 50.0)
        rsi_array[period:] = rs_values[:len(prices) - period]
        return rsi_array

    @staticmethod
    def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD, Signal, and Histogram.
        
        Args:
            prices: Close prices array
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line EMA period (default 9)
        
        Returns:
            Tuple of (MACD, Signal, Histogram) arrays
        """
        ema_fast = TechnicalIndicators._ema(prices, fast)
        ema_slow = TechnicalIndicators._ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators._ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(prices: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands.
        
        Args:
            prices: Close prices array
            period: Moving average period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)
        
        Returns:
            Tuple of (Upper, Middle, Lower) bands
        """
        sma = TechnicalIndicators._sma(prices, period)
        std = np.array([np.std(prices[max(0, i-period+1):i+1]) for i in range(len(prices))])
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return upper, sma, lower

    @staticmethod
    def volatility(prices: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate volatility (standard deviation of returns).
        
        Args:
            prices: Close prices array
            period: Lookback period (default 20)
        
        Returns:
            Volatility array
        """
        returns = np.diff(prices) / prices[:-1]
        volatility_arr = np.full(len(prices), 0.02)
        
        for i in range(period, len(prices)):
            volatility_arr[i] = np.std(returns[i-period:i])
        
        return volatility_arr

    @staticmethod
    def _ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        ema = np.zeros(len(prices))
        ema[0] = prices[0]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(prices)):
            ema[i] = prices[i] * multiplier + ema[i - 1] * (1 - multiplier)
        
        return ema

    @staticmethod
    def _sma(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        sma = np.zeros(len(prices))
        for i in range(len(prices)):
            start = max(0, i - period + 1)
            sma[i] = np.mean(prices[start:i+1])
        return sma


class FeatureEngineer:
    """Engineer features from OHLCV data."""

    @staticmethod
    def create_features(ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicator features.
        
        Args:
            ohlcv_data: DataFrame with columns: Open, High, Low, Close, Volume
        
        Returns:
            DataFrame with engineered features
        """
        features = ohlcv_data.copy()
        
        close = features['Close'].values
        high = features['High'].values
        low = features['Low'].values
        volume = features['Volume'].values
        
        # Technical indicators
        features['RSI_14'] = TechnicalIndicators.rsi(close, period=14)
        
        macd, signal, histogram = TechnicalIndicators.macd(close)
        features['MACD'] = macd
        features['MACD_Signal'] = signal
        features['MACD_Histogram'] = histogram
        
        upper, middle, lower = TechnicalIndicators.bollinger_bands(close, period=20)
        features['BB_Upper'] = upper
        features['BB_Middle'] = middle
        features['BB_Lower'] = lower
        
        features['Volatility'] = TechnicalIndicators.volatility(close, period=20)
        
        # Price-based features
        features['HL_Ratio'] = high / (low + 1e-8)
        features['Volume_SMA_20'] = TechnicalIndicators._sma(volume, 20)
        features['Price_SMA_20'] = TechnicalIndicators._sma(close, 20)
        
        return features


class StockPredictor:
    """Production ML pipeline for stock price prediction.
    
    Combines technical indicator preprocessing with XGBoost regression
    for high-accuracy stock price forecasting.
    """

    def __init__(self):
        """Initialize the stock predictor with preprocessing and model."""
        self.feature_names = [
            'RSI_14', 'MACD', 'MACD_Signal', 'MACD_Histogram',
            'BB_Upper', 'BB_Middle', 'BB_Lower', 'Volatility',
            'HL_Ratio', 'Volume_SMA_20', 'Price_SMA_20'
        ]
        
        # Create preprocessing pipeline
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('scaler', StandardScaler(), self.feature_names)
            ],
            remainder='passthrough'
        )
        
        # Create full pipeline
        self.pipeline = Pipeline([
            ('preprocessor', self.preprocessor),
            ('model', XGBRegressor(
                n_estimators=500,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                objective='reg:squarederror'
            ))
        ])
        
        self.is_trained = False
        logger.info("StockPredictor initialized with XGBoost model")

    def train(self, X: pd.DataFrame, y: np.ndarray) -> dict:
        """Train the ML pipeline.
        
        Args:
            X: Feature matrix with technical indicators
            y: Target values (prices to predict)
        
        Returns:
            Dictionary with training metrics
        """
        if X.shape[0] < 50:
            logger.warning(f"Training with only {X.shape[0]} samples (recommended: 100+)")
        
        X_train = X[self.feature_names]
        self.pipeline.fit(X_train, y)
        self.is_trained = True
        
        # Calculate training metrics
        train_score = self.pipeline.score(X_train, y)
        predictions = self.pipeline.predict(X_train)
        rmse = np.sqrt(np.mean((predictions - y) ** 2))
        mae = np.mean(np.abs(predictions - y))
        
        metrics = {
            'r2_score': float(train_score),
            'rmse': float(rmse),
            'mae': float(mae),
            'samples': X.shape[0],
            'features': len(self.feature_names)
        }
        
        logger.info(f"Model trained: R²={train_score:.4f}, RMSE={rmse:.4f}, MAE={mae:.4f}")
        return metrics

    async def predict(self, data: pd.DataFrame) -> List[float]:
        """Predict stock prices (async).
        
        Args:
            data: DataFrame with OHLCV data (Open, High, Low, Close, Volume)
        
        Returns:
            List of predicted prices
        
        Raises:
            ValueError: If model not trained or invalid data
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        if data.shape[0] == 0:
            raise ValueError("Input data is empty")
        
        required_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}
        if not required_cols.issubset(data.columns):
            raise ValueError(f"Missing columns. Required: {required_cols}")
        
        # Run preprocessing in thread pool to avoid blocking
        def _prepare_features():
            features = FeatureEngineer.create_features(data)
            X = features[self.feature_names]
            return X
        
        loop = asyncio.get_event_loop()
        X_processed = await loop.run_in_executor(None, _prepare_features)
        
        # Make predictions
        predictions = self.pipeline.predict(X_processed)
        return predictions.tolist()

    def get_feature_importance(self) -> dict:
        """Get feature importances from trained model.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")
        
        xgb_model = self.pipeline.named_steps['model']
        importances = xgb_model.feature_importances_
        
        feature_importance = {
            name: float(importance)
            for name, importance in zip(self.feature_names, importances)
        }
        
        # Sort by importance
        return dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

    def get_model_info(self) -> dict:
        """Get model metadata.
        
        Returns:
            Dictionary with model information
        """
        xgb_model = self.pipeline.named_steps['model']
        return {
            'name': 'Stock Price Predictor',
            'type': 'regression',
            'algorithm': 'XGBoost',
            'n_estimators': xgb_model.n_estimators,
            'max_depth': xgb_model.max_depth,
            'learning_rate': xgb_model.learning_rate,
            'n_features': len(self.feature_names),
            'features': self.feature_names,
            'is_trained': self.is_trained
        }


# Global model instance
_model_instance = None


def get_model() -> StockPredictor:
    """Get or create the global model instance."""
    global _model_instance
    if _model_instance is None:
        _model_instance = StockPredictor()
    return _model_instance
