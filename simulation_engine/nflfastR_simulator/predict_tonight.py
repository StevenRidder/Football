"""
Predict tonight's game: Baltimore Ravens @ Miami Dolphins
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile

# Game details
SEASON = 2024
WEEK = 17  # Adjust if needed
HOME_TEAM = "MIA"
AWAY_TEAM = "BAL"

# Current Vegas lines: MIA -7.5, Total 52.5
# In our convention: positive spread_line means home team favored
SPREAD_LINE = 7.5  # MIA -7.5 (MIA favored by 7.5)
TOTAL_LINE = 52.5

# Simulation parameters
N_SIMS = 1000
BREAKEVEN = 0.5238
EDGE_THRESHOLD = 0.025

print("=" * 60)
print("🏈 TONIGHT'S GAME PREDICTION")
print("=" * 60)
print(f"\n{AWAY_TEAM} @ {HOME_TEAM}")
print(f"Week {WEEK}, {SEASON}")
print(f"\nVegas Lines:")
print(f"  Spread: {AWAY_TEAM} {SPREAD_LINE:+.1f}")
print(f"  Total: {TOTAL_LINE}")
print(f"\nRunning {N_SIMS:,} simulations...")
print("=" * 60)

# Create team profiles
data_dir = Path(__file__).parent / "data" / "nflfastR"
home_profile = TeamProfile(HOME_TEAM, SEASON, WEEK, data_dir=data_dir)
away_profile = TeamProfile(AWAY_TEAM, SEASON, WEEK, data_dir=data_dir)

print(f"\n📊 TEAM PROFILES:")
print(f"\n{HOME_TEAM} (Home): {home_profile.team}")
print(f"\n{AWAY_TEAM} (Away): {away_profile.team}")

# Create simulator
simulator = GameSimulator(home_profile, away_profile)

# Run simulations
home_scores = []
away_scores = []

for sim_i in range(N_SIMS):
    np.random.seed(42 + sim_i)  # Reproducible
    
    result = simulator.simulate_game()
    
    home_scores.append(result['home_score'])
    away_scores.append(result['away_score'])

# Convert to arrays
home_scores = np.asarray(home_scores)
away_scores = np.asarray(away_scores)

# Raw simulation results
raw_home_avg = home_scores.mean()
raw_away_avg = away_scores.mean()
raw_spread = raw_home_avg - raw_away_avg
raw_total = raw_home_avg + raw_away_avg

print(f"\n📈 RAW SIMULATION (before market centering):")
print(f"  {HOME_TEAM}: {raw_home_avg:.1f} points")
print(f"  {AWAY_TEAM}: {raw_away_avg:.1f} points")
print(f"  Spread: {HOME_TEAM} {raw_spread:+.1f}")
print(f"  Total: {raw_total:.1f}")

# Center to market
def center_scores_to_market(home_scores, away_scores, spread_line, total_line):
    """Center simulated scores to match market lines."""
    home_mean = home_scores.mean()
    away_mean = away_scores.mean()
    
    sim_spread = home_mean - away_mean
    sim_total = home_mean + away_mean
    
    spread_adj = (spread_line - sim_spread) / 2
    total_adj = (total_line - sim_total) / 2
    
    home_adj = home_scores + spread_adj + total_adj
    away_adj = away_scores - spread_adj + total_adj
    
    return home_adj, away_adj

home_c, away_c = center_scores_to_market(home_scores, away_scores, SPREAD_LINE, TOTAL_LINE)

spreads_c = home_c - away_c
totals_c = home_c + away_c

print(f"\n📊 CENTERED TO MARKET:")
print(f"  {HOME_TEAM}: {home_c.mean():.1f} ± {home_c.std():.1f}")
print(f"  {AWAY_TEAM}: {away_c.mean():.1f} ± {away_c.std():.1f}")
print(f"  Spread: {HOME_TEAM} {spreads_c.mean():+.1f} (SD: {spreads_c.std():.1f})")
print(f"  Total: {totals_c.mean():.1f} (SD: {totals_c.std():.1f})")

# Calculate probabilities
p_home_cover = np.mean(spreads_c > SPREAD_LINE)
p_away_cover = 1 - p_home_cover
p_over = np.mean(totals_c > TOTAL_LINE)
p_under = 1 - p_over

print(f"\n🎲 PROBABILITIES:")
print(f"  {HOME_TEAM} covers ({HOME_TEAM} {SPREAD_LINE:+.1f}): {p_home_cover:.1%}")
print(f"  {AWAY_TEAM} covers ({AWAY_TEAM} {-SPREAD_LINE:+.1f}): {p_away_cover:.1%}")
print(f"  Over {TOTAL_LINE}: {p_over:.1%}")
print(f"  Under {TOTAL_LINE}: {p_under:.1%}")

# Betting recommendations
print(f"\n💰 BETTING RECOMMENDATIONS:")
print(f"  (Edge threshold: {EDGE_THRESHOLD*100:.1f}%, Breakeven: {BREAKEVEN*100:.2f}%)")

bet_spread = None
bet_total = None

if p_home_cover > (BREAKEVEN + EDGE_THRESHOLD):
    bet_spread = f"{HOME_TEAM} {SPREAD_LINE:+.1f}"
    edge_spread = p_home_cover - BREAKEVEN
    print(f"  ✅ BET: {bet_spread} (Edge: {edge_spread*100:.1f}%)")
elif p_away_cover > (BREAKEVEN + EDGE_THRESHOLD):
    bet_spread = f"{AWAY_TEAM} {-SPREAD_LINE:+.1f}"
    edge_spread = p_away_cover - BREAKEVEN
    print(f"  ✅ BET: {bet_spread} (Edge: {edge_spread*100:.1f}%)")
else:
    print(f"  ⛔ NO SPREAD BET (no edge)")

if p_over > (BREAKEVEN + EDGE_THRESHOLD):
    bet_total = f"OVER {TOTAL_LINE}"
    edge_total = p_over - BREAKEVEN
    print(f"  ✅ BET: {bet_total} (Edge: {edge_total*100:.1f}%)")
elif p_under > (BREAKEVEN + EDGE_THRESHOLD):
    bet_total = f"UNDER {TOTAL_LINE}"
    edge_total = p_under - BREAKEVEN
    print(f"  ✅ BET: {bet_total} (Edge: {edge_total*100:.1f}%)")
else:
    print(f"  ⛔ NO TOTAL BET (no edge)")

# Score distribution
print(f"\n📊 SCORE DISTRIBUTION:")
print(f"  Most likely {HOME_TEAM} score: {np.median(home_c):.0f}")
print(f"  Most likely {AWAY_TEAM} score: {np.median(away_c):.0f}")
print(f"  {HOME_TEAM} scores 20-30: {np.mean((home_c >= 20) & (home_c <= 30)):.1%}")
print(f"  {AWAY_TEAM} scores 20-30: {np.mean((away_c >= 20) & (away_c <= 30)):.1%}")
print(f"  Total 40-50: {np.mean((totals_c >= 40) & (totals_c <= 50)):.1%}")
print(f"  Total 50+: {np.mean(totals_c >= 50):.1%}")

# Win probability
p_home_win = np.mean(home_c > away_c)
print(f"\n🏆 WIN PROBABILITY:")
print(f"  {HOME_TEAM}: {p_home_win:.1%}")
print(f"  {AWAY_TEAM}: {1-p_home_win:.1%}")

print("\n" + "=" * 60)
print("Note: Update SPREAD_LINE and TOTAL_LINE with current odds")
print("=" * 60)

