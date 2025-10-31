"""
Analyze strategy document to identify missing signals.

Compare what's in the strategy doc vs what we're currently using.
"""
import re
from pathlib import Path

def read_strategy_doc():
    """Read the strategy.rtf file."""
    strategy_path = Path.home() / "Dropbox" / "Mac" / "Downloads" / "strategy.rtf"
    
    if not strategy_path.exists():
        print(f"⚠️  Strategy doc not found at {strategy_path}")
        return None
    
    with open(strategy_path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    return content

def extract_signals_from_strategy(content):
    """Extract key signals mentioned in the strategy document."""
    signals = {}
    
    # Key signal patterns
    signal_patterns = {
        'yards_per_play': r'yards?\s+per\s+(?:play|attempt)',
        'early_down_success': r'early[-\s]?down\s+success',
        'anya': r'ANY/A|adjusted\s+net\s+yards',
        'pressure_rate': r'pressure\s+rate|pass\s+rush|pass\s+block',
        'explosive_plays': r'explosive\s+plays?|chunk\s+plays?|20\+|big\s+plays?',
        'pace': r'pace\s+of\s+play|tempo|plays?\s+per\s+(?:game|drive)',
        'turnover_regression': r'turnover\s+(?:margin|regression|luck)',
        'red_zone': r'red[-\s]?zone|inside\s+the\s+opponent',
        'special_teams': r'special\s+teams?|field\s+goal|punt|kick\s+return',
        'coaching': r'coaching|fourth[-\s]?down|play[-\s]?calling',
        'wr_vs_cb': r'receiver|WR|coverage|CB|secondary',
        'ol_dl_mismatch': r'offensive\s+line|defensive\s+line|O[-\s]?line|D[-\s]?line|trenches',
    }
    
    for signal_name, pattern in signal_patterns.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            signals[signal_name] = len(matches)
    
    return signals

def check_current_implementation():
    """Check what signals we're currently using."""
    play_sim_path = Path(__file__).parent.parent / "simulator" / "play_simulator.py"
    game_sim_path = Path(__file__).parent.parent / "simulator" / "game_simulator.py"
    team_profile_path = Path(__file__).parent.parent / "simulator" / "team_profile.py"
    
    play_sim_code = play_sim_path.read_text()
    game_sim_code = game_sim_path.read_text()
    team_profile_code = team_profile_path.read_text()
    
    implemented = {}
    
    checks = {
        'yards_per_play': ['ypp', 'yards_per_play', 'off_yards_per_play'],
        'yards_per_pass_attempt': ['ypa', 'yards_per_pass', 'off_yards_per_pass'],
        'early_down_success': ['early_down_success', 'success_rate'],
        'anya': ['anya', 'adjusted_net_yards'],
        'pressure_rate': ['pressure', 'ol_grade', 'dl_grade', 'pass_rush'],
        'explosive_plays': ['explosive', 'big_play', 'chunk'],
        'pace': ['pace', 'plays_per_drive', 'tempo'],
        'turnover_regression': ['turnover_regression', 'turnover_factor'],
        'red_zone': ['red_zone', 'rz_'],
        'special_teams': ['field_goal', 'punt', 'special_teams', 'fg_'],
        'coaching': ['get_pass_rate', 'playcalling', 'fourth_down'],
        'wr_vs_cb': ['passing_grade', 'coverage_grade', 'receiver'],
        'ol_dl_mismatch': ['ol_grade', 'dl_grade', 'ol_run_grade', 'dl_run_grade'],
    }
    
    all_code = play_sim_code + game_sim_code + team_profile_code
    
    for signal_name, keywords in checks.items():
        for keyword in keywords:
            if keyword.lower() in all_code.lower():
                implemented[signal_name] = True
                break
    
    return implemented

def analyze_missing_signals():
    """Compare strategy signals vs implementation."""
    print("="*70)
    print("STRATEGY DOCUMENT SIGNAL ANALYSIS")
    print("="*70)
    
    # Read strategy doc
    content = read_strategy_doc()
    if not content:
        return
    
    # Extract signals
    strategy_signals = extract_signals_from_strategy(content)
    
    # Check implementation
    implemented = check_current_implementation()
    
    print(f"\n📊 Signals Mentioned in Strategy Document:")
    for signal, count in sorted(strategy_signals.items(), key=lambda x: -x[1]):
        status = "✅ IMPLEMENTED" if signal in implemented else "❌ MISSING"
        print(f"   {signal:25s} ({count:3d} mentions) - {status}")
    
    print(f"\n📋 Missing Signals (High Priority):")
    missing = [s for s in strategy_signals.keys() if s not in implemented]
    
    if not missing:
        print("   ✅ All signals from strategy document are implemented!")
    else:
        for signal in missing:
            mentions = strategy_signals[signal]
            print(f"   • {signal} ({mentions} mentions)")
    
    # Additional signals from strategy doc that might be missing
    print(f"\n💡 Additional Potential Signals (From Strategy Doc):")
    
    additional_signals = []
    
    # Check for specific mentions
    if 'coaching aggression' in content.lower() or 'fourth down' in content.lower():
        additional_signals.append("4th Down Aggression - Pass rate over expected, 4th down go-rate")
    
    if 'defensive coverage vs wr skill types' in content.lower():
        additional_signals.append("WR Skill Types - Specific receiver types vs coverage schemes")
    
    if 'situational' in content.lower() or 'weather' in content.lower():
        additional_signals.append("Weather Factors - Wind, precipitation impact on passing/totals")
    
    if 'rest days' in content.lower() or 'travel' in content.lower():
        additional_signals.append("Rest Days - Short week impact, travel distance")
    
    if additional_signals:
        for sig in additional_signals:
            print(f"   • {sig}")
    else:
        print("   None identified")

if __name__ == "__main__":
    analyze_missing_signals()

