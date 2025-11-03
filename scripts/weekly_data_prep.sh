#!/bin/bash
# Weekly Data Preparation Script
# Run this every Tuesday morning before generating predictions
#
# Usage:
#   ./scripts/weekly_data_prep.sh

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════════════════════"
echo "🏈 WEEKLY DATA PREP - NFL Edge"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Get current directory
PROJECT_ROOT="/Users/steveridder/Git/Football"
cd "$PROJECT_ROOT"

# Step 1: Update NFLverse stats (YPP, EPA, Red Zone, Special Teams, etc.)
echo "📊 Step 1/2: Updating NFLverse stats from nflfastR..."
echo "────────────────────────────────────────────────────────────────────────────────"
cd simulation_engine/nflfastR_simulator
python3 scripts/update_weekly_data.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ NFLverse data updated successfully!"
else
    echo ""
    echo "❌ NFLverse data update failed!"
    exit 1
fi

# Step 2: Re-fit isotonic calibration with latest data
echo ""
echo "📈 Step 2/2: Re-fitting isotonic calibration..."
echo "────────────────────────────────────────────────────────────────────────────────"
python3 fit_isotonic_2025_only.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Isotonic calibration updated successfully!"
else
    echo ""
    echo "❌ Calibration update failed!"
    exit 1
fi

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "✅ WEEKLY DATA PREP COMPLETE!"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📝 Next Steps:"
echo ""
echo "   1. [OPTIONAL] Download PFF QB Grades (manual process):"
echo "      → See: scripts/PFF_DOWNLOAD_GUIDE.md"
echo ""
echo "   2. Generate predictions for upcoming week:"
echo "      → Open: http://localhost:9876"
echo "      → Click: 'Predict Next 2 Weeks' button"
echo ""
echo "   3. Verify predictions loaded correctly"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "⏱️  Total time: ~2-3 minutes"
echo "════════════════════════════════════════════════════════════════════════════════"

