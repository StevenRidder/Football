#!/usr/bin/env python3
"""
Grade historical predictions for weeks 1-7 against actual results
"""
import pandas as pd
import requests
from pathlib import Path


def fetch_espn_scores(season: int, week: int):
    """Fetch actual scores from ESPN for a specific week"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        params = {'seasontype': 2, 'week': week, 'year': season}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            scores = {}
            
            for event in data.get('events', []):
                competition = event.get('competitions', [{}])[0]
                competitors = competition.get('competitors', [])
                status = competition.get('status', {}).get('type', {}).get('completed', False)
                
                if len(competitors) >= 2 and status:
                    home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
                    away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
                    
                    home_abbr = home.get('team', {}).get('abbreviation')
                    away_abbr = away.get('team', {}).get('abbreviation')
                    home_score = int(home.get('score', 0))
                    away_score = int(away.get('score', 0))
                    
                    if home_abbr and away_abbr:
                        # Map ESPN to nflverse abbreviations
                        espn_to_nflverse = {'WSH': 'WAS', 'LAR': 'LA'}
                        home_abbr = espn_to_nflverse.get(home_abbr, home_abbr)
                        away_abbr = espn_to_nflverse.get(away_abbr, away_abbr)
                        
                        scores[(away_abbr, home_abbr)] = {
                            'away_score': away_score,
                            'home_score': home_score,
                            'total': away_score + home_score,
                            'home_margin': home_score - away_score
                        }
            
            return scores
    except Exception as e:
        print(f"Error fetching scores for week {week}: {e}")
        return {}


def grade_predictions(predictions_df, actual_scores):
    """Grade predictions against actual results"""
    results = []
    
    for _, pred in predictions_df.iterrows():
        away = pred['away']
        home = pred['home']
        
        actual = actual_scores.get((away, home))
        if not actual:
            continue
        
        # Extract predicted scores
        exp_score = pred.get('Exp score (away-home)', pred.get('exp_score', ''))
        if '-' in str(exp_score):
            pred_away, pred_home = map(float, str(exp_score).split('-'))
        else:
            continue
        
        # Actual results
        actual_away = actual['away_score']
        actual_home = actual['home_score']
        actual_total = actual['total']
        actual_margin = actual['home_margin']
        
        # Model predictions
        model_spread = pred.get('Model spread home-', pred.get('model_spread', 0))
        model_total = pred.get('Model total', pred_away + pred_home)
        spread_used = pred.get('Spread used (home-)', pred.get('spread_used', None))
        
        # Grade winner prediction
        pred_winner = home if pred_home > pred_away else away
        actual_winner = home if actual_home > actual_away else away
        winner_correct = pred_winner == actual_winner
        
        # Grade spread prediction (did home team cover the model spread?)
        # Model spread is negative if home favored
        # Home covers if: actual_margin > model_spread (when home favored)
        spread_error = abs(model_spread - actual_margin)
        
        # Grade total prediction
        total_error = abs(model_total - actual_total)
        
        # Grade against betting lines (if available)
        spread_bet_correct = None
        total_bet_correct = None
        
        if pd.notna(spread_used):
            # Did the home team cover the spread used?
            home_covered = actual_margin > spread_used
            # Model recommended home if model_spread > spread_used (home undervalued)
            model_recommended_home = model_spread > spread_used
            spread_bet_correct = home_covered == model_recommended_home
        
        results.append({
            'away': away,
            'home': home,
            'pred_score': f"{pred_away:.1f}-{pred_home:.1f}",
            'actual_score': f"{actual_away}-{actual_home}",
            'winner_correct': winner_correct,
            'spread_error': spread_error,
            'total_error': total_error,
            'model_spread': model_spread,
            'actual_margin': actual_margin,
            'model_total': model_total,
            'actual_total': actual_total,
            'spread_bet_correct': spread_bet_correct
        })
    
    return pd.DataFrame(results)


def main():
    print("="*80)
    print("GRADING HISTORICAL PREDICTIONS (Weeks 1-7 of 2025)")
    print("="*80)
    
    all_results = []
    week_summaries = []
    
    for week in range(1, 8):
        print(f"\n{'='*80}")
        print(f"Week {week}")
        print(f"{'='*80}")
        
        # Load predictions
        pred_file = Path(f"artifacts/predictions_2025_week{week}_2025-10-26.csv")
        if not pred_file.exists():
            print(f"❌ Predictions file not found: {pred_file}")
            continue
        
        predictions = pd.read_csv(pred_file)
        
        # Fetch actual scores
        print("Fetching actual scores from ESPN...")
        actual_scores = fetch_espn_scores(2025, week)
        
        if not actual_scores:
            print(f"❌ No actual scores found for week {week}")
            continue
        
        print(f"Found {len(actual_scores)} completed games")
        
        # Grade predictions
        graded = grade_predictions(predictions, actual_scores)
        
        if graded.empty:
            print(f"❌ No games to grade for week {week}")
            continue
        
        # Calculate statistics
        winner_accuracy = graded['winner_correct'].mean() * 100
        avg_spread_error = graded['spread_error'].mean()
        avg_total_error = graded['total_error'].mean()
        
        spread_bets = graded[graded['spread_bet_correct'].notna()]
        spread_bet_accuracy = spread_bets['spread_bet_correct'].mean() * 100 if not spread_bets.empty else 0
        
        print(f"\n📊 Week {week} Results:")
        print(f"   Games graded: {len(graded)}")
        print(f"   Winner accuracy: {winner_accuracy:.1f}%")
        print(f"   Avg spread error: {avg_spread_error:.2f} points")
        print(f"   Avg total error: {avg_total_error:.2f} points")
        if not spread_bets.empty:
            print(f"   Spread bet accuracy: {spread_bet_accuracy:.1f}% ({len(spread_bets)} bets)")
        
        # Show biggest misses
        print("\n   Biggest spread misses:")
        worst_spread = graded.nlargest(3, 'spread_error')[['away', 'home', 'pred_score', 'actual_score', 'spread_error']]
        for _, row in worst_spread.iterrows():
            print(f"      {row['away']}@{row['home']}: Pred {row['pred_score']}, Actual {row['actual_score']} (off by {row['spread_error']:.1f})")
        
        # Store results
        graded['week'] = week
        all_results.append(graded)
        
        week_summaries.append({
            'week': week,
            'games': len(graded),
            'winner_accuracy': winner_accuracy,
            'avg_spread_error': avg_spread_error,
            'avg_total_error': avg_total_error,
            'spread_bet_accuracy': spread_bet_accuracy,
            'spread_bets': len(spread_bets)
        })
    
    # Overall summary
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        summary_df = pd.DataFrame(week_summaries)
        
        print(f"\n{'='*80}")
        print("OVERALL SUMMARY (Weeks 1-7)")
        print(f"{'='*80}")
        print(f"\nTotal games graded: {len(combined)}")
        print(f"Overall winner accuracy: {combined['winner_correct'].mean() * 100:.1f}%")
        print(f"Overall avg spread error: {combined['spread_error'].mean():.2f} points")
        print(f"Overall avg total error: {combined['total_error'].mean():.2f} points")
        
        spread_bets_all = combined[combined['spread_bet_correct'].notna()]
        if not spread_bets_all.empty:
            print(f"Overall spread bet accuracy: {spread_bets_all['spread_bet_correct'].mean() * 100:.1f}% ({len(spread_bets_all)} bets)")
        
        print("\n📈 Week-by-Week Breakdown:")
        print(summary_df.to_string(index=False))
        
        # Save detailed results
        output_file = Path("artifacts/historical_grading_weeks_1-7.csv")
        combined.to_csv(output_file, index=False)
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        summary_file = Path("artifacts/historical_summary_weeks_1-7.csv")
        summary_df.to_csv(summary_file, index=False)
        print(f"💾 Summary saved to: {summary_file}")
        
        print(f"\n{'='*80}")


if __name__ == "__main__":
    main()

