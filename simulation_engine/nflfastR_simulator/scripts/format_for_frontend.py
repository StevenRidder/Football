"""
Convert backtest results to frontend-compatible format.

Reads backtest_all_games_conviction.csv and formats it for the Flask frontend.
"""
import pandas as pd
import numpy as np
from pathlib import Path

def format_conviction_badge(conviction):
    """Convert conviction level to Tabler badge class."""
    if pd.isna(conviction) or conviction is None:
        return None
    
    conviction = str(conviction).upper()
    if conviction == 'HIGH':
        return 'bg-danger'  # Red badge for high conviction
    elif conviction == 'MEDIUM':
        return 'bg-warning'  # Yellow badge for medium conviction
    elif conviction == 'LOW':
        return 'bg-secondary'  # Gray badge for low conviction
    return None

def format_spread_bet(bet):
    """Format spread bet recommendation."""
    if pd.isna(bet) or bet is None:
        return 'Pass'
    
    bet = str(bet).upper()
    if bet == 'HOME':
        return 'Home ATS'
    elif bet == 'AWAY':
        return 'Away ATS'
    return 'Pass'

def format_total_bet(bet):
    """Format total bet recommendation."""
    if pd.isna(bet) or bet is None:
        return 'Pass'
    
    bet = str(bet).upper()
    if bet == 'OVER':
        return 'Over'
    elif bet == 'UNDER':
        return 'Under'
    return 'Pass'

def format_result(result):
    """Convert numeric result (1=WIN, 0=LOSS, NaN=PUSH/None) to text."""
    if pd.isna(result):
        return None
    
    if result == 1.0:
        return 'WIN'
    elif result == 0.0:
        return 'LOSS'
    return None

def convert_backtest_to_frontend(input_file, output_file):
    """
    Convert backtest CSV to frontend-compatible format.
    
    Expected input columns from backtest_all_games_conviction.py:
    - away_team, home_team, season, week
    - spread_line, closing_total (market_total)
    - home_score_mean, away_score_mean (raw predictions)
    - home_score, away_score (actual scores if available)
    - spread_bet, total_bet (HOME/AWAY/OVER/UNDER)
    - spread_edge, total_edge
    - spread_conviction, total_conviction (HIGH/MEDIUM/LOW)
    - spread_result, total_result (1.0=WIN, 0.0=LOSS, NaN=PUSH)
    
    Output format matches alpha_index_v3.html expectations:
    - away_team, home_team, week
    - closing_spread, closing_total (market lines)
    - our_spread, our_total (model predictions)
    - spread_recommendation, total_recommendation (formatted bets)
    - spread_conviction, total_conviction (HIGH/MEDIUM/LOW)
    - spread_conviction_badge, total_conviction_badge (Tabler badge classes)
    - spread_result, total_result (WIN/LOSS/None)
    - spread_edge_pct, total_edge_pct (as percentages)
    - final_score, is_completed
    """
    print(f"📂 Loading backtest results from: {input_file}")
    df = pd.read_csv(input_file)
    
    print(f"   Loaded {len(df)} games")
    
    # Create frontend-compatible DataFrame
    frontend_df = pd.DataFrame()
    
    # Basic game info
    frontend_df['away_team'] = df['away_team']
    frontend_df['home_team'] = df['home_team']
    frontend_df['week'] = df['week']
    frontend_df['season'] = df.get('season', 2025)
    
    # Market lines - CRITICAL: Use total_line from backtest (Odds API data)
    # Backtest CSV uses total_line (from Odds API), not closing_total
    # Priority: closing_total > total_line > market_total > 45.0 (fallback)
    frontend_df['closing_spread'] = df.get('spread_line', df.get('market_spread', 0.0))
    
    # For totals, check multiple column names in priority order
    if 'closing_total' in df.columns:
        frontend_df['closing_total'] = df['closing_total']
    elif 'total_line' in df.columns:
        # CRITICAL FIX: Backtest uses total_line (from Odds API), use that!
        frontend_df['closing_total'] = df['total_line']
        print(f"   ✅ Using total_line column for closing_total (Odds API data)")
    elif 'market_total' in df.columns:
        frontend_df['closing_total'] = df['market_total']
    else:
        print(f"   ⚠️  WARNING: No total column found, using 45.0 default")
        frontend_df['closing_total'] = 45.0
    
    # Verify we're not using all 45.0 values
    unique_totals = frontend_df['closing_total'].unique()
    if len(unique_totals) == 1 and unique_totals[0] == 45.0:
        print(f"   ⚠️  WARNING: All closing_totals are 45.0 - may be placeholder!")
    else:
        print(f"   ✅ Closing totals range: {frontend_df['closing_total'].min():.1f} to {frontend_df['closing_total'].max():.1f}")
    
    frontend_df['opening_spread'] = df.get('opening_spread', frontend_df['closing_spread'])
    frontend_df['opening_total'] = df.get('opening_total', frontend_df['closing_total'])
    
    # Model predictions (centered scores - these are what we use for betting)
    # Handle both formats: week 9 has direct scores, backtest has spread/total means
    frontend_df['our_home_score'] = None
    frontend_df['our_away_score'] = None
    
    # Try direct scores first (week 9 format)
    if 'home_score_mean' in df.columns:
        frontend_df['our_home_score'] = df['home_score_mean']
    if 'away_score_mean' in df.columns:
        frontend_df['our_away_score'] = df['away_score_mean']
    
    # Reconstruct from spread/total for rows missing direct scores (backtest format)
    if 'spread_mean' in df.columns and 'total_mean' in df.columns:
        missing_home = frontend_df['our_home_score'].isna()
        missing_away = frontend_df['our_away_score'].isna()
        
        if missing_home.any():
            frontend_df.loc[missing_home, 'our_home_score'] = (
                (df.loc[missing_home, 'total_mean'] + df.loc[missing_home, 'spread_mean']) / 2.0
            )
        if missing_away.any():
            frontend_df.loc[missing_away, 'our_away_score'] = (
                (df.loc[missing_away, 'total_mean'] - df.loc[missing_away, 'spread_mean']) / 2.0
            )
    
    # Final fallback (shouldn't happen)
    frontend_df['our_home_score'] = frontend_df['our_home_score'].fillna(df.get('predicted_home_score', 24.0))
    frontend_df['our_away_score'] = frontend_df['our_away_score'].fillna(df.get('predicted_away_score', 21.0))
    frontend_df['our_spread'] = frontend_df['our_home_score'] - frontend_df['our_away_score']
    frontend_df['our_total'] = frontend_df['our_home_score'] + frontend_df['our_away_score']
    
    # Raw simulator scores (before market centering) - for display/debugging
    # Try multiple column names for backcompat
    frontend_df['our_home_score_raw'] = df.get('home_score_raw', 
                                               df.get('home_score_raw_mean', None))
    frontend_df['our_away_score_raw'] = df.get('away_score_raw',
                                               df.get('away_score_raw_mean', None))
    
    # If we have spread_raw/total_raw, reconstruct raw scores
    if 'spread_raw' in df.columns and 'total_raw' in df.columns:
        # Always reconstruct from spread_raw/total_raw (more reliable)
        frontend_df['our_home_score_raw'] = (df['total_raw'] + df['spread_raw']) / 2.0
        frontend_df['our_away_score_raw'] = (df['total_raw'] - df['spread_raw']) / 2.0
    
    # Distribution metrics (THE ACTUAL EDGE - from shape, not mean)
    frontend_df['p_home_cover'] = df.get('p_home_cover', None)
    frontend_df['p_away_cover'] = df.get('p_away_cover', None)
    frontend_df['p_over'] = df.get('p_over', None)
    frontend_df['p_under'] = df.get('p_under', None)
    frontend_df['spread_std'] = df.get('spread_std', None)
    frontend_df['total_std'] = df.get('total_std', None)
    frontend_df['blowout_prob'] = df.get('blowout_prob', None)
    frontend_df['close_game_prob'] = df.get('close_game_prob', None)
    
    # Actual scores (if available) - try multiple column name variations
    if 'actual_home_score' in df.columns:
        frontend_df['actual_home_score'] = df['actual_home_score']
    elif 'home_score' in df.columns:
        frontend_df['actual_home_score'] = df['home_score']
    else:
        frontend_df['actual_home_score'] = None
    
    if 'actual_away_score' in df.columns:
        frontend_df['actual_away_score'] = df['actual_away_score']
    elif 'away_score' in df.columns:
        frontend_df['actual_away_score'] = df['away_score']
    else:
        frontend_df['actual_away_score'] = None
    
    # Format final score
    has_results = frontend_df['actual_home_score'].notna() & frontend_df['actual_away_score'].notna()
    frontend_df['final_score'] = None
    frontend_df.loc[has_results, 'final_score'] = (
        frontend_df.loc[has_results, 'actual_away_score'].astype(int).astype(str) + '-' +
        frontend_df.loc[has_results, 'actual_home_score'].astype(int).astype(str)
    )
    frontend_df['is_completed'] = has_results
    
    # Bet recommendations
    frontend_df['spread_recommendation'] = df['spread_bet'].apply(format_spread_bet)
    frontend_df['total_recommendation'] = df['total_bet'].apply(format_total_bet)
    
    # Conviction levels (keep original values)
    frontend_df['spread_conviction'] = df.get('spread_conviction', None)
    frontend_df['total_conviction'] = df.get('total_conviction', None)
    
    # Badge classes for convictions
    frontend_df['spread_conviction_badge'] = frontend_df['spread_conviction'].apply(format_conviction_badge)
    frontend_df['total_conviction_badge'] = frontend_df['total_conviction'].apply(format_conviction_badge)
    
    # Results (WIN/LOSS/None)
    frontend_df['spread_result'] = df.get('spread_result', None).apply(format_result)
    frontend_df['total_result'] = df.get('total_result', None).apply(format_result)
    
    # Edge percentages
    frontend_df['spread_edge_pct'] = (df.get('spread_edge', 0.0) * 100).round(1)
    frontend_df['total_edge_pct'] = (df.get('total_edge', 0.0) * 100).round(1)
    
    # Confidence (use edge as proxy, converted to 0-1 scale)
    # Edge of 0.04 (4%) = 0.54 confidence, Edge of 0.08 (8%) = 0.58 confidence
    max_edge = 0.10  # 10% edge = max confidence
    frontend_df['spread_rec_confidence'] = (0.50 + frontend_df['spread_edge_pct'] / 100.0 * 4.0).clip(0.0, 1.0)
    frontend_df['total_rec_confidence'] = (0.50 + frontend_df['total_edge_pct'] / 100.0 * 4.0).clip(0.0, 1.0)
    
    # Calculate market-implied scores from spread/total lines
    # CRITICAL: Always calculate market scores when we have valid lines, even for future games
    has_valid_lines = frontend_df['closing_total'].notna() & (frontend_df['closing_total'] > 20) & (frontend_df['closing_total'] < 80)
    has_valid_spread = frontend_df['closing_spread'].notna() & (frontend_df['closing_spread'].abs() < 30)
    
    # Initialize market scores (will be NaN for games without valid lines)
    frontend_df['closing_away_score'] = None
    frontend_df['closing_home_score'] = None
    
    valid_idx = has_valid_lines & has_valid_spread
    if valid_idx.any():
        # Market-implied scores: derived from closing_total and closing_spread
        frontend_df.loc[valid_idx, 'closing_away_score'] = (
            frontend_df.loc[valid_idx, 'closing_total'] / 2.0 - 
            frontend_df.loc[valid_idx, 'closing_spread'] / 2.0
        )
        frontend_df.loc[valid_idx, 'closing_home_score'] = (
            frontend_df.loc[valid_idx, 'closing_total'] / 2.0 + 
            frontend_df.loc[valid_idx, 'closing_spread'] / 2.0
        )
    
    # Also try to get market scores from existing columns if available
    if 'market_home_score' in frontend_df.columns:
        missing_home = frontend_df['closing_home_score'].isna() & frontend_df['market_home_score'].notna()
        frontend_df.loc[missing_home, 'closing_home_score'] = frontend_df.loc[missing_home, 'market_home_score']
    if 'market_away_score' in frontend_df.columns:
        missing_away = frontend_df['closing_away_score'].isna() & frontend_df['market_away_score'].notna()
        frontend_df.loc[missing_away, 'closing_away_score'] = frontend_df.loc[missing_away, 'market_away_score']
    
    # Line movements
    frontend_df['spread_movement'] = frontend_df['closing_spread'] - frontend_df['opening_spread']
    frontend_df['total_movement'] = frontend_df['closing_total'] - frontend_df['opening_total']
    
    # Game date (if available)
    frontend_df['game_date'] = df.get('game_date', None)
    
    # Replace NaN with None for JSON serialization
    frontend_df = frontend_df.replace({pd.NA: None, float('nan'): None, np.nan: None})
    
    # Save to CSV
    output_file.parent.mkdir(parents=True, exist_ok=True)
    frontend_df.to_csv(output_file, index=False)
    
    print(f"✅ Formatted {len(frontend_df)} games")
    print(f"💾 Saved to: {output_file}")
    
    # Print summary
    spread_bets = frontend_df[frontend_df['spread_recommendation'] != 'Pass']
    total_bets = frontend_df[frontend_df['total_recommendation'] != 'Pass']
    
    print(f"\n📊 Summary:")
    print(f"   Spread bets: {len(spread_bets)}")
    print(f"   Total bets: {len(total_bets)}")
    
    if len(spread_bets) > 0:
        high_conv = spread_bets[spread_bets['spread_conviction'] == 'HIGH']
        med_conv = spread_bets[spread_bets['spread_conviction'] == 'MEDIUM']
        low_conv = spread_bets[spread_bets['spread_conviction'] == 'LOW']
        print(f"   Spread convictions: HIGH={len(high_conv)}, MEDIUM={len(med_conv)}, LOW={len(low_conv)}")
    
    if len(total_bets) > 0:
        high_conv = total_bets[total_bets['total_conviction'] == 'HIGH']
        med_conv = total_bets[total_bets['total_conviction'] == 'MEDIUM']
        low_conv = total_bets[total_bets['total_conviction'] == 'LOW']
        print(f"   Total convictions: HIGH={len(high_conv)}, MEDIUM={len(med_conv)}, LOW={len(low_conv)}")
    
    completed = frontend_df[frontend_df['is_completed'] == True]
    if len(completed) > 0:
        spread_wins = (completed['spread_result'] == 'WIN').sum()
        spread_losses = (completed['spread_result'] == 'LOSS').sum()
        total_wins = (completed['total_result'] == 'WIN').sum()
        total_losses = (completed['total_result'] == 'LOSS').sum()
        print(f"\n   Completed games: {len(completed)}")
        print(f"   Spread: {spread_wins}W-{spread_losses}L")
        print(f"   Total: {total_wins}W-{total_losses}L")
    
    return frontend_df

if __name__ == "__main__":
    import sys
    import glob
    
    # Default paths
    script_dir = Path(__file__).parent.parent
    base_output_file = Path(__file__).parent.parent.parent.parent / "artifacts" / "simulator_predictions.csv"
    
    # Look for backtest files (weeks 1-8)
    backtest_file = script_dir / "artifacts" / "backtest_all_games_conviction.csv"
    week9_file = script_dir / "artifacts" / "backtest_week9_predictions.csv"
    
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
        convert_backtest_to_frontend(input_file, base_output_file)
    else:
        # Combine weeks 1-8 and week 9 if available
        dfs = []
        
        if backtest_file.exists():
            print(f"📂 Loading weeks 1-8 from: {backtest_file}")
            df_weeks18 = pd.read_csv(backtest_file)
            dfs.append(df_weeks18)
        
        # CRITICAL: Only load ONE source for weeks 9-10 to avoid duplicates
        # Prefer backtest_week9_10_predictions.csv (newer, correct) over backtest_week9_predictions.csv (old, wrong)
        week9_10_file = script_dir / "artifacts" / "backtest_week9_10_predictions.csv"
        if week9_10_file.exists():
            print(f"📂 Loading weeks 9-10 from: {week9_10_file}")
            df_week9_10 = pd.read_csv(week9_10_file)
            dfs.append(df_week9_10)
        elif week9_file.exists():
            print(f"⚠️  Loading week 9 from: {week9_file} (OLD FILE - prefer backtest_week9_10_predictions.csv)")
            df_week9 = pd.read_csv(week9_file)
            dfs.append(df_week9)
        
        if not dfs:
            print(f"❌ Error: No backtest files found")
            print(f"   Expected:")
            print(f"     - {backtest_file} (weeks 1-8)")
            print(f"     - {week9_10_file} (weeks 9-10, preferred)")
            print(f"   Run backtest_all_games_conviction.py and generate_week9_10_predictions.py")
            sys.exit(1)
        
        # Combine all weeks
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # CRITICAL: Remove duplicates - keep the most recent row for each game
        # Deduplicate by season, week, away_team, home_team
        print(f"\n🔍 Checking for duplicates...")
        before_count = len(df_combined)
        
        # Sort by source priority (week9_10 > week9 > backtest) then drop duplicates
        # We'll keep the last occurrence which should be from the newer files
        df_combined = df_combined.drop_duplicates(
            subset=['season', 'week', 'away_team', 'home_team'],
            keep='last'  # Keep the last (newest) duplicate
        )
        
        after_count = len(df_combined)
        if before_count != after_count:
            print(f"   ⚠️  Removed {before_count - after_count} duplicate rows")
        else:
            print(f"   ✅ No duplicates found")
        
        # Save temporary combined file
        temp_file = script_dir / "artifacts" / "backtest_combined_temp.csv"
        df_combined.to_csv(temp_file, index=False)
        
        # Format combined data
        convert_backtest_to_frontend(temp_file, base_output_file)
        
        # Clean up temp file
        temp_file.unlink()

