"""
Backtest situational factors on 2025 data (Weeks 1-8).

Measures:
- CLV Rate (% of bets that beat closing line)
- Average CLV (points)
- Win Rate
- ROI

Success Criteria:
- CLV Rate ≥55%
- Avg CLV ≥+0.5 pts
- ROI positive
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

from edge_hunt.situational_factors_fast import get_all_situational_adjustments_fast
from market_implied_scores import market_to_implied_score, implied_score_to_spread_total


def load_historical_games(weeks: List[int], season: int = 2025) -> pd.DataFrame:
    """Load historical games with opening and closing lines."""
    # Load opening/closing lines
    lines_path = Path("artifacts/opening_closing_lines_weeks_1-7_20251027.csv")
    
    if not lines_path.exists():
        print(f"❌ Lines file not found: {lines_path}")
        return pd.DataFrame()
    
    lines_df = pd.read_csv(lines_path)
    
    # Pivot to get opening and closing in same row
    opening = lines_df[lines_df['line_type'] == 'opening'][['week', 'away', 'home', 'spread', 'total']].copy()
    opening.columns = ['week', 'away', 'home', 'spread_open', 'total_open']
    
    closing = lines_df[lines_df['line_type'] == 'closing'][['week', 'away', 'home', 'spread', 'total']].copy()
    closing.columns = ['week', 'away', 'home', 'spread_close', 'total_close']
    
    df = opening.merge(closing, on=['week', 'away', 'home'], how='inner')
    
    # Load results from ESPN
    import requests
    from nfl_edge.team_mapping import normalize_team
    
    all_games = []
    for week in weeks:
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={week}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            for event in data.get('events', []):
                if event['status']['type']['completed']:
                    comps = event['competitions'][0]
                    away_team = comps['competitors'][1]
                    home_team = comps['competitors'][0]
                    
                    away_abbr = normalize_team(away_team['team']['abbreviation'], 'espn')
                    home_abbr = normalize_team(home_team['team']['abbreviation'], 'espn')
                    
                    all_games.append({
                        'week': week,
                        'away': away_abbr,
                        'home': home_abbr,
                        'away_score': int(away_team['score']),
                        'home_score': int(home_team['score'])
                    })
        except Exception as e:
            print(f"⚠️  Week {week}: {e}")
    
    results_df = pd.DataFrame(all_games)
    
    # Merge with results
    df = df.merge(results_df[['week', 'away', 'home', 'away_score', 'home_score']], 
                  on=['week', 'away', 'home'], how='left')
    
    # Filter to requested weeks
    df = df[df['week'].isin(weeks)]
    
    print(f"📊 Loaded {len(df)} games from weeks {min(weeks)}-{max(weeks)}")
    print(f"   {(~df['away_score'].isna()).sum()} games with results")
    
    return df


def backtest_situational_factors(df: pd.DataFrame, min_edge: float = 2.0) -> Dict:
    """
    Backtest situational factors on historical data.
    
    Args:
        df: DataFrame with historical games (must have opening/closing lines and results)
        min_edge: Minimum edge threshold for betting (points)
    
    Returns:
        Dictionary with backtest results
    """
    print(f"\n{'='*80}")
    print(f"BACKTESTING SITUATIONAL FACTORS")
    print(f"{'='*80}\n")
    
    bets = []
    
    for idx, row in df.iterrows():
        away = row['away']
        home = row['home']
        week = row['week']
        
        # Get opening lines
        open_spread = row['spread_open']
        open_total = row['total_open']
        
        # Get closing lines
        close_spread = row['spread_close']
        close_total = row['total_close']
        
        # Get actual results
        away_score = row.get('away_score', None)
        home_score = row.get('home_score', None)
        
        if pd.isna(away_score) or pd.isna(home_score):
            continue  # Game not completed
        
        # Get market-implied scores from opening lines
        market_away, market_home = market_to_implied_score(open_spread, open_total)
        
        # Get situational adjustments
        sit = get_all_situational_adjustments_fast(away, home)
        
        if not sit['has_adjustment']:
            continue  # No edge
        
        # Apply adjustments
        adj_away = market_away + (sit['total_adjustment'] / 2)
        adj_home = market_home + (sit['total_adjustment'] / 2)
        
        adj_spread, adj_total = implied_score_to_spread_total(adj_away, adj_home)
        
        # Check for betting opportunities
        
        # SPREAD
        spread_edge = abs(adj_spread - open_spread)
        if spread_edge >= min_edge:
            # Determine side
            if adj_spread < open_spread:  # We think home will cover by more
                bet_side = f"{home} {open_spread:+.1f}"
                bet_team = home
                bet_line = open_spread
            else:  # We think away will cover by more
                bet_side = f"{away} {-open_spread:+.1f}"
                bet_team = away
                bet_line = -open_spread
            
            # Calculate CLV
            if adj_spread < open_spread:  # Bet home
                clv = close_spread - open_spread
            else:  # Bet away
                clv = open_spread - close_spread
            
            # Grade bet
            actual_margin = home_score - away_score
            if bet_team == home:
                won = actual_margin > bet_line
            else:
                won = -actual_margin > bet_line
            
            bets.append({
                'week': week,
                'game': f"{away} @ {home}",
                'type': 'spread',
                'bet': bet_side,
                'open_line': open_spread,
                'close_line': close_spread,
                'edge_pts': spread_edge,
                'clv': clv,
                'won': won,
                'factors': ', '.join(sit['explanations'][:2])
            })
        
        # TOTAL
        total_edge = abs(adj_total - open_total)
        if total_edge >= min_edge:
            # Determine side
            if adj_total < open_total:  # Bet UNDER
                bet_side = f"UNDER {open_total:.1f}"
                clv = open_total - close_total  # Positive if line moved down
            else:  # Bet OVER
                bet_side = f"OVER {open_total:.1f}"
                clv = close_total - open_total  # Positive if line moved up
            
            # Grade bet
            actual_total = away_score + home_score
            if adj_total < open_total:  # Bet UNDER
                won = actual_total < open_total
            else:  # Bet OVER
                won = actual_total > open_total
            
            bets.append({
                'week': week,
                'game': f"{away} @ {home}",
                'type': 'total',
                'bet': bet_side,
                'open_line': open_total,
                'close_line': close_total,
                'edge_pts': total_edge,
                'clv': clv,
                'won': won,
                'factors': ', '.join(sit['explanations'][:2])
            })
    
    # Calculate metrics
    if len(bets) == 0:
        print("❌ No bets generated")
        return {'bets': [], 'metrics': {}}
    
    bets_df = pd.DataFrame(bets)
    
    # CLV metrics
    clv_positive = (bets_df['clv'] > 0).sum()
    clv_rate = clv_positive / len(bets_df) * 100
    avg_clv = bets_df['clv'].mean()
    
    # Win metrics
    wins = bets_df['won'].sum()
    win_rate = wins / len(bets_df) * 100
    
    # ROI (assuming -110 odds)
    profit = wins * 0.909 - (len(bets_df) - wins) * 1.0  # Win $0.909 per $1 bet
    roi = profit / len(bets_df) * 100
    
    metrics = {
        'total_bets': len(bets_df),
        'clv_positive': clv_positive,
        'clv_rate': clv_rate,
        'avg_clv': avg_clv,
        'wins': wins,
        'losses': len(bets_df) - wins,
        'win_rate': win_rate,
        'roi': roi,
        'profit_units': profit
    }
    
    return {'bets': bets_df, 'metrics': metrics}


def print_backtest_results(results: Dict):
    """Print backtest results in a nice format."""
    metrics = results['metrics']
    bets_df = results['bets']
    
    print(f"\n{'='*80}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*80}\n")
    
    print(f"📊 BETTING ACTIVITY")
    print(f"  Total Bets: {metrics['total_bets']}")
    print(f"  Spread Bets: {(bets_df['type'] == 'spread').sum()}")
    print(f"  Total Bets: {(bets_df['type'] == 'total').sum()}")
    print()
    
    print(f"📈 CLOSING LINE VALUE (CLV)")
    print(f"  CLV Rate: {metrics['clv_rate']:.1f}% ({metrics['clv_positive']}/{metrics['total_bets']})")
    print(f"  Avg CLV: {metrics['avg_clv']:+.2f} pts")
    print(f"  {'✅ PASS' if metrics['clv_rate'] >= 55 else '❌ FAIL'} (target: ≥55%)")
    print(f"  {'✅ PASS' if metrics['avg_clv'] >= 0.5 else '❌ FAIL'} (target: ≥+0.5 pts)")
    print()
    
    print(f"🎯 WIN RATE")
    print(f"  Wins: {metrics['wins']}")
    print(f"  Losses: {metrics['losses']}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  {'✅ PASS' if metrics['win_rate'] >= 52.4 else '❌ FAIL'} (target: ≥52.4% to break even at -110)")
    print()
    
    print(f"💰 RETURN ON INVESTMENT")
    print(f"  Profit: {metrics['profit_units']:+.2f} units")
    print(f"  ROI: {metrics['roi']:+.1f}%")
    print(f"  {'✅ PASS' if metrics['roi'] > 0 else '❌ FAIL'} (target: positive)")
    print()
    
    # Show top bets by CLV
    print(f"🏆 TOP 5 BETS BY CLV")
    top_bets = bets_df.nlargest(5, 'clv')
    for idx, bet in top_bets.iterrows():
        result = "✅ WON" if bet['won'] else "❌ LOST"
        print(f"  Week {bet['week']}: {bet['game']} - {bet['bet']}")
        print(f"    CLV: {bet['clv']:+.2f} pts | Edge: {bet['edge_pts']:.1f} pts | {result}")
        print(f"    Factors: {bet['factors']}")
        print()
    
    # Overall verdict
    print(f"{'='*80}")
    passed = (
        metrics['clv_rate'] >= 55 and
        metrics['avg_clv'] >= 0.5 and
        metrics['roi'] > 0
    )
    
    if passed:
        print("✅ VERDICT: SITUATIONAL FACTORS HAVE EDGE - DEPLOY TO PRODUCTION")
    else:
        print("❌ VERDICT: SITUATIONAL FACTORS ALREADY PRICED - DO NOT USE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # Backtest on 2025 Weeks 1-7
    df = load_historical_games(weeks=list(range(1, 8)), season=2025)
    
    if len(df) > 0:
        results = backtest_situational_factors(df, min_edge=2.0)
        print_backtest_results(results)
        
        # Save results
        if len(results['bets']) > 0:
            results['bets'].to_csv('artifacts/backtest_situational_2025.csv', index=False)
            print(f"💾 Saved detailed results to: artifacts/backtest_situational_2025.csv")
    else:
        print("❌ No historical data available for backtesting")
        print("   Run fetch_real_closing_lines.py first to get historical data")

