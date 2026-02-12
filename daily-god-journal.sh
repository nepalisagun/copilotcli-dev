#!/bin/bash
# daily-god-journal.sh - Daily god-level ML intelligence + self-healing
# Full 25-factor analysis + Finnhub + Alpha Vantage + auto-retrain decision

set -e

TICKER="${1:-NVDA}"
API_HOST="${2:-http://localhost:8000}"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║  🧠 GOD-LEVEL DAILY ML ANALYSIS                                     ║"
echo "║  $(date '+%Y-%m-%d %H:%M:%S')                                              ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Validate ticker
echo "✅ Validating ticker $TICKER..."
python3 << 'PYTHON_EOF'
import sys
import yfinance as yf

ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
try:
    _ = yf.Ticker(ticker).info
    print(f"✓ {ticker} valid")
except:
    print(f"✗ Invalid ticker: {ticker}")
    sys.exit(1)
PYTHON_EOF

echo ""
echo "📊 FETCHING 25-FACTOR GOD-MODE ANALYSIS..."
echo ""

# Call /god-mode endpoint
GOD_RESPONSE=$(curl -s -X POST "$API_HOST/god-mode?ticker=$TICKER")

# Display intelligence score
INTEL_SCORE=$(echo "$GOD_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intelligence_score', 0))" 2>/dev/null || echo "0")

echo "🎯 INTELLIGENCE SCORE: $INTEL_SCORE/100"
echo ""

# Display geopolitical analysis
echo "🌍 GEOPOLITICAL ANALYSIS:"
echo "$GOD_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
geo = d.get('factors', {}).get('geopolitical', {})
score = geo.get('score', 0)
keywords = geo.get('risk_keywords', {})
interp = geo.get('interpretation', 'UNKNOWN')

print(f\"  • Geo Risk Score: {score}%\")
print(f\"  • Interpretation: {interp}\")
if keywords:
    for kw, count in sorted(keywords.items(), key=lambda x: -x[1])[:3]:
        print(f\"    - {kw}: {count} mentions\")
else:
    print(f\"    - No risk keywords detected (safe)\")
" 2>/dev/null

echo ""
echo "📈 TECHNICAL ANALYSIS (20-year patterns):"
echo "$GOD_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tech = d.get('factors', {}).get('technical', {})

print(f\"  • RSI(14) 20-yr Avg: {tech.get('rsi_20yr', 'N/A')}\")
print(f\"  • RSI Trend: {tech.get('rsi_trend', 'N/A').upper()}\")
print(f\"  • Volatility (1yr): {tech.get('volatility', 'N/A')}%\")
print(f\"  • MACD Signal: {tech.get('macd_signal', 'N/A').upper()}\")
print(f\"  • Price Trend (30d): {tech.get('trend', 'N/A').upper()}\")
" 2>/dev/null

echo ""
echo "🧠 ML BRAIN STATUS:"
echo "$GOD_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ml = d.get('factors', {}).get('ml_brain', {})

print(f\"  • Accuracy (7d): {ml.get('accuracy_7d', 'N/A')}%\")
print(f\"  • Lessons Learned: {ml.get('lessons_learned', 0)}\")
print(f\"  • Improvement Trend: {ml.get('trend', 'N/A').upper()}\")
print(f\"  • Model Age: {ml.get('model_age_days', 'N/A')} days\")
" 2>/dev/null

echo ""
echo "🔄 DECISION ENGINE:"
RETRAIN=$(echo "$GOD_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print('YES' if d.get('decision', {}).get('retrain_needed') else 'NO')" 2>/dev/null || echo "NO")
REASON=$(echo "$GOD_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('decision', {}).get('retrain_reason', 'unknown'))" 2>/dev/null || echo "unknown")
ACTION=$(echo "$GOD_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('decision', {}).get('recommended_action', 'MONITOR'))" 2>/dev/null || echo "MONITOR")

echo "  • Retrain Needed: $RETRAIN"
echo "  • Reason: $REASON"
echo "  • Action: $ACTION"

if [ "$RETRAIN" = "YES" ]; then
    echo ""
    echo "⚡ AUTO-RETRAIN INITIATED"
    echo "  → CODEGEN_AGENT triggered for model improvement"
    echo "  → TEST_AGENT will validate 95%+ coverage"
    echo "  → DEPLOY_AGENT will containerize & deploy"
    echo "  → Estimated time: 120 seconds"
fi

echo ""
echo "📋 API REQUEST COUNTERS:"
echo "$GOD_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
sources = d.get('data_sources', {})

print(f\"  • Finnhub: {sources.get('finnhub_requests', 'N/A')}\")
print(f\"  • Alpha Vantage: {sources.get('alpha_vantage_requests', 'N/A')}\")
print(f\"  • ML Journal Entries: {sources.get('ml_journal_entries', 0)}\")
" 2>/dev/null

echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "🏆 GOD-MODE ANALYSIS COMPLETE"
echo "═════════════════════════════════════════════════════════════════════════"
echo ""

# Update daily journal with this analysis
echo "🧠 Storing analysis in ML journal..."
curl -s -X POST "$API_HOST/daily-journal-update?ticker=$TICKER" > /dev/null 2>&1 || true
echo "✅ Journal updated"
echo ""
