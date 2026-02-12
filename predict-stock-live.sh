#!/bin/bash
# Real-time Stock Price Predictor
# Fetches LIVE OHLCV data from ANY ticker and predicts price
# Zero API keys required (uses free yfinance library)
#
# Usage:
#   ./predict-stock-live.sh NVDA        # Single prediction
#   ./predict-stock-live.sh NVDA --watch  # Refresh every 60s
#   ./predict-stock-live.sh AAPL TSLA GOOG  # Multiple tickers

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
LOG_FILE="${LOG_FILE:-predictions.log}"
WATCH_MODE=false
REFRESH_INTERVAL=60

# Parse arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}✗ ERROR: Stock ticker required${NC}"
    echo -e "${CYAN}Usage: $0 TICKER [--watch]${NC}"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 NVDA              # Single prediction"
    echo "  $0 NVDA --watch      # Refresh every 60s"
    echo "  $0 AAPL TSLA GOOG   # Multiple tickers"
    exit 1
fi

# Extract ticker and check for --watch flag
TICKERS=()
for arg in "$@"; do
    if [ "$arg" = "--watch" ]; then
        WATCH_MODE=true
    else
        TICKERS+=("$arg")
    fi
done

if [ ${#TICKERS[@]} -eq 0 ]; then
    echo -e "${RED}✗ ERROR: At least one ticker required${NC}"
    exit 1
fi

# Function to fetch and predict
predict_stock() {
    local ticker=$1
    
    echo -e "${CYAN}📊 Fetching LIVE data for ${WHITE}$ticker${NC}..."
    
    # Python script to fetch data and call API
    python3 << PYTHON_EOF
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    print("\033[0;31m✗ yfinance not installed\033[0m")
    print("\033[1;33mInstall: pip install yfinance\033[0m")
    sys.exit(1)

try:
    # Fetch latest data
    ticker = "$ticker"
    data = yf.download(ticker, period="1y", progress=False)
    
    if data.empty:
        print(f"✗ No data for {ticker}")
        sys.exit(1)
    
    # Get latest values
    latest = data.iloc[-1]
    open_price = float(latest['Open'])
    high = float(latest['High'])
    low = float(latest['Low'])
    close = float(latest['Close'])
    volume = float(latest['Volume'])
    
    # Calculate technical indicators
    def calc_rsi(prices, period=14):
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        seed = sum([d for d in deltas[:period] if d > 0]) / period
        neg_seed = sum([abs(d) for d in deltas[:period] if d < 0]) / period
        rs = seed / neg_seed if neg_seed else 0
        rsi = [100 - 100 / (1 + rs)]
        for i in range(period, len(deltas)):
            if deltas[i] > 0:
                seed = (seed * (period - 1) + deltas[i]) / period
                neg_seed = (neg_seed * (period - 1)) / period
            else:
                seed = (seed * (period - 1)) / period
                neg_seed = (neg_seed * (period - 1) + abs(deltas[i])) / period
            rs = seed / neg_seed if neg_seed else 0
            rsi.append(100 - 100 / (1 + rs))
        return rsi[-1] if rsi else 50
    
    # Calculate MACD
    def calc_macd(prices):
        ema12 = sum(prices[-12:]) / 12
        ema26 = sum(prices[-26:]) / 26 if len(prices) >= 26 else ema12
        macd = ema12 - ema26
        signal = (macd + ema12) / 2
        return macd, signal
    
    # Calculate Bollinger Bands
    def calc_bb(prices, period=20):
        sma = sum(prices[-period:]) / period
        variance = sum([(p - sma) ** 2 for p in prices[-period:]]) / period
        stddev = variance ** 0.5
        return sma + 2*stddev, sma, sma - 2*stddev
    
    prices = data['Close'].tolist()
    rsi = calc_rsi(prices)
    macd, signal = calc_macd(prices)
    bb_upper, bb_mid, bb_lower = calc_bb(prices)
    volatility = (prices[-1] - prices[-21]) / prices[-21] * 100 if len(prices) > 20 else 0
    
    # Prepare API request
    pred_data = {
        "data": [[open_price, high, low, close, volume, close, close, 0.01]]
    }
    
    # Call API
    url = "${API_URL}/predict"
    req = urllib.request.Request(
        url,
        data=json.dumps(pred_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read())
            
            # Format output
            print(f"\n\033[0;32m✓ LIVE DATA for {ticker}\033[0m")
            print(f"  Price: \033[0;36m\${close:.2f}\033[0m")
            print(f"  52W Range: {low:.2f} - {high:.2f}")
            print(f"  Volume: {volume:,.0f}")
            print(f"\n\033[0;35m📈 TECHNICAL INDICATORS\033[0m")
            print(f"  RSI(14): {rsi:.1f}", end="")
            if rsi > 70:
                print(f" \033[1;33mOVERBOUGHT\033[0m")
            elif rsi < 30:
                print(f" \033[1;33mOVERSOLD\033[0m")
            else:
                print()
            print(f"  MACD: {macd:.4f} | Signal: {signal:.4f}")
            print(f"  Bollinger Bands: {bb_upper:.2f} / {bb_mid:.2f} / {bb_lower:.2f}")
            print(f"  Volatility: {volatility:.2f}%")
            
            pred = result.get('predictions', [0])[0]
            conf = result.get('confidence', 0)
            
            # Log prediction for validation
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} | {ticker} | PRED: \${pred:.2f} | ACTUAL: pending | LOG_ONLY\n"
            
            try:
                with open("$LOG_FILE", "a") as log:
                    log.write(log_entry)
            except Exception:
                pass  # Continue even if logging fails
            
            print(f"\n\033[0;34m🔮 PREDICTION\033[0m")
            print(f"  Next Price: \033[0;32m\${pred:.2f}\033[0m")
            print(f"  Confidence: \033[0;35m{conf:.1%}\033[0m")
            
            change = pred - close
            pct_change = (change / close * 100) if close else 0
            if change > 0:
                print(f"  Expected: \033[0;32m+{pct_change:.2f}%\033[0m")
            else:
                print(f"  Expected: \033[0;31m{pct_change:.2f}%\033[0m")
            print()
    
    except urllib.error.URLError as e:
        print(f"✗ API Error: {e}")
        print(f"  Make sure API is running: curl http://localhost:8000/health")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

PYTHON_EOF
}

# Main loop
if [ "$WATCH_MODE" = true ]; then
    echo -e "${YELLOW}👀 WATCH MODE - Refreshing every ${REFRESH_INTERVAL}s (Ctrl+C to stop)${NC}\n"
    while true; do
        for ticker in "${TICKERS[@]}"; do
            predict_stock "$ticker"
        done
        echo -e "${YELLOW}⏰ Next refresh in ${REFRESH_INTERVAL}s... ($(date))${NC}\n"
        sleep "$REFRESH_INTERVAL"
    done
else
    for ticker in "${TICKERS[@]}"; do
        predict_stock "$ticker"
    done
fi
