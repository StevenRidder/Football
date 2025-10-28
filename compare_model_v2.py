#!/usr/bin/env python3
"""
Compare Model v1 (old) vs Model v2 (new) on Week 8 data.

Model v1:
- recent_weight = 0.67
- No turnover differential

Model v2:
- recent_weight = 0.85
- Turnover differential feature added
"""

import pandas as pd
import requests
from pathlib import Path

# Team abbreviation mapping
TEAM_MAP = {
    'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
    'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
    'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
    'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
    'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS'
}

def fetch_actual_results():
    """Fetch Week 8 actual results from ESPN"""
    url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
    response = requests.get(url)
    data = response.json()
    
    results = []
    for game in data.get('events', []):
        competitions = game.get('competitions', [])
        if not competitions:
            continue
        
        comp = competitions[0]
        status = comp.get('status', {}).get('type', {}).get('name', '')
        
        if status != 'STATUS_FINAL':
            continue
        
        competitors = comp.get('competitors', [])
        if len(competitors) < 2:
            continue
        
        home_team = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
        away_team = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
        
        home_abbr = TEAM_MAP.get(home_team['team']['displayName'], home_team['team']['abbreviation'])
        away_abbr = TEAM_MAP.get(away_team['team']['displayName'], away_team['team']['abbreviation'])
        
        home_score = int(home_team.get('score', 0))
        away_score = int(away_team.get('score', 0))
        
        results.append({
            'away': away_abbr,
            'home': home_abbr,
            'away_score': away_score,
            'home_score': home_score,
            'actual_margin': home_score - away_score,
            'actual_total': home_score + away_score,
            'winner': home_abbr if home_score > away_score else away_abbr
        })
    
    return pd.DataFrame(results)

def evaluate_model(pred_file, actual_df):
    """Evaluate a model's predictions against actual results"""
    df = pd.read_csv(pred_file)
    
    results = []
    for _, pred in df.iterrows():
        # Find matching actual game
        actual = actual_df[(actual_df['away'] == pred['away']) & (actual_df['home'] == pred['home'])]
        
        if len(actual) == 0:
            continue
        
        actual = actual.iloc[0]
        
        # Parse predicted score
        exp_score = pred['Exp score (away-home)']
        scores = exp_score.split('-')
        pred_away = float(scores[0])
        pred_home = float(scores[1])
        pred_margin = pred_home - pred_away
        pred_total = pred_away + pred_home
        pred_winner = pred['home'] if pred_home > pred_away else pred['away']
        
        # Calculate errors
        margin_error = abs(actual['actual_margin'] - pred_margin)
        total_error = abs(actual['actual_total'] - pred_total)
        winner_correct = (pred_winner == actual['winner'])
        
        # Check spread bet (if we made one)
        spread_rec = pred['Rec_spread']
        spread_bet_won = None
        if 'SKIP' not in spread_rec:
            market_spread = pred['Spread used (home-)']
            # If market spread is positive, home is underdog
            if market_spread > 0:
                # Bet was on home team as underdog
                spread_bet_won = (actual['home_score'] + market_spread) > actual['away_score']
            else:
                # Bet was on away team as underdog
                spread_bet_won = (actual['away_score'] - market_spread) > actual['home_score']
        
        results.append({
            'game': f"{pred['away']}@{pred['home']}",
            'pred_margin': pred_margin,
            'actual_margin': actual['actual_margin'],
            'margin_error': margin_error,
            'pred_total': pred_total,
            'actual_total': actual['actual_total'],
            'total_error': total_error,
            'winner_correct': winner_correct,
            'spread_bet_won': spread_bet_won
        })
    
    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("MODEL v1 vs v2 COMPARISON - Week 8")
    print("=" * 80)
    print()
    
    # Fetch actual results
    print("Fetching actual Week 8 results...")
    actual_df = fetch_actual_results()
    print(f"Found {len(actual_df)} completed games")
    print()
    
    # Load old model predictions (v1)
    v1_file = Path("artifacts/predictions_2025_2025-10-26_v1.csv")
    if not v1_file.exists():
        # Backup the current file as v1
        current_file = Path("artifacts/predictions_2025_2025-10-26.csv")
        if current_file.exists():
            print("Backing up current predictions as v1...")
            import shutil
            shutil.copy(current_file, v1_file)
    
    # Run new model (v2)
    print("Running Model v2 (with improvements)...")
    from nfl_edge.main import run_week
    proj, clv, dbg, bets = run_week()
    v2_file = Path(proj)
    print(f"Generated: {v2_file}")
    print()
    
    # Evaluate both models
    print("=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)
    print()
    
    if v1_file.exists():
        print("MODEL v1 (Old):")
        print("  - recent_weight = 0.67")
        print("  - No turnover differential")
        print()
        v1_results = evaluate_model(v1_file, actual_df)
        
        print(f"Games: {len(v1_results)}")
        print(f"Winner Accuracy: {v1_results['winner_correct'].sum()}/{len(v1_results)} ({100*v1_results['winner_correct'].mean():.1f}%)")
        print(f"Avg Margin Error: {v1_results['margin_error'].mean():.1f} points")
        print(f"Avg Total Error: {v1_results['total_error'].mean():.1f} points")
        
        bet_results = v1_results[v1_results['spread_bet_won'].notna()]
        if len(bet_results) > 0:
            bet_wins = bet_results['spread_bet_won'].sum()
            print(f"Spread Bets: {int(bet_wins)}/{len(bet_results)} ({100*bet_wins/len(bet_results):.1f}%)")
            profit_v1 = (bet_wins * 90.91) - ((len(bet_results) - bet_wins) * 100)
            print(f"Profit/Loss: ${profit_v1:.2f}")
            print(f"ROI: {100*profit_v1/(len(bet_results)*100):.1f}%")
        print()
    else:
        print("MODEL v1 predictions not found (first run)")
        print()
        v1_results = None
        profit_v1 = None
    
    print("MODEL v2 (New):")
    print("  - recent_weight = 0.85")
    print("  - Turnover differential feature")
    print()
    v2_results = evaluate_model(v2_file, actual_df)
    
    print(f"Games: {len(v2_results)}")
    print(f"Winner Accuracy: {v2_results['winner_correct'].sum()}/{len(v2_results)} ({100*v2_results['winner_correct'].mean():.1f}%)")
    print(f"Avg Margin Error: {v2_results['margin_error'].mean():.1f} points")
    print(f"Avg Total Error: {v2_results['total_error'].mean():.1f} points")
    
    bet_results = v2_results[v2_results['spread_bet_won'].notna()]
    if len(bet_results) > 0:
        bet_wins = bet_results['spread_bet_won'].sum()
        print(f"Spread Bets: {int(bet_wins)}/{len(bet_results)} ({100*bet_wins/len(bet_results):.1f}%)")
        profit_v2 = (bet_wins * 90.91) - ((len(bet_results) - bet_wins) * 100)
        print(f"Profit/Loss: ${profit_v2:.2f}")
        print(f"ROI: {100*profit_v2/(len(bet_results)*100):.1f}%")
    print()
    
    # Comparison
    if v1_results is not None:
        print("=" * 80)
        print("IMPROVEMENT")
        print("=" * 80)
        print()
        
        winner_diff = v2_results['winner_correct'].mean() - v1_results['winner_correct'].mean()
        margin_diff = v1_results['margin_error'].mean() - v2_results['margin_error'].mean()
        
        print(f"Winner Accuracy: {winner_diff:+.1%}")
        print(f"Margin Error: {margin_diff:+.1f} points (negative = better)")
        
        if profit_v1 is not None and profit_v2 is not None:
            profit_diff = profit_v2 - profit_v1
            print(f"Profit: ${profit_diff:+.2f}")
            print()
            
            if profit_diff > 0:
                print("✅ Model v2 is MORE PROFITABLE")
            elif profit_diff < 0:
                print("❌ Model v2 is LESS PROFITABLE")
            else:
                print("➖ Models have EQUAL profitability")

if __name__ == "__main__":
    main()

