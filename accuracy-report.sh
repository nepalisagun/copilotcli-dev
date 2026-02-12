#!/bin/bash
# Daily Accuracy Report - Analyze last 30 predictions
# Shows: Prediction accuracy, root cause analysis, self-improvement triggers

set -e

API_URL="${API_URL:-http://localhost:8000}"
LOG_FILE="${LOG_FILE:-predictions.log}"

if [ ! -f "$LOG_FILE" ]; then
    echo "📊 Accuracy Report"
    echo ""
    echo "❌ No prediction history found: $LOG_FILE"
    echo ""
    echo "To start logging predictions, run:"
    echo "  ./predict-stock-live.sh NVDA"
    exit 0
fi

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           📊 ACCURACY REPORT - Last 30 Predictions            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get root cause analysis from API
echo -e "${YELLOW}Fetching root cause analysis from API...${NC}"
root_cause_data=$(curl -s "$API_URL/root-cause" 2>/dev/null || echo '{}')

# Parse response
total_preds=$(echo "$root_cause_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_recent_predictions', 0))" 2>/dev/null || echo "0")
low_acc_count=$(echo "$root_cause_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('low_accuracy_count', 0))" 2>/dev/null || echo "0")
low_acc_pct=$(echo "$root_cause_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('low_accuracy_percentage', 0))" 2>/dev/null || echo "0")
recommended=$(echo "$root_cause_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('recommended_action', 'MONITOR'))" 2>/dev/null || echo "MONITOR")

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}PREDICTION ACCURACY METRICS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

if [ "$total_preds" -gt 0 ]; then
    accuracy_rate=$((100 - ${low_acc_pct%.*}))
    if [ "$accuracy_rate" -ge 90 ]; then
        status="${GREEN}✅ EXCELLENT${NC}"
    elif [ "$accuracy_rate" -ge 85 ]; then
        status="${GREEN}✅ GOOD${NC}"
    elif [ "$accuracy_rate" -ge 80 ]; then
        status="${YELLOW}⚠️  FAIR${NC}"
    else
        status="${RED}❌ POOR${NC}"
    fi
    
    echo -e "  Total predictions: ${CYAN}$total_preds${NC}"
    echo -e "  Accurate (≥85%):   ${GREEN}$((total_preds - ${low_acc_count%.*}))${NC}"
    echo -e "  Low accuracy (<85%): ${RED}${low_acc_count%.*}${NC}"
    echo -e "  Success rate:      $accuracy_rate%  $status"
else
    echo -e "  ${YELLOW}Insufficient data for analysis${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}ROOT CAUSE ANALYSIS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

echo -e "  ${MAGENTA}🌍 GEOPOLITICAL RISK${NC}"
echo -e "    Check for: war, tariff, sanction keywords in news"
echo -e "    Status: ⚠️  Manual verification needed (NewsAPI integration recommended)"
echo ""

echo -e "  ${MAGENTA}💰 FINANCIAL ANOMALIES${NC}"
echo -e "    Check for: Volume spike (>200% of 20-day avg)"
echo -e "    Check for: Earnings date announcement"
echo -e "    Status: ℹ️  Check knowledge/data/stocks-1k.csv for volatility"
echo ""

echo -e "  ${MAGENTA}⚙️  ALGORITHM DRIFT${NC}"
echo -e "    Check for: Feature importance weights change >20%"
echo -e "    Check for: RSI/MACD weighting shift"
echo -e "    Status: ℹ️  Current: XGBoost (500 estimators, v2.1)"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}RECENT LOW-ACCURACY PREDICTIONS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Show last 5 low accuracy predictions from log
if [ "$low_acc_count" -gt 0 ]; then
    echo ""
    tail -50 "$LOG_FILE" 2>/dev/null | grep -v "LOG_ONLY" | tail -5 | while read line; do
        if [ ! -z "$line" ]; then
            echo -e "  ${RED}$line${NC}"
        fi
    done
else
    echo -e "  ${GREEN}✅ All predictions accurate (≥85%)${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}SELF-IMPROVEMENT STATUS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

if [ "$recommended" = "TRIGGER RETRAIN" ]; then
    echo -e "  ${YELLOW}⚠️  CONDITION MET: 3+ days with accuracy <85%${NC}"
    echo -e "  ${YELLOW}🔄 RECOMMENDED ACTION: TRIGGER RETRAIN${NC}"
    echo ""
    echo -e "  ${CYAN}Command to trigger auto-retrain:${NC}"
    echo -e "    ${CYAN}curl -X POST $API_URL/trigger-retrain${NC}"
    echo ""
    echo -e "  ${YELLOW}This will:${NC}"
    echo -e "    1. Trigger CODEGEN_AGENT to regenerate @src/models/stock_pipeline.py"
    echo -e "    2. Analyze feature importance drift"
    echo -e "    3. Re-tune XGBoost hyperparameters"
    echo -e "    4. Run pytest with 95%+ coverage target"
    echo -e "    5. Deploy updated model"
else
    echo -e "  ${GREEN}✅ Status: MONITORING${NC}"
    echo -e "  Accuracy trend: ${GREEN}Good${NC}"
    echo -e "  No retrain needed at this time"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}API ENDPOINT REFERENCE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

echo -e "  ${CYAN}Validate a prediction:${NC}"
echo -e "    curl -X POST $API_URL/validate \\\\"
echo -e "      -H 'Content-Type: application/json' \\\\"
echo -e "      -d '{\"ticker\": \"NVDA\", \"timestamp\": \"2026-02-12 10:30:00\", \"predicted\": 194.27, \"actual\": 193.80}'"
echo ""

echo -e "  ${CYAN}Get root cause analysis:${NC}"
echo -e "    curl $API_URL/root-cause"
echo ""

echo -e "  ${CYAN}Trigger model retrain:${NC}"
echo -e "    curl -X POST $API_URL/trigger-retrain"
echo ""

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "Report generated: $(date)"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
