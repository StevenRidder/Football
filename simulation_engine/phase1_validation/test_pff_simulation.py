"""
TEST THE REAL THESIS: PFF Compounding Effects in Monte Carlo Simulation

Compare two Monte Carlo simulators:
1. EPA-only (baseline)
2. EPA + PFF pressure multiplier (compounding effects)

Key metrics:
- Tail predictions (blowouts, unders)
- Win probability calibration
- Spread cover accuracy
- Total accuracy
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.special import expit as sigmoid

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
ROLLING_EPA_FILE = Path("/Users/steveridder/Git/Football/data/features/rolling_epa_2022_2025.csv")


def load_rolling_epa_data(seasons):
    """Load rolling EPA data for given seasons."""
    if not ROLLING_EPA_FILE.exists():
        raise FileNotFoundError(f"Rolling EPA data not found: {ROLLING_EPA_FILE}")
    
    df = pd.read_csv(ROLLING_EPA_FILE)
    
    # Filter to requested seasons
    df = df[df['season'].isin(seasons)]
    
    return df


def load_matchup_data():
    """Load PFF matchup metrics."""
    df = pd.read_csv(DATA_DIR / "matchup_metrics_2022_2024.csv")
    
    # Filter to completed games with spread lines
    completed = df[
        df['point_differential'].notna() & 
        df['spread_line'].notna()
    ].copy()
    
    return completed


def merge_epa_and_pff():
    """Merge EPA and PFF data for each game."""
    print("📊 Loading data...")
    
    # Load EPA
    epa_df = load_rolling_epa_data([2022, 2023, 2024])
    print(f"   EPA data: {len(epa_df)} team-weeks")
    
    # Load PFF matchup data
    pff_df = load_matchup_data()
    print(f"   PFF data: {len(pff_df)} games")
    
    # Merge EPA for away team
    merged = pd.merge(
        pff_df,
        epa_df[['season', 'week', 'team', 'off_epa_per_play', 'def_epa_per_play']],
        left_on=['season', 'week', 'away_team'],
        right_on=['season', 'week', 'team'],
        how='left'
    ).rename(columns={
        'off_epa_per_play': 'away_off_epa',
        'def_epa_per_play': 'away_def_epa'
    }).drop(columns=['team'])
    
    # Merge EPA for home team
    merged = pd.merge(
        merged,
        epa_df[['season', 'week', 'team', 'off_epa_per_play', 'def_epa_per_play']],
        left_on=['season', 'week', 'home_team'],
        right_on=['season', 'week', 'team'],
        how='left'
    ).rename(columns={
        'off_epa_per_play': 'home_off_epa',
        'def_epa_per_play': 'home_def_epa'
    }).drop(columns=['team'])
    
    # Filter to games with EPA data
    merged = merged.dropna(subset=[
        'away_off_epa', 'away_def_epa', 'home_off_epa', 'home_def_epa'
    ])
    
    print(f"   Merged: {len(merged)} games with EPA + PFF data")
    
    return merged


def simulate_drive_epa_only(off_epa, def_epa):
    """
    Simulate a single drive using EPA-only (baseline).
    This is your current production model.
    """
    # Adjust EPA for matchup
    adjusted_epa = off_epa + (def_epa * 0.3)
    adjusted_epa += np.random.normal(0, 0.08)
    
    # Score probability (calibrated to NFL reality)
    score_prob = 0.40 + (adjusted_epa * 1.0)
    score_prob = max(0.15, min(0.75, score_prob))
    
    if np.random.random() < score_prob:
        # TD vs FG
        td_prob = 0.65 + (adjusted_epa * 1.5)
        td_prob = max(0.35, min(0.85, td_prob))
        points = 7 if np.random.random() < td_prob else 3
    else:
        points = 0
    
    return points


def simulate_drive_with_pff(off_epa, def_epa, pressure_advantage):
    """
    Simulate a single drive with PFF pressure multiplier (compounding effects).
    
    Theory:
    - If DL >> OL (negative pressure_advantage for offense):
      → Higher sack rate
      → More turnovers (strip-sacks, hurried throws)
      → Shorter drives
      → Compounding: defense gets ball back faster → more opportunities
    
    - If OL >> DL (positive pressure_advantage for offense):
      → Clean pocket
      → Sustained drives
      → Higher TD rate
    """
    # Base EPA adjustment
    adjusted_epa = off_epa + (def_epa * 0.3)
    
    # PFF PRESSURE MULTIPLIER (compounding effect)
    # pressure_advantage > 0 means offense has OL advantage
    # pressure_advantage < 0 means defense has DL advantage
    pressure_multiplier = sigmoid(pressure_advantage * 0.5)  # Scale to [0, 1]
    
    # Apply compounding effects:
    # 1. EPA adjustment (pressure hurts efficiency)
    pressure_penalty = (1 - pressure_multiplier) * 0.15  # Up to -0.15 EPA if dominated
    adjusted_epa -= pressure_penalty
    
    # 2. Add variance (pressure increases chaos)
    chaos_factor = 0.08 + (abs(pressure_advantage) * 0.02)  # More variance with mismatch
    adjusted_epa += np.random.normal(0, chaos_factor)
    
    # Score probability
    score_prob = 0.40 + (adjusted_epa * 1.0)
    score_prob = max(0.15, min(0.75, score_prob))
    
    if np.random.random() < score_prob:
        # TD vs FG (pressure affects red zone efficiency)
        td_prob = 0.65 + (adjusted_epa * 1.5)
        td_prob *= (0.8 + pressure_multiplier * 0.4)  # Pressure hurts TD rate
        td_prob = max(0.35, min(0.85, td_prob))
        points = 7 if np.random.random() < td_prob else 3
    else:
        points = 0
    
    # 3. COMPOUNDING: Turnover chance (strip-sacks, hurried throws)
    # If defense dominates, small chance of turnover → 0 points + opponent gets ball
    if pressure_advantage < -2:  # Defense has big edge
        turnover_prob = 0.05 + (abs(pressure_advantage) * 0.01)
        if np.random.random() < turnover_prob:
            points = 0  # Drive ends in turnover
    
    return points


def simulate_game_epa_only(away_off_epa, away_def_epa, home_off_epa, home_def_epa, n_sims=5000):
    """Simulate game using EPA-only (baseline)."""
    results = []
    
    for _ in range(n_sims):
        # Each team gets ~12 drives
        away_score = sum([simulate_drive_epa_only(away_off_epa, home_def_epa) for _ in range(12)])
        home_score = sum([simulate_drive_epa_only(home_off_epa, away_def_epa) for _ in range(12)])
        
        results.append({
            'away_score': away_score,
            'home_score': home_score,
            'spread': away_score - home_score,
            'total': away_score + home_score
        })
    
    return pd.DataFrame(results)


def simulate_game_with_pff(away_off_epa, away_def_epa, home_off_epa, home_def_epa,
                           away_pressure_adv, home_pressure_adv, n_sims=5000):
    """Simulate game with PFF pressure multiplier (compounding effects)."""
    results = []
    
    for _ in range(n_sims):
        # Each team gets ~12 drives
        # Away offense vs home defense
        away_score = sum([
            simulate_drive_with_pff(away_off_epa, home_def_epa, away_pressure_adv)
            for _ in range(12)
        ])
        
        # Home offense vs away defense
        home_score = sum([
            simulate_drive_with_pff(home_off_epa, away_def_epa, home_pressure_adv)
            for _ in range(12)
        ])
        
        results.append({
            'away_score': away_score,
            'home_score': home_score,
            'spread': away_score - home_score,
            'total': away_score + home_score
        })
    
    return pd.DataFrame(results)


def evaluate_predictions(df, model_name):
    """Evaluate model predictions against actual outcomes."""
    results = {
        'model': model_name,
        'games': len(df),
        'spread_mae': 0,
        'total_mae': 0,
        'spread_cover_acc': 0,
        'total_cover_acc': 0,
        'win_prob_calibration': 0,
        'blowout_prediction': 0,
        'under_prediction': 0
    }
    
    spread_errors = []
    total_errors = []
    spread_covers = []
    total_covers = []
    win_probs = []
    actual_wins = []
    blowout_probs = []
    actual_blowouts = []
    under_probs = []
    actual_unders = []
    
    for idx, row in df.iterrows():
        # Get simulation results
        sim_results = row['sim_results']
        
        # Predicted spread and total (median of simulations)
        pred_spread = sim_results['spread'].median()
        pred_total = sim_results['total'].median()
        
        # Actual outcomes
        actual_spread = row['actual_spread']
        actual_total = row['away_score'] + row['home_score']
        market_spread = row['spread_line']
        market_total = row['total_line']
        
        # Errors
        spread_errors.append(abs(pred_spread - actual_spread))
        total_errors.append(abs(pred_total - actual_total))
        
        # Cover accuracy (vs market spread)
        # Home covers if actual_spread < spread_line (home wins by more than expected)
        actual_home_cover = actual_spread < market_spread
        pred_home_cover_prob = (sim_results['spread'] < market_spread).mean()
        pred_home_cover = pred_home_cover_prob > 0.5
        spread_covers.append(1 if pred_home_cover == actual_home_cover else 0)
        
        # Total accuracy (vs market total)
        actual_over = actual_total > market_total
        pred_over_prob = (sim_results['total'] > market_total).mean()
        pred_over = pred_over_prob > 0.5
        total_covers.append(1 if pred_over == actual_over else 0)
        
        # Win probability calibration
        pred_home_win_prob = (sim_results['spread'] < 0).mean()
        actual_home_win = actual_spread < 0
        win_probs.append(pred_home_win_prob)
        actual_wins.append(1 if actual_home_win else 0)
        
        # Blowout prediction (>14 points)
        pred_blowout_prob = (sim_results['spread'].abs() > 14).mean()
        actual_blowout = abs(actual_spread) > 14
        blowout_probs.append(pred_blowout_prob)
        actual_blowouts.append(1 if actual_blowout else 0)
        
        # Under prediction (<40 points)
        pred_under_prob = (sim_results['total'] < 40).mean()
        actual_under = actual_total < 40
        under_probs.append(pred_under_prob)
        actual_unders.append(1 if actual_under else 0)
    
    # Calculate metrics
    results['spread_mae'] = np.mean(spread_errors)
    results['total_mae'] = np.mean(total_errors)
    results['spread_cover_acc'] = np.mean(spread_covers)
    results['total_cover_acc'] = np.mean(total_covers)
    
    # Win probability calibration (correlation between predicted prob and actual outcome)
    results['win_prob_calibration'] = np.corrcoef(win_probs, actual_wins)[0, 1]
    
    # Tail predictions (correlation)
    results['blowout_prediction'] = np.corrcoef(blowout_probs, actual_blowouts)[0, 1]
    results['under_prediction'] = np.corrcoef(under_probs, actual_unders)[0, 1]
    
    return results


def main():
    """Run the full comparison test."""
    print("="*80)
    print("TEST THE REAL THESIS: PFF Compounding Effects in Monte Carlo")
    print("="*80)
    
    # Load and merge data
    df = merge_epa_and_pff()
    
    # Limit to first 50 games for speed (can expand later)
    print(f"\n⚠️  Testing on first 50 games for speed...")
    df = df.head(50)
    
    print("\n" + "="*80)
    print("RUNNING SIMULATIONS (5000 per game)")
    print("="*80)
    
    # Run simulations for each game
    print("\n1️⃣  EPA-only (baseline)...")
    epa_results = []
    for idx, row in df.iterrows():
        sim = simulate_game_epa_only(
            row['away_off_epa'], row['away_def_epa'],
            row['home_off_epa'], row['home_def_epa']
        )
        epa_results.append(sim)
    df['epa_sim_results'] = epa_results
    
    print("2️⃣  EPA + PFF (compounding effects)...")
    pff_results = []
    for idx, row in df.iterrows():
        sim = simulate_game_with_pff(
            row['away_off_epa'], row['away_def_epa'],
            row['home_off_epa'], row['home_def_epa'],
            row['pressure_edge_away'], row['pressure_edge_home']
        )
        pff_results.append(sim)
    df['pff_sim_results'] = pff_results
    
    print("\n" + "="*80)
    print("EVALUATING PREDICTIONS")
    print("="*80)
    
    # Evaluate EPA-only
    df_epa = df.copy()
    df_epa['sim_results'] = df_epa['epa_sim_results']
    epa_metrics = evaluate_predictions(df_epa, "EPA-only")
    
    # Evaluate EPA+PFF
    df_pff = df.copy()
    df_pff['sim_results'] = df_pff['pff_sim_results']
    pff_metrics = evaluate_predictions(df_pff, "EPA+PFF")
    
    # Compare
    print("\n" + "="*80)
    print("📊 RESULTS")
    print("="*80)
    
    print(f"\n{'Metric':<30} {'EPA-only':<15} {'EPA+PFF':<15} {'Winner':<15}")
    print("-"*75)
    
    metrics = [
        ('Spread MAE', 'spread_mae', 'lower'),
        ('Total MAE', 'total_mae', 'lower'),
        ('Spread Cover Accuracy', 'spread_cover_acc', 'higher'),
        ('Total Cover Accuracy', 'total_cover_acc', 'higher'),
        ('Win Prob Calibration', 'win_prob_calibration', 'higher'),
        ('Blowout Prediction', 'blowout_prediction', 'higher'),
        ('Under Prediction', 'under_prediction', 'higher')
    ]
    
    epa_wins = 0
    pff_wins = 0
    
    for label, key, direction in metrics:
        epa_val = epa_metrics[key]
        pff_val = pff_metrics[key]
        
        if direction == 'lower':
            winner = 'EPA-only ✅' if epa_val < pff_val else 'EPA+PFF ✅'
            if epa_val < pff_val:
                epa_wins += 1
            else:
                pff_wins += 1
        else:
            winner = 'EPA-only ✅' if epa_val > pff_val else 'EPA+PFF ✅'
            if epa_val > pff_val:
                epa_wins += 1
            else:
                pff_wins += 1
        
        print(f"{label:<30} {epa_val:<15.3f} {pff_val:<15.3f} {winner:<15}")
    
    print("-"*75)
    print(f"\n🏆 Overall: EPA-only wins {epa_wins}/7, EPA+PFF wins {pff_wins}/7")
    
    # Verdict
    print("\n" + "="*80)
    print("🎯 VERDICT")
    print("="*80)
    
    if pff_wins > epa_wins:
        print("\n✅ PFF COMPOUNDING EFFECTS ADD VALUE")
        print("   → PFF pressure multiplier improves simulation accuracy")
        print("   → Worth integrating into production model")
    elif pff_wins == epa_wins:
        print("\n⚠️  TIE - PFF ADDS MARGINAL VALUE")
        print("   → PFF helps in some areas, hurts in others")
        print("   → Stick with EPA-only for simplicity")
    else:
        print("\n❌ PFF COMPOUNDING EFFECTS DO NOT HELP")
        print("   → EPA-only simulation is more accurate")
        print("   → Keep simulator lean, skip PFF")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

