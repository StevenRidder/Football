#!/bin/bash
# Run backtest, format for frontend, and verify integration

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SIMULATOR_DIR="$SCRIPT_DIR/simulation_engine/nflfastR_simulator"

echo "=" 
echo "NFL Simulator Integration"
echo "=" 
echo ""

# Step 1: Run backtest
echo "Step 1: Running backtest..."
cd "$SIMULATOR_DIR"
python3 backtest_all_games_conviction.py

# Step 2: Format for frontend
echo ""
echo "Step 2: Formatting for frontend..."
python3 scripts/format_for_frontend.py

# Step 3: Verify output
echo ""
echo "Step 3: Verifying output..."
OUTPUT_FILE="$SCRIPT_DIR/artifacts/simulator_predictions.csv"
if [ -f "$OUTPUT_FILE" ]; then
    echo "✅ Output file exists: $OUTPUT_FILE"
    ROW_COUNT=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "   Rows: $ROW_COUNT"
else
    echo "❌ Output file not found: $OUTPUT_FILE"
    exit 1
fi

echo ""
echo "✅ Integration complete!"
echo ""
echo "Next steps:"
echo "1. Start Flask server: python3 app_flask.py"
echo "2. Visit http://localhost:9876"
echo "3. Select weeks 1-8 for results, week 9 for predictions"

