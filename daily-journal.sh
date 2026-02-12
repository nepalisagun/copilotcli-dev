#!/bin/bash
# daily-journal.sh - Daily ML swarm validation + self-learning
# Runs after market close to validate yesterday's predictions and update ML brain

set -e

TICKER="${1:-NVDA}"
API_HOST="${2:-http://localhost:8000}"
DATE=$(date +%Y-%m-%d)
PREV_DATE=$(date -d yesterday +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  🧠 DAILY ML JOURNAL UPDATE - $(date +%Y-%m-%d)"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Fetch LIVE data for validation
echo "📊 Fetching LIVE validation data for $TICKER..."
python3 << 'PYTHON_EOF'
import sys
import json
import yfinance as yf
from datetime import datetime, timedelta

ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

try:
    # Get yesterday's closing price (actual)
    hist = yf.Ticker(ticker).history(period="5d")
    if len(hist) >= 2:
        actual = float(hist.iloc[-2]['Close'])  # Yesterday's close
        date_str = hist.index[-2].strftime('%Y-%m-%d')
    else:
        print(json.dumps({"error": "insufficient data"}))
        sys.exit(1)
    
    # Get current data
    current = hist.iloc[-1]
    current_price = float(current['Close'])
    volume = int(current['Volume'])
    
    data = {
        "date": date_str,
        "ticker": ticker,
        "actual": actual,
        "current_price": current_price,
        "volume": volume,
        "volume_7d_avg": float(hist['Volume'].tail(7).mean())
    }
    
    print(json.dumps(data))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
PYTHON_EOF

DATA_JSON=$(python3 << 'PYTHON_EOF'
import sys
import json
import yfinance as yf
from datetime import datetime, timedelta

ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

try:
    hist = yf.Ticker(ticker).history(period="5d")
    if len(hist) >= 2:
        actual = float(hist.iloc[-2]['Close'])
        date_str = hist.index[-2].strftime('%Y-%m-%d')
    else:
        print(json.dumps({"error": "insufficient data"}))
        sys.exit(1)
    
    current = hist.iloc[-1]
    current_price = float(current['Close'])
    volume = int(current['Volume'])
    
    data = {
        "date": date_str,
        "ticker": ticker,
        "actual": actual,
        "current_price": current_price,
        "volume": volume,
        "volume_7d_avg": float(hist['Volume'].tail(7).mean())
    }
    
    print(json.dumps(data))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
PYTHON_EOF
)

ACTUAL=$(echo $DATA_JSON | python3 -c "import sys, json; print(json.load(sys.stdin).get('actual', 'unknown'))" 2>/dev/null || echo "unknown")
VOLUME=$(echo $DATA_JSON | python3 -c "import sys, json; print(json.load(sys.stdin).get('volume', 0))" 2>/dev/null || echo "0")
VOL_7D_AVG=$(echo $DATA_JSON | python3 -c "import sys, json; print(json.load(sys.stdin).get('volume_7d_avg', 1))" 2>/dev/null || echo "1")

if [ "$ACTUAL" = "unknown" ]; then
    echo "❌ Failed to fetch validation data"
    exit 1
fi

echo "✅ ACTUAL $TICKER: \$$ACTUAL (Volume: ${VOLUME})"
echo ""

# Fetch last prediction from predictions.csv
if [ -f "predictions.csv" ]; then
    LAST_PRED=$(tail -1 predictions.csv | cut -d',' -f3)
    echo "📈 LAST PREDICTION: \$$LAST_PRED"
else
    echo "⚠️  No predictions.csv found"
    LAST_PRED="0"
fi

if [ "$LAST_PRED" != "0" ] && [ "$ACTUAL" != "unknown" ]; then
    # Calculate accuracy
    DIFF=$(python3 -c "print(abs($ACTUAL - $LAST_PRED))")
    ACCURACY=$(python3 -c "print(max(0, min(100, (1 - abs($ACTUAL - $LAST_PRED) / abs($ACTUAL)) * 100)))")
    
    echo "📊 ACCURACY: ${ACCURACY}%"
    echo ""
    
    # Call /daily-journal-update endpoint
    echo "🧠 Updating ML brain..."
    RESPONSE=$(curl -s -X POST "$API_HOST/daily-journal-update?ticker=$TICKER&prediction=$LAST_PRED&actual=$ACTUAL" \
        -H "Content-Type: application/json")
    
    echo "✅ Journal updated"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    
    # Check if retrain needed
    RETRAIN=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print('YES' if d.get('retrain_needed') else 'NO')" 2>/dev/null || echo "NO")
    
    if [ "$RETRAIN" = "YES" ]; then
        echo ""
        echo "🔄 RETRAIN TRIGGERED - Accuracy <85% detected"
        echo "→ CODEGEN_AGENT will improve model tomorrow"
    fi
else
    echo "⚠️  Skipping validation (no valid prediction data)"
fi

# Get journal summary
echo ""
echo "📚 ML BRAIN STATUS:"
JOURNAL=$(curl -s "$API_HOST/journal")
echo "$JOURNAL" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  • Entries: {d.get('journal_entries', 0)}\")
print(f\"  • 7-Day Avg Accuracy: {d.get('accuracy_7d_avg', 0)}%\")
print(f\"  • Trend: {d.get('accuracy_trend', 'unknown')}\")
print(f\"  • Lessons Learned: {d.get('lessons_learned_count', 0)}\")
print(f\"  • Self-Improving: {d.get('self_improving', False)}\")
" 2>/dev/null || echo "  ❌ Could not fetch journal"

echo ""
echo "════════════════════════════════════════════════════════════════"
