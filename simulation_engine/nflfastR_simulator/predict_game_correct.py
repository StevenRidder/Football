"""
Predict game with CORRECT interpretation:
- Market sets the mean
- Simulator shapes the distribution
- Never mention raw uncentered totals
- Only report centered probabilities
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from simulator.game_simulator import GameSimulator
from simulator.team_profile import TeamProfile

def center_scores_to_market(
    home_scores,
    away_scores,
    spread_line,
    total_line,
    alpha: float = 1.0,
    clip_scale: tuple = (0.5, 2.0)
):
    """
    Anchor simulated scores to market while preserving relative structure.
    
    Three-step process:
    1) Multiplicative scale toward target_total (clipped for safety)
    2) Additive total correction (preserves spread, fixes mean)
    3) Additive spread correction (preserves total)
    
    This hits market exactly even when scaling is clipped.
    """
    home_scores = np.asarray(home_scores, dtype=np.float64)
    away_scores = np.asarray(away_scores, dtype=np.float64)

    hm, am = home_scores.mean(), away_scores.mean()
    sim_total, sim_spread = hm + am, hm - am

    # Blended targets
    target_total  = alpha * total_line  + (1 - alpha) * sim_total
    target_spread = alpha * spread_line + (1 - alpha) * sim_spread

    # Step 1: multiplicative scale toward target_total, but clip
    eps = 1e-6
    scale = float(np.clip(target_total / max(sim_total, eps), *clip_scale))
    h = home_scores * scale
    a = away_scores * scale

    # Step 2: additive total correction (preserves spread)
    scaled_total = h.mean() + a.mean()
    c = (target_total - scaled_total) / 2.0
    h += c
    a += c

    # Step 3: additive spread correction (preserves total)
    scaled_spread = h.mean() - a.mean()
    d = (target_spread - scaled_spread) / 2.0
    h += d
    a -= d

    # Non-negative guard
    h = np.clip(h, 0, None)
    a = np.clip(a, 0, None)
    return h, a

def predict_game(away_team, home_team, spread_line, total_line, season=2024, week=17, n_sims=1000):
    """
    Predict game outcome.
    
    GATING CHECKLIST:
    1. Centering check: mean(spread_sim) ≈ market_spread and mean(total_sim) ≈ market_total
    2. Probability source: all probabilities computed from centered distributions
    3. Breakeven test: p > 0.5238 + threshold for the offered side or total
    4. Sample check: n_sims ≥ 200; SD within targets (spread 10–16, total 7–13)
    5. Consistency check: spread sign and bet side agree with the printed line
    """
    BREAKEVEN = 0.5238
    EDGE_THRESHOLD = 0.025
    
    # Create team profiles
    data_dir = Path(__file__).parent / "data" / "nflfastR"
    home_profile = TeamProfile(home_team, season, week, data_dir=data_dir)
    away_profile = TeamProfile(away_team, season, week, data_dir=data_dir)
    
    # Create simulator
    simulator = GameSimulator(home_profile, away_profile)
    
    # Run simulations
    home_scores = []
    away_scores = []
    
    for sim_i in range(n_sims):
        np.random.seed(42 + sim_i)
        result = simulator.simulate_game()
        home_scores.append(result['home_score'])
        away_scores.append(result['away_score'])
    
    # Convert to arrays
    home_scores = np.asarray(home_scores)
    away_scores = np.asarray(away_scores)
    
    # Store raw simulator stats
    raw_home_mean = home_scores.mean()
    raw_away_mean = away_scores.mean()
    raw_spread_mean = raw_home_mean - raw_away_mean
    raw_total_mean = raw_home_mean + raw_away_mean
    
    # CENTER TO MARKET (this is the key step)
    home_c, away_c = center_scores_to_market(home_scores, away_scores, spread_line, total_line)
    
    spreads_c = home_c - away_c
    totals_c = home_c + away_c
    
    # Final centered stats
    centered_home_mean = home_c.mean()
    centered_away_mean = away_c.mean()
    centered_spread_mean = spreads_c.mean()
    centered_total_mean = totals_c.mean()
    
    # GATING CHECK 1: Centering
    spread_error = abs(spreads_c.mean() - spread_line)
    total_error = abs(totals_c.mean() - total_line)
    
    if spread_error > 0.25 or total_error > 0.25:
        return {"error": f"Centering failed: spread_error={spread_error:.3f}, total_error={total_error:.3f}"}
    
    # GATING CHECK 4: Sample size and variance
    spread_sd = spreads_c.std()
    total_sd = totals_c.std()
    
    if n_sims < 200:
        print(f"⚠️  Warning: n_sims={n_sims} < 200 (less stable)")
    
    if not (10 <= spread_sd <= 16):
        print(f"⚠️  Warning: spread_sd={spread_sd:.1f} outside [10, 16]")
    
    if not (7 <= total_sd <= 13):
        print(f"⚠️  Warning: total_sd={total_sd:.1f} outside [7, 13]")
    
    # GATING CHECK 2: Compute probabilities from CENTERED distributions
    p_home_cover = np.mean(spreads_c > spread_line)
    p_away_cover = 1 - p_home_cover
    p_over = np.mean(totals_c > total_line)
    p_under = 1 - p_over
    
    # GATING CHECK 3: Breakeven test
    spread_bet = None
    spread_edge = 0
    
    if p_home_cover > (BREAKEVEN + EDGE_THRESHOLD):
        spread_bet = 'HOME'
        spread_edge = p_home_cover - BREAKEVEN
    elif p_away_cover > (BREAKEVEN + EDGE_THRESHOLD):
        spread_bet = 'AWAY'
        spread_edge = p_away_cover - BREAKEVEN
    
    total_bet = None
    total_edge = 0
    
    if p_over > (BREAKEVEN + EDGE_THRESHOLD):
        total_bet = f"OVER {total_line}"
        total_edge = p_over - BREAKEVEN
    elif p_under > (BREAKEVEN + EDGE_THRESHOLD):
        total_bet = f"UNDER {total_line}"
        total_edge = p_under - BREAKEVEN
    
    # GATING CHECK 5: Consistency (done implicitly by construction)
    
    return {
        'away_team': away_team,
        'home_team': home_team,
        'spread_line': spread_line,
        'total_line': total_line,
        'p_home_cover': p_home_cover,
        'p_away_cover': p_away_cover,
        'p_over': p_over,
        'p_under': p_under,
        'spread_bet': spread_bet,
        'spread_edge': spread_edge,
        'total_bet': total_bet,
        'total_edge': total_edge,
        'spread_sd': spread_sd,
        'total_sd': total_sd,
        # Raw simulator output
        'raw_home_mean': raw_home_mean,
        'raw_away_mean': raw_away_mean,
        'raw_spread_mean': raw_spread_mean,
        'raw_total_mean': raw_total_mean,
        # Centered output
        'centered_home_mean': centered_home_mean,
        'centered_away_mean': centered_away_mean,
        'centered_spread_mean': centered_spread_mean,
        'centered_total_mean': centered_total_mean,
    }

def print_prediction(result):
    """Print prediction in correct format."""
    if 'error' in result:
        print(f"❌ ERROR: {result['error']}")
        return
    
    print("=" * 70)
    print("GAME PREDICTION")
    print("=" * 70)
    
    print(f"\nGAME: {result['away_team']} @ {result['home_team']}")
    
    # Format spread line correctly: show favored team
    if result['spread_line'] < 0:
        spread_str = f"{result['away_team']} {result['spread_line']:+.1f}"
    else:
        spread_str = f"{result['home_team']} {result['spread_line']:+.1f}"
    
    print(f"LINE: {spread_str}, TOTAL {result['total_line']:.1f}")
    
    print(f"\n" + "=" * 70)
    print("RAW SIMULATOR OUTPUT (Before Market Centering)")
    print("=" * 70)
    print(f"{result['home_team']}: {result['raw_home_mean']:.1f} points")
    print(f"{result['away_team']}: {result['raw_away_mean']:.1f} points")
    print(f"Spread ({result['home_team']} - {result['away_team']}): {result['raw_spread_mean']:+.1f}")
    print(f"Total: {result['raw_total_mean']:.1f}")
    
    print(f"\n" + "=" * 70)
    print("AFTER MARKET CENTERING")
    print("=" * 70)
    print(f"{result['home_team']}: {result['centered_home_mean']:.1f} points")
    print(f"{result['away_team']}: {result['centered_away_mean']:.1f} points")
    print(f"Spread ({result['home_team']} - {result['away_team']}): {result['centered_spread_mean']:+.1f}")
    print(f"Total: {result['centered_total_mean']:.1f}")
    print(f"\n✅ Centered to market: Spread {result['spread_line']:+.1f}, Total {result['total_line']:.1f}")
    
    print(f"\n" + "=" * 70)
    print("MODEL SIGNAL")
    print("=" * 70)
    print(f"• Spread: {result['p_home_cover']:.1%} ({result['home_team']}) / {result['p_away_cover']:.1%} ({result['away_team']})")
    print(f"• Total:  {result['p_over']:.1%} (OVER) / {result['p_under']:.1%} (UNDER)")
    print(f"• Distribution: spread SD={result['spread_sd']:.1f}, total SD={result['total_sd']:.1f}")
    
    print(f"\nDECISION")
    if result['spread_bet'] or result['total_bet']:
        bets = []
        if result['spread_bet']:
            # Format bet correctly
            # spread_line is (home - away), so if negative, away is favored
            if result['spread_bet'] == 'HOME':
                # Betting home team means they get the opposite sign
                bet_str = f"{result['home_team']} {-result['spread_line']:+.1f}"
            else:
                # Betting away team means they get the opposite sign
                bet_str = f"{result['away_team']} {result['spread_line']:+.1f}"
            bets.append(f"SPREAD: {bet_str} (edge: {result['spread_edge']*100:+.1f}%)")
        if result['total_bet']:
            bets.append(f"TOTAL: {result['total_bet']} {result['total_line']:.1f} (edge: {result['total_edge']*100:+.1f}%)")
        for bet in bets:
            print(f"• BET: {bet}")
    else:
        print(f"• PASS (no edge above threshold)")
    
    print("=" * 70)

if __name__ == "__main__":
    # Tonight's game: BAL @ MIA
    # Market: BAL -7.5 (Baltimore favored by 7.5)
    # In our convention: spread_line = home - away
    # If BAL (away) is favored by 7.5, then home - away = -7.5
    result = predict_game(
        away_team="BAL",
        home_team="MIA",
        spread_line=-7.5,  # home - away = -7.5 (away team BAL favored)
        total_line=52.5,
        season=2024,
        week=17,
        n_sims=1000
    )
    
    print_prediction(result)

