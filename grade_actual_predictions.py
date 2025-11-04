"""
Grade ACTUAL predictions from simulator_predictions.csv
Shows how your real predictions performed (not re-simulated)
"""
import pandas as pd
from pathlib import Path

def grade_actual_predictions():
    # Load actual predictions
    preds_file = Path("artifacts/simulator_predictions.csv")
    df = pd.read_csv(preds_file)
    
    # Filter to completed games
    df = df[df['is_completed'] == True].copy()
    
    print("=" * 70)
    print("ACTUAL PREDICTIONS PERFORMANCE")
    print("=" * 70)
    print(f"\nTotal completed games: {len(df)}")
    print(f"Weeks: {sorted(df['week'].unique())}")
    
    # Grade spread bets
    spread_bets = df[df['spread_recommendation'].notna()].copy()
    
    spread_results = []
    for _, row in spread_bets.iterrows():
        rec = row['spread_recommendation']
        spread_line = row['closing_spread']
        actual_spread = row['actual_home_score'] - row['actual_away_score']
        away_team = row['away_team']
        home_team = row['home_team']
        
        # Determine which team we bet on
        # Format: "TEAM ATS" or "TEAM home" or "TEAM away"
        rec_upper = rec.upper()
        
        if away_team in rec_upper:
            # Betting on away team to cover
            result = 'WIN' if actual_spread < spread_line else ('PUSH' if actual_spread == spread_line else 'LOSS')
        elif home_team in rec_upper:
            # Betting on home team to cover  
            result = 'WIN' if actual_spread > spread_line else ('PUSH' if actual_spread == spread_line else 'LOSS')
        else:
            result = 'UNKNOWN'
        
        spread_results.append({
            'week': row['week'],
            'conviction': row['spread_conviction'],
            'result': result
        })
    
    spread_df = pd.DataFrame(spread_results)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 SPREAD BETS PERFORMANCE")
    print("=" * 70)
    
    for conviction in ['HIGH', 'MEDIUM', 'LOW', 'ALL']:
        if conviction == 'ALL':
            conv_bets = spread_df
        else:
            conv_bets = spread_df[spread_df['conviction'] == conviction]
        
        if len(conv_bets) > 0:
            wins = (conv_bets['result'] == 'WIN').sum()
            losses = (conv_bets['result'] == 'LOSS').sum()
            pushes = (conv_bets['result'] == 'PUSH').sum()
            win_rate = 100 * wins / (wins + losses) if (wins + losses) > 0 else 0
            roi = 100 * ((wins - losses * 1.1) / len(conv_bets))
            
            label = f"{conviction} Conviction" if conviction != 'ALL' else f"{conviction} Spread Bets"
            print(f"\n{label} ({len(conv_bets)} total):")
            print(f"   {wins}W-{losses}L-{pushes}P | Win Rate: {win_rate:.1f}% | ROI: {roi:+.1f}%")
    
    # Week by week
    print("\n" + "=" * 70)
    print("WEEK BY WEEK PERFORMANCE")
    print("=" * 70)
    
    for week in sorted(spread_df['week'].unique()):
        week_bets = spread_df[spread_df['week'] == week]
        wins = (week_bets['result'] == 'WIN').sum()
        losses = (week_bets['result'] == 'LOSS').sum()
        pushes = (week_bets['result'] == 'PUSH').sum()
        win_rate = 100 * wins / (wins + losses) if (wins + losses) > 0 else 0
        
        print(f"Week {week}: {wins}W-{losses}L-{pushes}P ({win_rate:.1f}%) - {len(week_bets)} bets")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    grade_actual_predictions()

