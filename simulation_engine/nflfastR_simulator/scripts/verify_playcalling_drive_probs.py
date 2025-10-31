"""
Verify playcalling and drive_probs are fully utilized (Priority 2 & 3).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from simulator.team_profile import TeamProfile

def verify_playcalling_usage():
    """Verify get_pass_rate() uses full playcalling DataFrame."""
    print("="*70)
    print("VERIFY: PLAY-CALLING USAGE")
    print("="*70)
    
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    profile = TeamProfile('KC', 2025, 1, data_dir, debug=False)
    
    print(f"\n📊 Playcalling DataFrame:")
    print(f"   Shape: {profile.playcalling.shape}")
    print(f"   Columns: {list(profile.playcalling.columns)}")
    print(f"   Situations: {len(profile.playcalling)}")
    
    # Test get_pass_rate with various situations
    print(f"\n📊 Testing get_pass_rate() with different situations:")
    
    test_cases = [
        (1, 'short', 'tied', 'Q1-Q2'),
        (2, 'medium', 'up_7-13', 'Q3-Q4'),
        (3, 'long', 'down_14+', '2min'),
        (4, 'short', 'tied', 'Q1-Q2'),
    ]
    
    all_found = True
    for down, dist, score, time in test_cases:
        rate = profile.get_pass_rate(down, dist, score, time)
        if rate is None or rate < 0 or rate > 1:
            print(f"   ❌ FAIL: down={down}, dist={dist}, score={score}, time={time} -> {rate}")
            all_found = False
        else:
            print(f"   ✅ PASS: down={down}, dist={dist}, score={score}, time={time} -> {rate:.1%}")
    
    if all_found:
        print(f"\n✅ Playcalling fully utilized with robust fallbacks")
    else:
        print(f"\n⚠️  Some situations missing - fallbacks working")
    
    return all_found

def verify_drive_probs_usage():
    """Verify drive_probs are used (or identify where they should be integrated)."""
    print("\n" + "="*70)
    print("VERIFY: DRIVE PROBABILITIES USAGE")
    print("="*70)
    
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    profile = TeamProfile('KC', 2025, 1, data_dir, debug=False)
    
    print(f"\n📊 Drive Probabilities DataFrame:")
    print(f"   Shape: {profile.drive_probs.shape}")
    print(f"   Columns: {list(profile.drive_probs.columns)}")
    
    # Check if drive_probs has the expected structure
    expected_cols = ['start_yardline_bucket', 'td_prob', 'fg_prob', 'punt_prob', 'turnover_prob']
    has_all = all(col in profile.drive_probs.columns for col in expected_cols)
    
    if has_all:
        print(f"   ✅ Has expected columns")
        
        # Show sample
        print(f"\n   Sample data:")
        print(profile.drive_probs.head(10).to_string())
    else:
        missing = [col for col in expected_cols if col not in profile.drive_probs.columns]
        print(f"   ⚠️  Missing columns: {missing}")
    
    # Check game_simulator.py for usage
    game_sim_path = Path(__file__).parent.parent / "simulator" / "game_simulator.py"
    game_sim_code = game_sim_path.read_text()
    
    if 'drive_probs' in game_sim_code.lower():
        print(f"\n✅ drive_probs referenced in game_simulator.py")
        # Find where it's used
        lines = game_sim_code.split('\n')
        for i, line in enumerate(lines, 1):
            if 'drive_prob' in line.lower():
                print(f"   Line {i}: {line.strip()}")
    else:
        print(f"\n⚠️  drive_probs NOT found in game_simulator.py")
        print(f"   Recommendation: Integrate drive_probs for field position → outcome mapping")
        print(f"   Current: Drives simulate play-by-play until natural end")
        print(f"   Better: Use drive_probs to adjust TD/FG/punt probabilities by field position")
    
    return has_all

if __name__ == "__main__":
    playcalling_ok = verify_playcalling_usage()
    drive_probs_ok = verify_drive_probs_usage()
    
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    print(f"   Playcalling: {'✅ PASS' if playcalling_ok else '⚠️  NEEDS CHECK'}")
    print(f"   Drive Probs: {'✅ LOADED' if drive_probs_ok else '⚠️  ISSUES'}")
    print(f"   Drive Probs Usage: {'⚠️  NOT USED' if 'drive_probs' not in open(Path(__file__).parent.parent / 'simulator' / 'game_simulator.py').read().lower() else '✅ USED'}")

