#!/bin/bash

# Phase 1 Validation - Quick Start Script
# This script runs all Phase 1 steps in sequence

echo "================================================================================"
echo "PHASE 1 VALIDATION - QUICK START"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  1. Collect PFF data (or create sample data)"
echo "  2. Calculate matchup metrics"
echo "  3. Test all hypotheses"
echo "  4. Generate decision report"
echo ""
echo "Estimated time: 5-10 minutes"
echo ""
read -p "Press Enter to continue..."

cd "$(dirname "$0")"

echo ""
echo "================================================================================"
echo "STEP 1: COLLECT PFF DATA"
echo "================================================================================"
python3 collect_pff_data.py

if [ $? -ne 0 ]; then
    echo "❌ Error in Step 1"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 2: CALCULATE MATCHUP METRICS"
echo "================================================================================"
python3 calculate_matchup_metrics.py

if [ $? -ne 0 ]; then
    echo "❌ Error in Step 2"
    exit 1
fi

echo ""
echo "================================================================================"
echo "STEP 3: TEST ALL HYPOTHESES"
echo "================================================================================"
python3 test_all_hypotheses.py

if [ $? -ne 0 ]; then
    echo "❌ Error in Step 3"
    exit 1
fi

echo ""
echo "================================================================================"
echo "PHASE 1 COMPLETE!"
echo "================================================================================"
echo ""
echo "📄 Check results in: simulation_engine/phase1_validation/results/"
echo "📊 Review plots and summary report"
echo "🎯 Decision: GO / NO-GO to Phase 2"
echo ""

