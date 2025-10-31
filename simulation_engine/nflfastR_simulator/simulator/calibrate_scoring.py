"""
Step 1: Match NFL Reality

Tune the raw simulator to match league facts:
- Plays per drive: 6.0-6.8
- Drives per team: 10-12
- TD% per drive: 22-24%
- FG%: 8-10%
- Turnover%: 10-12%
- Sack rate given pressure: ~45%
- Baseline pressure rate: 30-32%
- Explosive plays (15+ yards): 10-12% of plays
- Average total: 42-46 points

Instrument the engine to log everything.
Adjust only the fewest knobs needed.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from team_profile import TeamProfile
from game_simulator import GameSimulator
from game_state import GameState
from play_simulator import PlaySimulator


class InstrumentedGameSimulator(GameSimulator):
    """GameSimulator with detailed logging for calibration."""
    
    def __init__(self, home_team, away_team):
        super().__init__(home_team, away_team)
        self.reset_logs()
    
    def reset_logs(self):
        """Reset all logging counters."""
        self.logs = {
            'drives': [],
            'plays': [],
            'scoring_events': [],
            'field_positions': [],
            'play_types': [],
            'outcomes': []
        }
    
    def simulate_game_instrumented(self):
        """Run one simulation with full logging."""
        self.reset_logs()
        
        game_state = GameState()
        game_state.possession = 'home'
        game_state.start_new_drive()
        
        while not game_state.is_game_over():
            # Log drive start
            drive_start = {
                'drive_num': game_state.drive_number,
                'team': game_state.possession,
                'start_yardline': game_state.yardline,
                'start_quarter': game_state.quarter,
                'plays': 0,
                'outcome': None
            }
            
            # Determine teams
            if game_state.possession == 'home':
                offense, defense = self.home_team, self.away_team
            else:
                offense, defense = self.away_team, self.home_team
            
            # Simulate drive
            drive_outcome = self._simulate_drive_instrumented(
                game_state, offense, defense, drive_start
            )
            
            # Log drive end
            drive_start['outcome'] = drive_outcome
            self.logs['drives'].append(drive_start)
        
        # Calculate summary stats
        return self._calculate_summary()
    
    def _simulate_drive_instrumented(self, game_state, offense, defense, drive_log):
        """Simulate drive with logging."""
        play_sim = PlaySimulator(offense, defense)
        
        max_plays = 20
        plays_run = 0
        
        while plays_run < max_plays and not game_state.is_game_over():
            plays_run += 1
            drive_log['plays'] += 1
            
            # Check for end of quarter
            if game_state.time_remaining == 0 and game_state.quarter < 4:
                game_state.advance_quarter()
                continue
            
            # Check for 4th down
            if game_state.down == 4:
                if game_state.should_attempt_fg():
                    fg_result = play_sim.simulate_field_goal(game_state)
                    self.logs['scoring_events'].append({
                        'type': 'FG',
                        'made': fg_result['made'],
                        'distance': (100 - game_state.yardline) + 17
                    })
                    if fg_result['made']:
                        game_state.add_points(3, game_state.possession)
                        return 'FG'
                    game_state.switch_possession()
                    game_state.start_new_drive()
                    return 'Missed_FG'
                
                elif game_state.should_punt():
                    punt_result = play_sim.simulate_punt(game_state)
                    game_state.switch_possession()
                    game_state.yardline = 100 - (game_state.yardline + punt_result['net_yards'])
                    game_state.yardline = np.clip(game_state.yardline, 0, 100)
                    game_state.start_new_drive()
                    return 'Punt'
            
            # Decide play type
            play_type = play_sim.decide_play_type(game_state)
            self.logs['play_types'].append(play_type)
            
            # Simulate play
            if play_type == 'pass':
                play_result = play_sim.simulate_pass_play(game_state)
            else:
                play_result = play_sim.simulate_run_play(game_state)
            
            # Log play outcome
            self.logs['plays'].append({
                'type': play_type,
                'result': play_result['type'],
                'yards': play_result.get('yards', 0),
                'td': play_result.get('td', False),
                'turnover': play_result.get('turnover', False)
            })
            
            # Log explosive plays
            if play_result.get('yards', 0) >= 15:
                self.logs['outcomes'].append('explosive')
            
            # Update game state
            game_state.update_from_play(play_result)
            
            # Check for scoring
            if play_result.get('td', False):
                self.logs['scoring_events'].append({
                    'type': 'TD',
                    'play_type': play_type
                })
                return 'TD'
            
            # Check for turnover
            if play_result.get('turnover', False):
                self.logs['scoring_events'].append({
                    'type': 'Turnover',
                    'play_type': play_type
                })
                return 'Turnover'
            
            # Check if drive ended
            if game_state.plays_this_drive == 0:
                return 'Turnover_on_Downs'
        
        return 'End_of_Half'
    
    def _calculate_summary(self):
        """Calculate summary statistics from logs."""
        total_drives = len(self.logs['drives'])
        total_plays = len(self.logs['plays'])
        
        # Drive outcomes
        outcomes = [d['outcome'] for d in self.logs['drives']]
        td_count = outcomes.count('TD')
        fg_count = outcomes.count('FG')
        turnover_count = outcomes.count('Turnover') + outcomes.count('Turnover_on_Downs')
        
        # Play types
        pass_plays = self.logs['play_types'].count('pass')
        run_plays = self.logs['play_types'].count('run')
        
        # Explosive plays
        explosive_count = self.logs['outcomes'].count('explosive')
        
        return {
            'total_drives': total_drives,
            'total_plays': total_plays,
            'plays_per_drive': total_plays / total_drives if total_drives > 0 else 0,
            'td_pct': td_count / total_drives if total_drives > 0 else 0,
            'fg_pct': fg_count / total_drives if total_drives > 0 else 0,
            'turnover_pct': turnover_count / total_drives if total_drives > 0 else 0,
            'pass_rate': pass_plays / (pass_plays + run_plays) if (pass_plays + run_plays) > 0 else 0,
            'explosive_rate': explosive_count / total_plays if total_plays > 0 else 0,
        }


def run_calibration_test(n_games=50):
    """
    Run calibration test on N games.
    
    Compare to NFL targets:
    - Plays per drive: 6.0-6.8
    - Drives per team: 10-12
    - TD%: 22-24%
    - FG%: 8-10%
    - Turnover%: 10-12%
    - Explosive%: 10-12%
    - Avg total: 42-46
    """
    print("="*80)
    print(f"CALIBRATION TEST: {n_games} GAMES")
    print("="*80)
    
    data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
    
    # Use 2024 Week 1 teams (will expand later)
    teams = ['KC', 'BUF', 'BAL', 'CIN', 'PHI', 'DAL', 'SF', 'LAR']
    
    results = []
    
    for i in range(n_games):
        # Random matchup
        home = np.random.choice(teams)
        away = np.random.choice([t for t in teams if t != home])
        
        home_team = TeamProfile(home, 2024, 1, data_dir)
        away_team = TeamProfile(away, 2024, 1, data_dir)
        
        sim = InstrumentedGameSimulator(home_team, away_team)
        result = sim.simulate_game_instrumented()
        
        results.append(result)
        
        if (i + 1) % 10 == 0:
            print(f"   Completed {i+1}/{n_games} games...")
    
    # Aggregate results
    df = pd.DataFrame(results)
    
    print("\n" + "="*80)
    print("CALIBRATION RESULTS")
    print("="*80)
    
    print(f"\n{'Metric':<30} {'Current':<15} {'Target':<15} {'Status':<10}")
    print("-"*70)
    
    metrics = [
        ('Plays per drive', df['plays_per_drive'].mean(), (6.0, 6.8)),
        ('Drives per team', df['total_drives'].mean() / 2, (10, 12)),
        ('TD% per drive', df['td_pct'].mean(), (0.22, 0.24)),
        ('FG% per drive', df['fg_pct'].mean(), (0.08, 0.10)),
        ('Turnover% per drive', df['turnover_pct'].mean(), (0.10, 0.12)),
        ('Pass rate', df['pass_rate'].mean(), (0.55, 0.65)),
        ('Explosive play rate', df['explosive_rate'].mean(), (0.10, 0.12)),
    ]
    
    for label, current, (target_min, target_max) in metrics:
        if target_min <= current <= target_max:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        if isinstance(current, float) and current < 1:
            print(f"{label:<30} {current:<15.1%} {f'{target_min:.0%}-{target_max:.0%}':<15} {status:<10}")
        else:
            print(f"{label:<30} {current:<15.1f} {f'{target_min:.1f}-{target_max:.1f}':<15} {status:<10}")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    # Calculate needed adjustments
    current_ppd = df['plays_per_drive'].mean()
    target_ppd = 6.4
    ppd_multiplier = target_ppd / current_ppd if current_ppd > 0 else 1.0
    
    current_td = df['td_pct'].mean()
    target_td = 0.23
    td_multiplier = target_td / current_td if current_td > 0 else 1.0
    
    print(f"\n1. Plays per drive: {current_ppd:.1f} → {target_ppd:.1f}")
    print(f"   → Multiply drive length by {ppd_multiplier:.2f}x")
    
    print(f"\n2. TD rate: {current_td:.1%} → {target_td:.1%}")
    print(f"   → Multiply scoring probability by {td_multiplier:.2f}x")
    
    print(f"\n3. Total points per game:")
    # Estimate: TD% * 7 + FG% * 3, times drives per team, times 2 teams
    current_total = (df['td_pct'].mean() * 7 + df['fg_pct'].mean() * 3) * (df['total_drives'].mean() / 2) * 2
    print(f"   Current: {current_total:.1f} points")
    print(f"   Target: 42-46 points")
    
    return df


if __name__ == "__main__":
    run_calibration_test(n_games=50)

