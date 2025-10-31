#!/bin/bash
# Script to generate all predictions and update frontend data

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo "=============================================================================="
echo "UPDATE FRONTEND PREDICTIONS - WEEKS 1-10"
echo "=============================================================================="

# Step 1: Generate backtest for weeks 1-8
echo ""
echo "Step 1: Generating backtest for weeks 1-8..."
python3 backtest_all_games_conviction.py

# Step 2: Generate predictions for weeks 9-10
echo ""
echo "Step 2: Generating predictions for weeks 9-10..."
python3 scripts/generate_week9_10_predictions.py

# Step 3: Format for frontend
echo ""
echo "Step 3: Formatting for frontend..."
python3 scripts/format_for_frontend.py

echo ""
echo "=============================================================================="
echo "✅ COMPLETE - Frontend predictions updated"
echo "=============================================================================="
echo ""
echo "Files generated:"
echo "  - artifacts/backtest_all_games_conviction.csv (weeks 1-8)"
echo "  - artifacts/backtest_week9_10_predictions.csv (weeks 9-10)"
echo "  - artifacts/simulator_predictions.csv (combined, formatted for frontend)"
echo ""
echo "Next: Refresh your browser to see updated predictions"

