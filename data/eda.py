"""EDA module for exploratory data analysis of financial data."""

import pandas as pd
import numpy as np
import json
from typing import Dict, Any


class EDA:
    """Exploratory Data Analysis for financial datasets."""
    
    @staticmethod
    def describe_data(df: pd.DataFrame) -> Dict[str, Any]:
        """Generate descriptive statistics."""
        return {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": df.dtypes.to_dict(),
            "null_count": df.isnull().sum().to_dict(),
            "numeric_stats": df.describe().to_dict(),
            "date_range": f"{df.index.min()} to {df.index.max()}" if hasattr(df.index, 'min') else "N/A"
        }
    
    @staticmethod
    def correlation_analysis(df: pd.DataFrame) -> Dict[str, float]:
        """Calculate correlations with closing price."""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] > 0:
            corr = numeric_df.corr()
            if 'Close' in corr.columns:
                return corr['Close'].sort_values(ascending=False).to_dict()
        return {}
    
    @staticmethod
    def missing_data_analysis(df: pd.DataFrame) -> Dict:
        """Analyze missing data patterns."""
        return {
            "total_missing": int(df.isnull().sum().sum()),
            "missing_by_column": df.isnull().sum().to_dict(),
            "missing_percentage": (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
            "rows_with_missing": int(df.isnull().any(axis=1).sum())
        }
    
    @staticmethod
    def volatility_analysis(df: pd.DataFrame) -> Dict:
        """Analyze price volatility."""
        returns = df['Close'].pct_change()
        return {
            "daily_volatility": float(returns.std()),
            "annual_volatility": float(returns.std() * np.sqrt(252)),
            "mean_return": float(returns.mean()),
            "max_return": float(returns.max()),
            "min_return": float(returns.min()),
            "sharpe_ratio": float((returns.mean() / returns.std()) * np.sqrt(252)) if returns.std() > 0 else 0
        }
    
    @staticmethod
    def trend_analysis(df: pd.DataFrame, window: int = 20) -> Dict:
        """Analyze price trends."""
        sma = df['Close'].rolling(window=window).mean()
        above_sma = (df['Close'] > sma).sum()
        
        return {
            "days_above_sma": int(above_sma),
            "days_below_sma": int((df['Close'] < sma).sum()),
            "sma_crossover_points": int(((df['Close'] > sma).astype(int).diff() != 0).sum()),
            "current_trend": "Uptrend" if df['Close'].iloc[-1] > sma.iloc[-1] else "Downtrend"
        }
