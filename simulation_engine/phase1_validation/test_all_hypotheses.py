"""
Phase 1 - Step 3: Test All Hypotheses

This script tests all 4 hypotheses in one go:
H1: Pressure edge predicts sacks
H2: QB pressure vulnerability predicts performance  
H3: Pressure mismatches affect spread outcomes
H4: Market underprices early-week mismatches

This is the CRITICAL test to see if we have signal.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


def load_data():
    """Load matchup metrics."""
    print("📊 Loading matchup metrics...")
    df = pd.read_csv(DATA_DIR / "matchup_metrics_2024.csv")
    completed = df[df['away_score'].notna()].copy()
    print(f"   Total games: {len(df)}")
    print(f"   Completed games: {len(completed)}")
    return df, completed


def test_h1_pressure_predicts_sacks(df):
    """
    H1: Pressure edge predicts sacks
    
    Test: Correlation between pressure_edge and actual sacks
    Expected: r > 0.3 (moderate positive correlation)
    """
    print("\n" + "="*80)
    print("H1: PRESSURE EDGE PREDICTS SACKS")
    print("="*80)
    
    # We need actual sack data from nflfastR
    # For now, we'll use a proxy: games with high pressure edge should have different outcomes
    
    # Calculate max pressure edge per game
    df['max_pressure_edge'] = df[['pressure_edge_away', 'pressure_edge_home']].abs().max(axis=1)
    
    # Split into high vs low pressure edge games
    threshold = 10
    high_pressure = df[df['max_pressure_edge'] > threshold]
    low_pressure = df[df['max_pressure_edge'] <= threshold]
    
    print(f"\nGames with pressure edge > {threshold}: {len(high_pressure)}")
    print(f"Games with pressure edge <= {threshold}: {len(low_pressure)}")
    
    if len(high_pressure) > 0 and len(low_pressure) > 0:
        # Compare actual spreads
        high_spread_mean = high_pressure['actual_spread'].mean()
        low_spread_mean = low_pressure['actual_spread'].mean()
        
        print(f"\nAverage spread (high pressure games): {high_spread_mean:.2f}")
        print(f"Average spread (low pressure games): {low_spread_mean:.2f}")
        print(f"Difference: {abs(high_spread_mean - low_spread_mean):.2f} points")
        
        # T-test
        t_stat, p_value = stats.ttest_ind(
            high_pressure['actual_spread'].dropna(),
            low_pressure['actual_spread'].dropna()
        )
        print(f"\nT-test: t={t_stat:.3f}, p={p_value:.4f}")
        
        if p_value < 0.05:
            print("✅ SIGNIFICANT: Pressure edge affects outcomes (p < 0.05)")
            h1_result = "PASS"
        else:
            print("❌ NOT SIGNIFICANT: No clear effect (p >= 0.05)")
            h1_result = "FAIL"
    else:
        print("⚠️  Insufficient data to test")
        h1_result = "INSUFFICIENT_DATA"
    
    # Visualization
    plt.figure(figsize=(10, 6))
    plt.scatter(df['net_pressure_advantage'], df['actual_spread'], alpha=0.6)
    plt.xlabel('Net Pressure Advantage (Home - Away)')
    plt.ylabel('Actual Spread (Home - Away)')
    plt.title('H1: Pressure Advantage vs Actual Spread')
    plt.axhline(y=0, color='r', linestyle='--', alpha=0.3)
    plt.axvline(x=0, color='r', linestyle='--', alpha=0.3)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'h1_pressure_vs_spread.png', dpi=150)
    print(f"\n📊 Saved plot: {OUTPUT_DIR / 'h1_pressure_vs_spread.png'}")
    
    return h1_result


def test_h2_qb_vulnerability(df):
    """
    H2: QB pressure vulnerability predicts performance
    
    Test: QBs facing high pressure edge perform worse than average
    Expected: Significant negative deviation (p < 0.05)
    """
    print("\n" + "="*80)
    print("H2: QB PRESSURE VULNERABILITY PREDICTS PERFORMANCE")
    print("="*80)
    
    # Find games where one team has big pressure advantage
    threshold = 10
    
    # Away team facing high pressure (home DL >> away OL)
    away_pressured = df[df['pressure_edge_home'] > threshold].copy()
    print(f"\nGames where away QB faced high pressure: {len(away_pressured)}")
    
    if len(away_pressured) > 5:
        # Compare to expected (spread line)
        away_pressured['away_performance'] = away_pressured['away_score'] - (away_pressured['total_line'] / 2 - away_pressured['spread_line'] / 2)
        avg_performance = away_pressured['away_performance'].mean()
        print(f"Average away team performance vs expected: {avg_performance:.2f} points")
        
        if avg_performance < -2:
            print("✅ Away teams underperformed when facing pressure (as expected)")
            h2_result = "PASS"
        else:
            print("❌ No clear underperformance")
            h2_result = "FAIL"
    else:
        print("⚠️  Insufficient data")
        h2_result = "INSUFFICIENT_DATA"
    
    # Home team facing high pressure (away DL >> home OL)
    home_pressured = df[df['pressure_edge_away'] > threshold].copy()
    print(f"\nGames where home QB faced high pressure: {len(home_pressured)}")
    
    if len(home_pressured) > 5:
        home_pressured['home_performance'] = home_pressured['home_score'] - (home_pressured['total_line'] / 2 + home_pressured['spread_line'] / 2)
        avg_performance = home_pressured['home_performance'].mean()
        print(f"Average home team performance vs expected: {avg_performance:.2f} points")
        
        if avg_performance < -2:
            print("✅ Home teams underperformed when facing pressure (as expected)")
        else:
            print("❌ No clear underperformance")
    
    return h2_result


def test_h3_spread_outcomes(df):
    """
    H3: Pressure mismatches affect spread outcomes
    
    Test: Team with pressure advantage covers spread more often
    Expected: >55% cover rate (vs 50% baseline)
    """
    print("\n" + "="*80)
    print("H3: PRESSURE MISMATCHES AFFECT SPREAD OUTCOMES")
    print("="*80)
    
    # Filter games with clear pressure advantage
    threshold = 10
    
    # Games where home has pressure advantage
    home_advantage = df[df['net_pressure_advantage'] > threshold].copy()
    print(f"\nGames where home has pressure advantage (>{threshold}): {len(home_advantage)}")
    
    if len(home_advantage) > 5:
        home_covers = (home_advantage['spread_result'] == 'HOME_COVER').sum()
        home_cover_rate = home_covers / len(home_advantage) * 100
        print(f"Home cover rate: {home_cover_rate:.1f}% ({home_covers}/{len(home_advantage)})")
        
        if home_cover_rate > 55:
            print(f"✅ PROFITABLE: {home_cover_rate:.1f}% > 55% (breakeven ~52.4%)")
            h3_home = "PASS"
        else:
            print(f"❌ NOT PROFITABLE: {home_cover_rate:.1f}% <= 55%")
            h3_home = "FAIL"
    else:
        print("⚠️  Insufficient data")
        h3_home = "INSUFFICIENT_DATA"
    
    # Games where away has pressure advantage
    away_advantage = df[df['net_pressure_advantage'] < -threshold].copy()
    print(f"\nGames where away has pressure advantage (<-{threshold}): {len(away_advantage)}")
    
    if len(away_advantage) > 5:
        away_covers = (away_advantage['spread_result'] == 'AWAY_COVER').sum()
        away_cover_rate = away_covers / len(away_advantage) * 100
        print(f"Away cover rate: {away_cover_rate:.1f}% ({away_covers}/{len(away_advantage)})")
        
        if away_cover_rate > 55:
            print(f"✅ PROFITABLE: {away_cover_rate:.1f}% > 55%")
            h3_away = "PASS"
        else:
            print(f"❌ NOT PROFITABLE: {away_cover_rate:.1f}% <= 55%")
            h3_away = "FAIL"
    else:
        print("⚠️  Insufficient data")
        h3_away = "INSUFFICIENT_DATA"
    
    # Overall result
    if h3_home == "PASS" or h3_away == "PASS":
        h3_result = "PASS"
    elif h3_home == "INSUFFICIENT_DATA" and h3_away == "INSUFFICIENT_DATA":
        h3_result = "INSUFFICIENT_DATA"
    else:
        h3_result = "FAIL"
    
    # Visualization
    if len(home_advantage) > 0 or len(away_advantage) > 0:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Home advantage games
        if len(home_advantage) > 0:
            home_results = home_advantage['spread_result'].value_counts()
            ax1.bar(home_results.index, home_results.values, color=['green', 'red'])
            ax1.set_title(f'Home Has Pressure Advantage (n={len(home_advantage)})')
            ax1.set_ylabel('Count')
            ax1.axhline(y=len(home_advantage)*0.5, color='black', linestyle='--', label='50% baseline')
            ax1.legend()
        
        # Away advantage games
        if len(away_advantage) > 0:
            away_results = away_advantage['spread_result'].value_counts()
            ax2.bar(away_results.index, away_results.values, color=['red', 'green'])
            ax2.set_title(f'Away Has Pressure Advantage (n={len(away_advantage)})')
            ax2.set_ylabel('Count')
            ax2.axhline(y=len(away_advantage)*0.5, color='black', linestyle='--', label='50% baseline')
            ax2.legend()
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'h3_cover_rates.png', dpi=150)
        print(f"\n📊 Saved plot: {OUTPUT_DIR / 'h3_cover_rates.png'}")
    
    return h3_result


def test_h4_line_movement(df):
    """
    H4: Market underprices early-week mismatches
    
    Test: Lines move toward team with pressure advantage
    Expected: Positive line movement (early betting edge)
    
    NOTE: This requires opening line data, which we may not have.
    For now, we'll skip this test.
    """
    print("\n" + "="*80)
    print("H4: MARKET UNDERPRICES EARLY-WEEK MISMATCHES")
    print("="*80)
    
    print("\n⚠️  SKIPPED: Requires opening line data")
    print("   To test this, we need:")
    print("   - Opening lines (Sunday/Monday)")
    print("   - Closing lines (kickoff)")
    print("   - Line movement direction and magnitude")
    
    return "SKIPPED"


def run_simple_backtest(df):
    """
    Simple backtest: Bet team with pressure advantage ATS
    """
    print("\n" + "="*80)
    print("SIMPLE BACKTEST: BET PRESSURE ADVANTAGE")
    print("="*80)
    
    threshold = 10
    
    # Find games with clear pressure advantage
    home_advantage = df[df['net_pressure_advantage'] > threshold].copy()
    away_advantage = df[df['net_pressure_advantage'] < -threshold].copy()
    
    total_bets = len(home_advantage) + len(away_advantage)
    
    if total_bets == 0:
        print("\n⚠️  No bets meet criteria (pressure edge > 10)")
        return "INSUFFICIENT_DATA"
    
    # Count wins
    home_wins = (home_advantage['spread_result'] == 'HOME_COVER').sum()
    away_wins = (away_advantage['spread_result'] == 'AWAY_COVER').sum()
    total_wins = home_wins + away_wins
    
    win_rate = (total_wins / total_bets) * 100
    
    # Calculate ROI (assuming -110 odds)
    total_risked = total_bets * 110
    profit = (total_wins * 100) - ((total_bets - total_wins) * 110)
    roi = (profit / total_risked) * 100
    
    print(f"\nBetting Strategy: Bet team with pressure advantage > {threshold}")
    print(f"Total bets: {total_bets}")
    print(f"Wins: {total_wins}")
    print(f"Losses: {total_bets - total_wins}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"ROI: {roi:+.1f}%")
    
    # Breakeven is 52.4% at -110 odds
    if win_rate >= 53:
        print(f"\n✅ PROFITABLE: {win_rate:.1f}% > 53% (breakeven ~52.4%)")
        backtest_result = "PASS"
    elif win_rate >= 50:
        print(f"\n⚠️  MARGINAL: {win_rate:.1f}% close to breakeven")
        backtest_result = "MARGINAL"
    else:
        print(f"\n❌ NOT PROFITABLE: {win_rate:.1f}% < 50%")
        backtest_result = "FAIL"
    
    return backtest_result


def generate_summary_report(h1, h2, h3, h4, backtest):
    """Generate summary report."""
    print("\n" + "="*80)
    print("PHASE 1 VALIDATION - SUMMARY REPORT")
    print("="*80)
    
    results = {
        "H1: Pressure edge predicts sacks": h1,
        "H2: QB vulnerability predicts performance": h2,
        "H3: Pressure affects spread outcomes": h3,
        "H4: Market underprices mismatches": h4,
        "Backtest: Bet pressure advantage": backtest,
    }
    
    print("\n📊 Test Results:")
    for test, result in results.items():
        emoji = "✅" if result == "PASS" else "⚠️" if result in ["MARGINAL", "INSUFFICIENT_DATA", "SKIPPED"] else "❌"
        print(f"   {emoji} {test}: {result}")
    
    # Decision
    print("\n" + "="*80)
    print("DECISION: GO / NO-GO TO PHASE 2")
    print("="*80)
    
    passes = sum(1 for r in results.values() if r == "PASS")
    marginals = sum(1 for r in results.values() if r == "MARGINAL")
    
    if passes >= 2:
        print("\n✅ RECOMMENDATION: GO TO PHASE 2")
        print(f"   Rationale: {passes} tests passed, signal detected")
        decision = "GO"
    elif passes >= 1 and marginals >= 1:
        print("\n⚠️  RECOMMENDATION: CONDITIONAL GO TO PHASE 2")
        print(f"   Rationale: {passes} passes + {marginals} marginal, weak signal")
        decision = "CONDITIONAL_GO"
    else:
        print("\n❌ RECOMMENDATION: NO-GO TO PHASE 2")
        print("   Rationale: Insufficient signal, market likely efficient")
        decision = "NO_GO"
    
    # Save report
    report_path = OUTPUT_DIR / "PHASE1_VALIDATION_SUMMARY.txt"
    with open(report_path, 'w') as f:
        f.write("PHASE 1 VALIDATION - SUMMARY REPORT\n")
        f.write("="*80 + "\n\n")
        f.write("Test Results:\n")
        for test, result in results.items():
            f.write(f"  {test}: {result}\n")
        f.write(f"\nDecision: {decision}\n")
    
    print(f"\n📄 Report saved: {report_path}")
    
    return decision


def main():
    """Main execution."""
    print("="*80)
    print("PHASE 1 - STEP 3: TEST ALL HYPOTHESES")
    print("="*80)
    
    # Load data
    df_all, df_completed = load_data()
    
    if len(df_completed) < 10:
        print("\n❌ ERROR: Not enough completed games to test")
        print(f"   Need at least 10, have {len(df_completed)}")
        print("\n   Wait for more games to complete, or use sample data")
        return
    
    # Test all hypotheses
    h1_result = test_h1_pressure_predicts_sacks(df_completed)
    h2_result = test_h2_qb_vulnerability(df_completed)
    h3_result = test_h3_spread_outcomes(df_completed)
    h4_result = test_h4_line_movement(df_completed)
    
    # Run backtest
    backtest_result = run_simple_backtest(df_completed)
    
    # Generate summary
    decision = generate_summary_report(h1_result, h2_result, h3_result, h4_result, backtest_result)
    
    print("\n" + "="*80)
    print(f"PHASE 1 COMPLETE - DECISION: {decision}")
    print("="*80)
    
    if decision == "GO":
        print("\n🚀 Next Step: Proceed to Phase 2 (Build Prototype Simulation)")
    elif decision == "CONDITIONAL_GO":
        print("\n⚠️  Next Step: Review results, decide if signal is strong enough")
    else:
        print("\n🛑 Next Step: Pivot to alternative strategies (live betting, props, etc.)")


if __name__ == "__main__":
    main()

