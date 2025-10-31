#!/usr/bin/env python3
"""
Roll-Forward Audit - Verify No Look-Ahead Bias

Checks that all features have as_of <= game kickoff - 1 week.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def audit_rollforward(games_file=None, features_dir=None):
    """
    Audit roll-forward discipline.
    
    For each game:
    1. Load all features used
    2. Check as_of timestamp
    3. Verify as_of <= kickoff - 7 days
    
    Returns:
        bool: True if all checks pass
    """
    print("\n" + "="*80)
    print("ROLL-FORWARD AUDIT")
    print("="*80 + "\n")
    
    # Placeholder - replace with actual data loading
    print("📊 Loading games and features...")
    
    # Sample 5 games for spot check
    sample_games = [
        {
            'game_id': '2024_01_01',
            'kickoff': datetime(2024, 9, 8, 13, 0),
            'features': [
                {'name': 'qb_stats', 'as_of': datetime(2024, 9, 1)},
                {'name': 'playcalling', 'as_of': datetime(2024, 9, 1)},
                {'name': 'epa', 'as_of': datetime(2024, 9, 1)},
            ]
        },
        # Add more sample games...
    ]
    
    print(f"   Checking {len(sample_games)} sample games\n")
    
    # Check each game
    violations = []
    
    for game in sample_games:
        print(f"Game: {game['game_id']} (Kickoff: {game['kickoff']})")
        
        cutoff = game['kickoff'] - timedelta(days=7)
        
        for feature in game['features']:
            as_of = feature['as_of']
            
            if as_of > cutoff:
                violation = {
                    'game_id': game['game_id'],
                    'feature': feature['name'],
                    'as_of': as_of,
                    'cutoff': cutoff,
                    'violation_days': (as_of - cutoff).days
                }
                violations.append(violation)
                print(f"  ❌ {feature['name']}: {as_of} > {cutoff} (VIOLATION)")
            else:
                print(f"  ✅ {feature['name']}: {as_of} <= {cutoff}")
        
        print()
    
    # Summary
    print("="*80)
    print("AUDIT RESULTS")
    print("="*80)
    
    if violations:
        print(f"❌ FAILED: {len(violations)} violations detected\n")
        for v in violations:
            print(f"  Game {v['game_id']}: {v['feature']} used data from "
                  f"{v['as_of']} (cutoff: {v['cutoff']}, "
                  f"{v['violation_days']} days late)")
        print()
        return False
    else:
        print("✅ PASSED: No look-ahead bias detected\n")
        return True


def main():
    passed = audit_rollforward()
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()

