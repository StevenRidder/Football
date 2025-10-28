"""
Pre-compute Edge Hunt signals and cache them.

Run this after generating predictions to warm the cache.
This way the web app loads instantly.

Usage:
    python3 precompute_edge_hunt_signals.py
"""

import pandas as pd
from pathlib import Path
from edge_hunt.integrate_signals import enrich_predictions_with_signals
from schedules import CURRENT_WEEK, CURRENT_SEASON
import time

def main():
    # Find latest predictions file
    artifacts = Path("artifacts")
    csvs = sorted(artifacts.glob("predictions_2025_*.csv"))
    
    # Get the most recent file that doesn't have 'week' in the name
    current_week_files = [f for f in csvs if '_week' not in f.name]
    if current_week_files:
        latest = current_week_files[-1]
    else:
        latest = csvs[-1]
    
    print(f"📊 Loading predictions from: {latest.name}")
    df = pd.read_csv(latest)
    print(f"   {len(df)} games found")
    
    # Pre-compute signals (this will populate the cache)
    print(f"\n🔄 Pre-computing Edge Hunt signals for Week {CURRENT_WEEK}...")
    print("   (This may take 60-90 seconds on first run)")
    
    start = time.time()
    enriched = enrich_predictions_with_signals(df, week=CURRENT_WEEK, season=CURRENT_SEASON)
    elapsed = time.time() - start
    
    signal_count = enriched['has_edge_hunt_signal'].sum()
    
    print(f"\n✅ Done in {elapsed:.1f} seconds!")
    print(f"   {signal_count} games have Edge Hunt signals")
    
    # Show summary
    if signal_count > 0:
        print(f"\n📋 Games with signals:")
        for _, row in enriched[enriched['has_edge_hunt_signal']].iterrows():
            signals = row['edge_hunt_signals']
            signal_names = [f"{s['icon']} {s['badge']}" for s in signals]
            print(f"   • {row['away']} @ {row['home']}: {', '.join(signal_names)}")
    
    # SAVE the enriched predictions (overwrites the original)
    print(f"\n💾 Saving enriched predictions to {latest.name}...")
    enriched.to_csv(latest, index=False)
    
    print(f"✅ Signals cached for 1 hour")
    print(f"✅ Enriched predictions saved")
    print(f"   Web app will now load instantly!")

if __name__ == "__main__":
    main()

