#!/bin/bash

# Run all preprocessing scripts to extract data from nflfastR

echo "=============================================================================="
echo "RUNNING ALL nflfastR DATA EXTRACTION"
echo "=============================================================================="

cd "$(dirname "$0")"

echo ""
echo "1/3 Extracting QB pressure splits..."
python3 extract_qb_splits.py

echo ""
echo "2/3 Extracting play-calling tendencies..."
python3 extract_playcalling.py

echo ""
echo "3/3 Extracting drive probabilities..."
python3 extract_drive_probs.py

echo ""
echo "=============================================================================="
echo "✅ ALL DATA EXTRACTION COMPLETE"
echo "=============================================================================="
echo ""
echo "Next steps:"
echo "  1. Review extracted data in simulation_engine/nflfastR_simulator/data/nflfastR/"
echo "  2. Build simulator classes (game_state.py, team_profile.py, etc.)"
echo "  3. Run backtest on 2024 season"

