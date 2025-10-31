"""
Comprehensive Simulation Audit
Verify all NFLfastR and PFF data is loaded and used correctly.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import inspect
from simulator.team_profile import TeamProfile
from simulator.play_simulator import PlaySimulator
from simulator.game_simulator import GameSimulator
from simulator.game_state import GameState

class SimulationAuditor:
    """Audit simulation to verify all data is used."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.team = 'KC'
        self.season = 2025
        self.week = 1
        
        # Expected data sources
        self.expected_data_sources = {
            # NFLfastR data
            'epa': {'file': 'data/features/rolling_epa_2022_2025.csv', 'loaded_as': ['off_epa', 'def_epa']},
            'qb_stats': {'file': 'data/nflfastR/qb_pressure_splits_season.csv', 'loaded_as': ['qb_name', 'qb_stats']},
            'playcalling': {'file': 'data/nflfastR/playcalling_tendencies_season.csv', 'loaded_as': ['playcalling']},
            'drive_probs': {'file': 'data/nflfastR/drive_probabilities_season.csv', 'loaded_as': ['drive_probs']},
            'pace': {'file': 'data/nflfastR/team_pace.csv', 'loaded_as': ['pace']},
            'yards_per_play': {'file': 'data/nflfastR/team_yards_per_play_season.csv', 'loaded_as': ['off_yards_per_play', 'def_yards_per_play_allowed', 'off_yards_per_pass_attempt', 'def_yards_per_pass_allowed']},
            'early_down_success': {'file': 'data/nflfastR/early_down_success_season.csv', 'loaded_as': ['early_down_success_rate']},
            'anya': {'file': 'data/nflfastR/team_anya_season.csv', 'loaded_as': ['off_anya', 'def_anya_allowed']},
            'turnover_regression': {'file': 'data/nflfastR/turnover_regression_season.csv', 'loaded_as': ['turnover_regression_factor']},
            'red_zone': {'file': 'data/nflfastR/red_zone_stats_season.csv', 'loaded_as': ['red_zone_trips_per_game', 'red_zone_td_pct']},
            'special_teams': {'file': 'data/nflfastR/special_teams_season.csv', 'loaded_as': ['punt_net_yards', 'field_goal_make_pct']},
            'situational_factors': {'file': 'data/nflfastR/situational_factors.csv', 'loaded_as': ['home_rest_days', 'away_rest_days', 'is_dome', 'temperature', 'wind']},
            
            # PFF data
            'pff_grades': {'file': 'data/pff_raw/team_grades_2024.csv', 'loaded_as': ['ol_grade', 'dl_grade', 'ol_run_grade', 'dl_run_grade', 'passing_grade', 'coverage_grade']},
        }
        
        # Expected usage in PlaySimulator
        self.expected_play_usage = {
            'ol_grade': 'Pass pressure calculation',
            'dl_grade': 'Pass pressure calculation',
            'ol_run_grade': 'Run blocking adjustment',
            'dl_run_grade': 'Run blocking adjustment',
            'passing_grade': 'Pass completion rate',
            'coverage_grade': 'Pass completion rate',
            'off_yards_per_pass_attempt': 'Pass yardage',
            'def_yards_per_pass_allowed': 'Pass yardage',
            'off_yards_per_play': 'Run yardage',
            'def_yards_per_play_allowed': 'Run yardage',
            'off_anya': 'QB efficiency adjustments',
            'def_anya_allowed': 'QB efficiency adjustments',
            'red_zone_td_pct': 'TD probability inside 20',
            'turnover_regression_factor': 'Turnover rates',
            'punt_net_yards': 'Field position on punts',
            'field_goal_make_pct': 'FG success rate',
            'early_down_success_rate': 'First down probability',
        }
        
    def audit_data_files(self):
        """Check if all expected data files exist."""
        print("="*70)
        print("AUDIT 1: DATA FILES")
        print("="*70)
        
        missing = []
        found = []
        
        for source_name, info in self.expected_data_sources.items():
            file_path = Path(info['file'])
            if not file_path.exists():
                # Try relative to simulation_engine
                file_path = Path(__file__).parent.parent.parent.parent / info['file']
            
            if file_path.exists():
                found.append(source_name)
                print(f"✅ {source_name:30s} -> {file_path.name}")
            else:
                missing.append(source_name)
                print(f"❌ {source_name:30s} -> MISSING: {info['file']}")
        
        print(f"\n📊 Summary: {len(found)}/{len(self.expected_data_sources)} files found")
        if missing:
            print(f"⚠️  Missing: {', '.join(missing)}")
        
        return len(missing) == 0
    
    def audit_team_profile(self):
        """Check what data TeamProfile actually loads."""
        print("\n" + "="*70)
        print("AUDIT 2: TEAMPROFILE DATA LOADING")
        print("="*70)
        
        profile = TeamProfile(self.team, self.season, self.week, self.data_dir, debug=False)
        
        # Get all attributes
        attrs = {k: v for k, v in vars(profile).items() if not k.startswith('_')}
        
        print(f"\n📊 Loaded attributes for {self.team} {self.season} W{self.week}:")
        
        loaded_data = {}
        missing_data = []
        
        for source_name, info in self.expected_data_sources.items():
            loaded_attrs = []
            for attr_name in info['loaded_as']:
                if hasattr(profile, attr_name):
                    value = getattr(profile, attr_name)
                    loaded_attrs.append(attr_name)
                    loaded_data[attr_name] = value
                    print(f"   ✅ {attr_name:35s} = {self._format_value(value)}")
                else:
                    missing_data.append(attr_name)
                    print(f"   ❌ {attr_name:35s} = NOT FOUND")
        
        # Check for unexpected attributes
        print(f"\n📊 Other attributes loaded:")
        for attr in sorted(attrs.keys()):
            if attr not in loaded_data and attr not in ['team', 'season', 'week', 'data_dir', 'debug']:
                value = attrs[attr]
                print(f"   ℹ️  {attr:35s} = {self._format_value(value)}")
        
        print(f"\n📊 Summary: {len(loaded_data)}/{sum(len(info['loaded_as']) for info in self.expected_data_sources.values())} expected attributes loaded")
        if missing_data:
            print(f"⚠️  Missing: {', '.join(missing_data)}")
        
        return profile, len(missing_data) == 0
    
    def _format_value(self, value):
        """Format value for display."""
        if value is None:
            return "None"
        elif isinstance(value, (int, float)):
            return f"{value:.3f}"
        elif isinstance(value, pd.DataFrame):
            return f"DataFrame({len(value)} rows)"
        elif isinstance(value, dict):
            return f"dict({len(value)} keys)"
        elif isinstance(value, (list, tuple, np.ndarray)):
            return f"{type(value).__name__}({len(value)} items)"
        else:
            return str(value)[:50]
    
    def audit_play_simulator_usage(self, home_profile, away_profile):
        """Check what data PlaySimulator actually uses."""
        print("\n" + "="*70)
        print("AUDIT 3: PLAY SIMULATOR DATA USAGE")
        print("="*70)
        
        # Read PlaySimulator source
        play_sim_path = Path(__file__).parent.parent / "simulator" / "play_simulator.py"
        play_sim_code = play_sim_path.read_text()
        
        # Check for each expected attribute
        print(f"\n📊 Checking PlaySimulator code for data usage:")
        
        used_attrs = {}
        unused_attrs = {}
        
        for attr_name, description in self.expected_play_usage.items():
            # Check if attribute is referenced
            patterns = [
                f"self.offense.{attr_name}",
                f"self.defense.{attr_name}",
                f"offense.{attr_name}",
                f"defense.{attr_name}",
                f"'{attr_name}'",
                f'"{attr_name}"',
            ]
            
            found = False
            for pattern in patterns:
                if pattern in play_sim_code:
                    used_attrs[attr_name] = description
                    found = True
                    break
            
            if not found:
                unused_attrs[attr_name] = description
        
        print(f"\n✅ USED ({len(used_attrs)}):")
        for attr, desc in sorted(used_attrs.items()):
            print(f"   ✅ {attr:35s} - {desc}")
        
        if unused_attrs:
            print(f"\n❌ NOT USED ({len(unused_attrs)}):")
            for attr, desc in sorted(unused_attrs.items()):
                print(f"   ❌ {attr:35s} - {desc}")
        
        # Check for hardcoded values that should use data
        print(f"\n📊 Checking for hardcoded values:")
        hardcoded_checks = [
            ('pressure_probability', 'Should use ol_grade/dl_grade'),
            ('completion_rate', 'Should use passing_grade/coverage_grade'),
            ('run_yards', 'Should use ol_run_grade/dl_run_grade'),
            ('yards_per_play', 'Should use off_yards_per_play'),
        ]
        
        for check, note in hardcoded_checks:
            if check in play_sim_code.lower():
                print(f"   ⚠️  Found '{check}' - {note}")
        
        return len(unused_attrs) == 0
    
    def audit_game_simulator_usage(self, home_profile, away_profile):
        """Check what data GameSimulator uses."""
        print("\n" + "="*70)
        print("AUDIT 4: GAME SIMULATOR DATA USAGE")
        print("="*70)
        
        game_sim_path = Path(__file__).parent.parent / "simulator" / "game_simulator.py"
        game_sim_code = game_sim_path.read_text()
        
        expected_usage = {
            'pace': 'Max plays per drive',
            'early_down_success_rate': 'First down probability',
            'playcalling': 'Play type selection',
            'drive_probs': 'Drive outcome probabilities',
        }
        
        print(f"\n📊 Checking GameSimulator code:")
        
        used = []
        unused = []
        
        for attr, desc in expected_usage.items():
            patterns = [
                f"offense.{attr}",
                f"away.{attr}",
                f"home.{attr}",
                f"self.{attr}",
            ]
            
            found = any(pattern in game_sim_code for pattern in patterns)
            
            if found:
                used.append((attr, desc))
                print(f"   ✅ {attr:35s} - {desc}")
            else:
                unused.append((attr, desc))
                print(f"   ❌ {attr:35s} - {desc}")
        
        return len(unused) == 0
    
    def audit_pff_integration(self, home_profile, away_profile):
        """Verify PFF grades are fully integrated."""
        print("\n" + "="*70)
        print("AUDIT 5: PFF GRADES INTEGRATION")
        print("="*70)
        
        pff_attrs = ['ol_grade', 'dl_grade', 'ol_run_grade', 'dl_run_grade', 'passing_grade', 'coverage_grade']
        
        print(f"\n📊 PFF Grades for {home_profile.team}:")
        all_loaded = True
        for attr in pff_attrs:
            if hasattr(home_profile, attr):
                value = getattr(home_profile, attr)
                if value is None or (isinstance(value, float) and value == 70.0):
                    print(f"   ⚠️  {attr:30s} = {value} (default/fallback)")
                    all_loaded = False
                else:
                    print(f"   ✅ {attr:30s} = {value:.1f}")
            else:
                print(f"   ❌ {attr:30s} = NOT FOUND")
                all_loaded = False
        
        # Check PFF data file
        pff_file = self.data_dir.parent / "pff_raw" / "team_grades_2024.csv"
        if pff_file.exists():
            pff_df = pd.read_csv(pff_file)
            print(f"\n📊 PFF Data File: {len(pff_df)} teams loaded")
            if self.team in pff_df['team'].values or 'BLT' in pff_df['team'].values:
                print(f"   ✅ {self.team} found in PFF data")
            else:
                print(f"   ⚠️  {self.team} not found - check team abbreviation mapping")
        else:
            print(f"\n⚠️  PFF file not found: {pff_file}")
        
        return all_loaded
    
    def audit_calibration_approach(self):
        """Audit calibration approach - are we predicting or just centering?"""
        print("\n" + "="*70)
        print("AUDIT 6: CALIBRATION APPROACH")
        print("="*70)
        
        backtest_path = Path(__file__).parent.parent / "backtest_all_games_conviction.py"
        backtest_code = backtest_path.read_text()
        
        print(f"\n📊 Current Calibration Logic:")
        
        # Check for linear calibration
        if 'LINEAR_ALPHA' in backtest_code and 'LINEAR_BETA' in backtest_code:
            print(f"   ✅ Linear calibration found:")
            # Extract values
            import re
            alpha_match = re.search(r'LINEAR_ALPHA\s*=\s*([0-9.]+)', backtest_code)
            beta_match = re.search(r'LINEAR_BETA\s*=\s*([0-9.]+)', backtest_code)
            if alpha_match and beta_match:
                print(f"      Alpha: {alpha_match.group(1)}")
                print(f"      Beta: {beta_match.group(1)}")
                print(f"      Formula: calibrated = {alpha_match.group(1)} + {beta_match.group(1)} * raw")
        
        # Check for market centering
        if 'center_scores_to_market' in backtest_code:
            print(f"   ⚠️  Market centering still present")
            print(f"      This aligns means to market, but may reduce predictive power")
        
        # Check for raw score preservation
        if 'spread_raw' in backtest_code and 'total_raw' in backtest_code:
            print(f"   ✅ Raw scores preserved (good for calibration)")
        else:
            print(f"   ❌ Raw scores not preserved")
        
        # Check probability calculation
        if 'norm.cdf' in backtest_code:
            print(f"   ✅ Probabilities calculated from calibrated distributions")
        else:
            print(f"   ⚠️  Probabilities may be from centered distributions only")
        
        print(f"\n💡 Recommendations:")
        print(f"   1. Use raw simulator outputs for calibration")
        print(f"   2. Fit calibration on actual outcomes, not market alignment")
        print(f"   3. Preserve raw simulator variance for edge calculation")
        print(f"   4. Test calibration on out-of-sample data")
    
    def run_full_audit(self):
        """Run complete audit."""
        print("="*70)
        print("COMPREHENSIVE SIMULATION AUDIT")
        print("="*70)
        print(f"\nAuditing: {self.team} @ Home Team, {self.season} Week {self.week}")
        print(f"Data directory: {self.data_dir}")
        
        results = {}
        
        # Audit 1: Data files
        results['data_files'] = self.audit_data_files()
        
        # Audit 2: TeamProfile
        home_profile, results['team_profile'] = self.audit_team_profile()
        
        # Create away profile for usage checks
        away_profile = TeamProfile('BUF', self.season, self.week, self.data_dir, debug=False)
        
        # Audit 3: PlaySimulator usage
        results['play_simulator'] = self.audit_play_simulator_usage(home_profile, away_profile)
        
        # Audit 4: GameSimulator usage
        results['game_simulator'] = self.audit_game_simulator_usage(home_profile, away_profile)
        
        # Audit 5: PFF integration
        results['pff_integration'] = self.audit_pff_integration(home_profile, away_profile)
        
        # Audit 6: Calibration
        self.audit_calibration_approach()
        
        # Summary
        print("\n" + "="*70)
        print("AUDIT SUMMARY")
        print("="*70)
        
        for check, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} - {check}")
        
        all_passed = all(results.values())
        print(f"\n{'✅ ALL CHECKS PASSED' if all_passed else '⚠️  SOME CHECKS FAILED'}")
        
        return results

if __name__ == "__main__":
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    auditor = SimulationAuditor(data_dir)
    auditor.run_full_audit()

