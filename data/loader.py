"""Data loading module for stocks and cryptocurrency data."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Tuple, Dict, List


class DataLoader:
    """Load and preprocess financial market data."""
    
    def __init__(self):
        self.stock_data = None
        self.crypto_data = None
        
    def load_stock_data(self, symbols: List[str], period: str = "1y") -> pd.DataFrame:
        """
        Load stock data from Yahoo Finance.
        
        Args:
            symbols: List of stock ticker symbols (e.g., ['AAPL', 'MSFT'])
            period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', etc.)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            data = yf.download(symbols, period=period, progress=False)
            self.stock_data = data
            return data
        except Exception as e:
            raise ValueError(f"Error loading stock data: {e}")
    
    def load_crypto_data(self, symbols: List[str], period: str = "1y") -> pd.DataFrame:
        """
        Load cryptocurrency data from Yahoo Finance.
        
        Args:
            symbols: List of crypto symbols (e.g., ['BTC-USD', 'ETH-USD'])
            period: Time period
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            data = yf.download(symbols, period=period, progress=False)
            self.crypto_data = data
            return data
        except Exception as e:
            raise ValueError(f"Error loading crypto data: {e}")
    
    def get_data_summary(self, data: pd.DataFrame) -> Dict:
        """Get summary statistics of the data."""
        return {
            "shape": data.shape,
            "columns": list(data.columns),
            "date_range": f"{data.index.min()} to {data.index.max()}",
            "missing_values": data.isnull().sum().to_dict(),
            "data_types": data.dtypes.to_dict()
        }
