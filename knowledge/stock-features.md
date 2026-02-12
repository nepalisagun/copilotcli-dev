# Stock Market Technical Indicators

## Core Features

### RSI (Relative Strength Index) - Period 14
**Purpose:** Momentum oscillator measuring overbought/oversold conditions
- **Range:** 0-100
- **Overbought:** > 70
- **Oversold:** < 30
- **Formula:** RSI = 100 - (100 / (1 + RS)) where RS = AvgGain / AvgLoss

```python
def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)
    
    for i in range(period, len(prices)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down
        rsi[i] = 100. - 100. / (1. + rs)
    
    return rsi
```

### MACD (Moving Average Convergence Divergence)
**Purpose:** Trend-following momentum indicator
- **MACD Line:** 12-day EMA - 26-day EMA
- **Signal Line:** 9-day EMA of MACD
- **Histogram:** MACD - Signal (divergence)
- **Signals:** Bullish when MACD > Signal, Bearish when MACD < Signal

```python
def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
```

### Bollinger Bands
**Purpose:** Volatility bands around price movement
- **Middle Band:** 20-day Simple Moving Average (SMA)
- **Upper Band:** SMA + (2 × 20-day StdDev)
- **Lower Band:** SMA - (2 × 20-day StdDev)
- **%B:** (Price - Lower) / (Upper - Lower)
- **Squeeze:** When bands are narrow → volatility breakout likely

```python
def calculate_bollinger_bands(prices, period=20, num_std=2):
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    bandwidth = (upper - lower) / sma
    pct_b = (prices - lower) / (upper - lower)
    return upper, sma, lower, bandwidth, pct_b
```

### Volatility (20-day Rolling)
**Purpose:** Price movement intensity
- **Calculation:** 20-day standard deviation of daily log returns
- **High Volatility:** > 2.0% (historically elevated)
- **Low Volatility:** < 0.5% (consolidation pattern)
- **Usage:** Risk assessment, option pricing, stop loss placement

```python
def calculate_volatility(prices, period=20):
    log_returns = np.log(prices / prices.shift(1))
    volatility = log_returns.rolling(period).std() * np.sqrt(252)  # annualized
    return volatility
```

## Feature Engineering Pipeline

### Data Preparation
1. **Load OHLCV Data:** Open, High, Low, Close, Volume
2. **Calculate Returns:** `log_return = ln(Close_t / Close_t-1)`
3. **Normalize Volume:** `Volume / SMA(Volume, 20)`
4. **Handle Missing Data:** Forward fill or remove NaN values

### Feature Matrix
```
Input Features (technical):
- RSI(14)
- MACD Line
- MACD Signal
- MACD Histogram
- Bollinger Upper
- Bollinger Middle (SMA)
- Bollinger Lower
- Bollinger %B
- Bollinger Bandwidth
- Volatility(20)
- Volume (normalized)
- Price (normalized log-scale)

Target Variable:
- Direction (1 = up, 0 = down) for classification
- Price_t+1 for regression
```

### Feature Scaling
```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

## Trading Signals

### Golden Cross (Bullish)
- 50-day SMA crosses above 200-day SMA
- Strong uptrend signal

### Death Cross (Bearish)
- 50-day SMA crosses below 200-day SMA
- Strong downtrend signal

### RSI Divergence
- **Bullish:** Price makes lower low, RSI makes higher low
- **Bearish:** Price makes higher high, RSI makes lower high

### MACD Crossover
- **Buy:** MACD crosses above Signal line
- **Sell:** MACD crosses below Signal line

## Data Quality Checklist

- [ ] No missing OHLCV values
- [ ] Open ≤ High and Low ≤ Close
- [ ] Volume > 0 (exclude zero-volume bars)
- [ ] Dates in ascending order
- [ ] No duplicate timestamps
- [ ] Sufficient history (minimum 100 bars for indicators)

## Production Usage

```python
import pandas as pd
from ta.indicators import rsi, macd, bollinger_bands

# Load data
df = pd.read_csv('stocks-1k.csv')

# Calculate indicators
df['RSI'] = rsi(df['Close'], 14)
df['MACD'], df['Signal'], df['Histogram'] = macd(df['Close'])
df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = bollinger_bands(df['Close'])
df['Volatility'] = df['Close'].pct_change().rolling(20).std() * np.sqrt(252)

# Feature engineering
features = df[['RSI', 'MACD', 'Signal', 'Histogram', 'BB_Upper', 'BB_Mid', 'BB_Lower', 'Volatility']]
features_scaled = StandardScaler().fit_transform(features)

# Model prediction
predictions = model.predict(features_scaled)
```
