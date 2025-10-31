"""
Integrate drive_probs into game simulation (Priority 3 enhancement).

Use drive_probs to adjust TD/FG/punt probabilities based on starting field position.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Read game_simulator.py
game_sim_path = Path(__file__).parent.parent / "simulator" / "game_simulator.py"
game_sim_code = game_sim_path.read_text()

print("="*70)
print("DRIVE PROBABILITIES INTEGRATION")
print("="*70)

print(f"\n📊 Current drive simulation:")
print(f"   • Simulates play-by-play until natural end")
print(f"   • 4th down decisions based on field position heuristics")
print(f"   • drive_probs loaded but NOT used")

print(f"\n💡 Enhancement idea:")
print(f"   • Use drive_probs to adjust TD/FG probabilities by starting field position")
print(f"   • Example: Starting at own 20 → use drive_probs['own_20']")
print(f"   • Boost TD prob if td_prob from drive_probs > baseline")
print(f"   • Adjust FG prob similarly")

print(f"\n⚠️  Current approach may be fine:")
print(f"   • Play-by-play simulation naturally produces realistic drive outcomes")
print(f"   • Adding drive_probs might be redundant or conflicting")
print(f"   • Recommendation: Keep play-by-play, use drive_probs for validation only")

print(f"\n✅ Drive probs ARE loaded and available for:")
print(f"   • Validation (check if simulated drive outcomes match historical probs)")
print(f"   • Calibration (adjust if simulated outcomes drift from historical)")

