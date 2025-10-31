"""
Force clean re-enrichment of predictions with current calibration.
"""
from adjustment_calibration import set_calibration_multiplier, get_calibration_multiplier
from edge_hunt.integrate_signals import enrich_predictions_with_signals, _SIGNAL_CACHE
import pandas as pd
from pathlib import Path
import sys

# Get calibration from command line or use 1x
calibration = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0

print(f"🎯 FORCE RE-ENRICHMENT WITH {calibration}x CALIBRATION")
print("="*80)

# Set calibration
set_calibration_multiplier(calibration)
print(f"✅ Calibration set to {get_calibration_multiplier()}x")

# Clear signal cache
_SIGNAL_CACHE.clear()
print(f"✅ Signal cache cleared")

# Load base predictions
artifacts = Path("artifacts")
csvs = sorted(artifacts.glob("predictions_2025_*.csv"))

if not csvs:
    print("❌ No predictions found!")
    sys.exit(1)

csv_file = csvs[-1]
print(f"📂 Loading: {csv_file}")

df = pd.read_csv(csv_file)
print(f"✅ Loaded {len(df)} games")

# Remove ALL enrichment columns to start fresh
enrich_cols = [
    'edge_hunt_signals', 'has_edge_hunt_signal', 'edge_hunt_signal_count',
    'edge_hunt_total_edge', 'edge_hunt_spread_edge', 'market_implied_away',
    'market_implied_home', 'adjusted_away', 'adjusted_home', 'adjusted_spread',
    'adjusted_total', 'all_injuries', 'away_injury_impact', 'home_injury_impact',
    'Rec_spread', 'Rec_total', 'spread_edge_pts', 'total_edge_pts'
]

for col in enrich_cols:
    if col in df.columns:
        df = df.drop(columns=[col])

print(f"✅ Removed enrichment columns, starting CLEAN")
print(f"\n🔄 Re-enriching {len(df)} games...")

# Re-enrich
enriched = enrich_predictions_with_signals(df, week=9, season=2025)

# Show sample results
print(f"\n📊 SAMPLE RESULTS (MIN @ DET):")
game = enriched[(enriched['away'] == 'MIN') & (enriched['home'] == 'DET')].iloc[0]
print(f"   Market: {game['market_implied_away']:.1f}-{game['market_implied_home']:.1f}")
print(f"   Adjusted: {game['adjusted_away']:.1f}-{game['adjusted_home']:.1f}")
print(f"   Market spread: {game['Spread used (home-)']:.1f}")
print(f"   Adjusted spread: {game['adjusted_spread']:.1f}")
print(f"   Market total: {game['Total used']:.1f}")
print(f"   Adjusted total: {game['adjusted_total']:.1f}")

# Save
enriched.to_csv(csv_file, index=False)
print(f"\n✅ SAVED to {csv_file}")
print(f"\n🎯 Calibration: {get_calibration_multiplier()}x")
print(f"   Reload the web page to see changes!")

