"""
PlaySimulator: Simulates individual plays using nflfastR distributions.

Per strategy doc:
1. Decide play type (pass/run) based on situation
2. For pass plays:
   - Determine if pressure occurs (base rate + PFF adjustment)
   - Use QB's clean vs pressure splits for outcome
   - Model sacks, completions, INTs, scrambles
3. For run plays:
   - Use team EPA and success rates
   - Model yards gained distribution
4. Update game state after each play
"""

import numpy as np
from typing import Dict

try:
    from .game_state import GameState
    from .team_profile import TeamProfile
except ImportError:
    from game_state import GameState
    from team_profile import TeamProfile


class PlaySimulator:
    """Simulates individual plays based on team profiles and game state."""
    
    # Base pressure rate (league average)
    BASE_PRESSURE_RATE = 0.212  # 21.2% from nflfastR data
    
    def __init__(self, offense: TeamProfile, defense: TeamProfile):
        """
        Initialize play simulator.
        
        Args:
            offense: Offensive team profile
            defense: Defensive team profile
        """
        self.offense = offense
        self.defense = defense
    
    def decide_play_type(self, game_state: GameState) -> str:
        """
        Decide pass or run based on situation and team tendencies.
        
        Args:
            game_state: Current game state
        
        Returns:
            'pass' or 'run'
        """
        # Get team's pass rate for this situation
        pass_rate = self.offense.get_pass_rate(
            down=game_state.down,
            distance_bucket=game_state.distance_bucket,
            score_diff_bucket=game_state.score_diff_bucket,
            time_bucket=game_state.time_bucket
        )
        
        # Random decision based on pass rate
        return 'pass' if np.random.random() < pass_rate else 'run'
    
    def simulate_pass_play(self, game_state: GameState) -> Dict:
        """
        Simulate a pass play.
        
        Per strategy doc:
        1. Determine if pressure occurs
        2. Use QB's clean vs pressure splits
        3. Sample outcome: completion, incomplete, sack, INT, scramble
        
        Args:
            game_state: Current game state
        
        Returns:
            Dict with keys: type, yards, td, turnover
        """
        # Step 1: Determine if pressure occurs
        pressure_rate = self.BASE_PRESSURE_RATE
        
        # Step 2: Apply PFF OL vs DL mismatch for pressure adjustment
        # Strategy: OL/DL mismatch is a key predictive factor
        # NO FALLBACKS - all PFF data must be loaded
        if not hasattr(self.offense, 'ol_grade') or self.offense.ol_grade is None:
            raise ValueError(f"Offense {self.offense.team} missing ol_grade - PFF data required")
        if not hasattr(self.defense, 'dl_grade') or self.defense.dl_grade is None:
            raise ValueError(f"Defense {self.defense.team} missing dl_grade - PFF data required")
        
        # Apply zero-mean PFF adjustments if available (preferred method)
        if hasattr(self.offense, 'pff_pressure_z') and self.offense.pff_pressure_z is not None:
            # Use pre-computed zero-mean z-score
            # Beta = 0.015 means 1 SD mismatch → ±1.5% pressure change
            beta = 0.015
            adjustment_factor = 1.0 + beta * self.offense.pff_pressure_z
            adjustment_factor = np.clip(adjustment_factor, 0.80, 1.20)
            pressure_rate = np.clip(pressure_rate * adjustment_factor, 0.05, 0.55)
        else:
            # Use raw PFF grades directly for OL vs DL mismatch
            # Each 10-point DL advantage = +2% pressure rate
            # Each 10-point OL advantage = -2% pressure rate
            ol_grade = self.offense.ol_grade
            dl_grade = self.defense.dl_grade
            mismatch = dl_grade - ol_grade  # Positive = defense advantage = more pressure
            pressure_adjustment = mismatch * 0.002  # 10 points = 2% change
            pressure_adjustment = np.clip(pressure_adjustment, -0.10, 0.10)  # Cap at ±10%
            pressure_rate = np.clip(pressure_rate + pressure_adjustment, 0.05, 0.55)
        
        is_pressure = np.random.random() < pressure_rate
        
        # Calculate ANY/A advantage once for use throughout pass play
        # USE ANY/A METRIC: Adjust QB efficiency based on team ANY/A vs defense allowed
        league_avg_anya = 6.0
        anya_advantage = self.offense.off_anya - self.defense.def_anya_allowed
        
        # Step 2: Get QB's performance splits
        if is_pressure:
            qb_stats = self.offense.qb_stats['pressure'].copy()
        else:
            qb_stats = self.offense.qb_stats['clean'].copy()
        
        # USE ANY/A METRIC: Adjust QB efficiency based on ANY/A advantage
        # Strategy: ANY/A rolls up yards, TDs, INTs, sacks - comprehensive efficiency metric
        # Adjust completion rate: each 1 ANY/A advantage = +2% completion
        anya_completion_boost = 1.0 + (anya_advantage * 0.02)
        qb_stats['completion_pct'] = qb_stats['completion_pct'] * anya_completion_boost
        
        # CALIBRATION TUNING: Completion boost (+40%, cap at 0.88) - applied after ANY/A
        completion_boost = 1.40
        qb_stats['completion_pct'] = min(0.88, qb_stats['completion_pct'] * completion_boost)
        
        # Adjust yards per attempt: each 1 ANY/A advantage = +0.5 yards
        qb_stats['yards_per_att'] = qb_stats['yards_per_att'] + (anya_advantage * 0.5)
        qb_stats['yards_per_att'] = np.clip(qb_stats['yards_per_att'], 2.0, 12.0)
        
        # CALIBRATION TUNING: Drive persistence bias
        # If last play gained >4 yards, boost completion by 15%
        if hasattr(game_state, 'last_play_yards') and game_state.last_play_yards > 4:
            qb_stats['completion_pct'] = min(0.85, qb_stats['completion_pct'] * 1.15)
        
        # Step 3: Sample outcome type
        # CALIBRATION: Explicit turnover subsystem with bounded rates
        
        # PRESSURE OUTLETS: Allocate realistic escape routes before pass attempt
        if is_pressure:
            pressure_outlet = np.random.random()
            
            # Scramble: 18%
            if pressure_outlet < 0.18:
                yards = int(np.random.normal(5, 4))
                yards = np.clip(yards, -2, 15)
                is_td = self._check_touchdown(yards, game_state)
                return {
                    'type': 'scramble',
                    'yards': yards,
                    'td': is_td,
                    'turnover': False
                }
            
            # Throwaway: 10%
            elif pressure_outlet < 0.28:  # 0.18 + 0.10
                return {
                    'type': 'incomplete',
                    'yards': 0,
                    'td': False,
                    'turnover': False
                }
            
            # Sack: 28%
            elif pressure_outlet < 0.56:  # 0.28 + 0.28
                yards = np.random.randint(-10, -1)
                # CALIBRATION: Fumble on sack - halved rate
                p_fumble_sack = 0.50 * 0.006
                # USE TURNOVER REGRESSION FACTOR: Apply regression to fumble rate
                p_fumble_sack = p_fumble_sack * self.offense.turnover_regression_factor
                fumble = np.random.random() < p_fumble_sack
                if fumble:
                    fumble = np.random.random() < 0.50  # 50% recovery rate
                return {
                    'type': 'sack',
                    'yards': yards,
                    'td': False,
                    'turnover': fumble,
                    'fumble': fumble
                }
            
            # Else: Attempted pass under pressure (44%)
        
        # INTERCEPTION PROBABILITY: Explicit, bounded rates
        # Base rates depend on pressure
        if is_pressure:
            p_int_base = 0.035  # Under pressure
        else:
            p_int_base = 0.015  # Clean pocket
        
        # Add throw-depth term (estimate 15 yards for deep passes)
        air_yards = 15 if np.random.random() < 0.20 else 8  # 20% deep shots
        p_int = p_int_base + 0.002 * max(0, air_yards - 12)
        
        # Desperation cap: Late and behind
        if game_state.game_seconds_remaining < 120 and game_state.score_differential < -8:
            p_int = min(p_int, 0.06)
        
        # CALIBRATION: 40% reduction globally
        p_int = 0.60 * p_int
        
        # USE ANY/A METRIC: Adjust INT rate based on ANY/A efficiency
        # Teams with higher ANY/A have lower INT rates (part of the formula)
        # Each 1 ANY/A advantage = -10% INT rate
        anya_int_reduction = 1.0 - (anya_advantage * 0.10)
        p_int = p_int * np.clip(anya_int_reduction, 0.5, 1.2)  # Cap reduction between 50-120%
        
        # USE TURNOVER REGRESSION FACTOR: Adjust turnover rates for regression
        # Strategy: Teams with unsustainable turnover luck should regress
        # Factor < 1.0 = fade (reduce efficiency), Factor > 1.0 = boost (regression opportunity)
        p_int = p_int * self.offense.turnover_regression_factor
        
        # Check for interception FIRST
        if np.random.random() < p_int:
            return {
                'type': 'interception',
                'yards': 0,
                'td': False,
                'turnover': True
            }
        
        # Step 4: Adjust completion probability for WR vs Coverage matchup
        # Strategy: Coverage grades vs Passing grades affect completion rate
        # NO FALLBACKS - all PFF data required
        if not hasattr(self.offense, 'passing_grade') or self.offense.passing_grade is None:
            raise ValueError(f"Offense {self.offense.team} missing passing_grade - PFF data required")
        if not hasattr(self.defense, 'coverage_grade') or self.defense.coverage_grade is None:
            raise ValueError(f"Defense {self.defense.team} missing coverage_grade - PFF data required")
        
        completion_pct = qb_stats['completion_pct']
        
        # Apply PFF coverage vs passing offense matchup
        # Each 10-point passing advantage = +2% completion rate
        # Each 10-point coverage advantage = -2% completion rate
        passing_advantage = self.offense.passing_grade - self.defense.coverage_grade
        completion_adjustment = passing_advantage * 0.002  # 10 points = 2% change
        completion_adjustment = np.clip(completion_adjustment, -0.08, 0.08)  # Cap at ±8%
        completion_pct = np.clip(completion_pct + completion_adjustment, 0.30, 0.90)
        
        # SITUATIONAL FACTOR: Weather impact on passing efficiency
        # Strategy: Wind and precipitation reduce completion rates and explosive plays
        if hasattr(self.offense, 'is_dome') and not self.offense.is_dome:
            # Outdoor game - check for weather impact
            # Assume moderate wind impact if outdoor (can enhance with actual wind data later)
            weather_penalty = 0.02  # -2% completion in outdoor conditions (base)
            completion_pct = np.clip(completion_pct - weather_penalty, 0.30, 0.90)
        
        # SITUATIONAL FACTOR: Rest days impact on team efficiency
        # Strategy: Short week (<7 days) = fatigue, Bye week (>7 days) = rest advantage
        if hasattr(self.offense, 'home_rest_days'):
            rest_days = self.offense.home_rest_days  # For home team
            if rest_days < 7:
                # Short week penalty: -1% per day under 7
                rest_penalty = (7 - rest_days) * 0.01
                completion_pct = np.clip(completion_pct - rest_penalty, 0.30, 0.90)
            elif rest_days > 7:
                # Bye week or extra rest bonus: +0.5% per day over 7
                rest_bonus = min((rest_days - 7) * 0.005, 0.02)  # Cap at +2%
                completion_pct = np.clip(completion_pct + rest_bonus, 0.30, 0.90)
        
        # Completion or incomplete
        if np.random.random() < completion_pct:
            # Completion
            
            # Step 5: Adjust explosive play rate based on passing grade vs coverage
            # Strategy: Explosive plays depend on receiver/coverage matchup
            # PFF grades already validated above
            explosive_rate = 0.15  # Base 15% on clean pocket
            if not is_pressure:
                # Higher passing grade vs lower coverage = more explosive plays
                explosive_advantage = (self.offense.passing_grade - self.defense.coverage_grade) / 50.0
                explosive_rate = np.clip(0.15 + explosive_advantage * 0.05, 0.05, 0.30)
            
            # SITUATIONAL FACTOR: Weather reduces explosive play rate
            if hasattr(self.offense, 'is_dome') and not self.offense.is_dome:
                # Outdoor conditions reduce big plays
                explosive_rate = explosive_rate * 0.85  # -15% explosive rate outdoors
            
            if not is_pressure and np.random.random() < explosive_rate:
                # Log-normal distribution for explosive plays
                yards = int(np.random.lognormal(3.2, 0.9))  # Mean ~25, tail to 60+
                yards = np.clip(yards, 15, 80)
            else:
                # Normal completion
                # USE YPA METRIC: Adjust yards based on team YPA vs defense allowed YPA
                # Strategy: YPA is highly predictive (97% win rate for teams winning YPA)
                base_ypa = qb_stats['yards_per_att'] / qb_stats['completion_pct'] if qb_stats['completion_pct'] > 0 else 7.0
                
                # Apply team YPA adjustment
                # Offensive YPA advantage = more yards per completion
                ypa_advantage = self.offense.off_yards_per_pass_attempt - self.defense.def_yards_per_pass_allowed
                avg_yards = base_ypa + (ypa_advantage * 1.2)  # Each 1 YPA advantage = 1.2 yards per completion
                
                # SITUATIONAL FACTOR: Weather reduces yards per completion
                if hasattr(self.offense, 'is_dome') and not self.offense.is_dome:
                    avg_yards = avg_yards * 0.93  # -7% yards in outdoor conditions
                
                avg_yards = max(3.0, avg_yards)  # At least 3 yards on completion
                
                # Add variance
                yards = int(np.random.gamma(2, avg_yards / 2))  # Gamma distribution for right-skewed yards
                yards = np.clip(yards, 0, 80)
            
            # Adjust for field position (can't gain more than distance to end zone)
            yards = min(yards, 100 - game_state.yardline)
            
            # Check for TD
            is_td = self._check_touchdown(yards, game_state)
            
            # USE RED ZONE METRIC: Adjust TD probability inside 20 based on team red zone TD%
            # Strategy: Focus on red zone opportunities and regress conversion rates
            if not is_td and game_state.yardline >= 80:  # Inside opponent 20
                distance_to_goal = 100 - game_state.yardline
                if yards >= distance_to_goal:
                    # Base TD probability (28%)
                    base_td_rate = 0.28
                    
                    # Apply team red zone TD% vs league average (60%)
                    # Team with 70% RZ TD% gets +10% boost, 50% gets -10% penalty
                    rz_adjustment = (self.offense.red_zone_td_pct - 0.60)  # League avg ~60%
                    td_rate = base_td_rate + rz_adjustment * 0.15  # Scale adjustment
                    td_rate = np.clip(td_rate, 0.10, 0.50)  # Cap between 10-50%
                    
                    # Scale by distance to goal
                    distance_multiplier = (20 - distance_to_goal) / 20  # 1.0 at goal, 0 at 20
                    final_td_rate = td_rate * (1.0 + 2.0 * distance_multiplier)  # Boost near goal
                    
                    if np.random.random() < min(0.88, final_td_rate):
                        is_td = True
                        yards = distance_to_goal
            
            # CALIBRATION: Fumble after catch - halved rate
            p_fumble_completion = 0.50 * 0.002
            # USE TURNOVER REGRESSION FACTOR: Apply regression to fumble rate
            p_fumble_completion = p_fumble_completion * self.offense.turnover_regression_factor
            fumble = np.random.random() < p_fumble_completion
            if fumble:
                fumble = np.random.random() < 0.50  # 50% recovery rate
            
            return {
                'type': 'completion',
                'yards': yards,
                'td': is_td,
                'turnover': fumble,
                'fumble': fumble
            }
        else:
            # Incomplete
            return {
                'type': 'incomplete',
                'yards': 0,
                'td': False,
                'turnover': False
            }
    
    def simulate_run_play(self, game_state: GameState) -> Dict:
        """
        Simulate a run play.
        
        Per strategy doc:
        - Use team EPA and success rates
        - Adjust for OL/DL matchup (Phase 2)
        
        Args:
            game_state: Current game state
        
        Returns:
            Dict with keys: type, yards, td, turnover
        """
        # Base yards: league average ~4.8 yards per carry
        base_yards = 4.8
        
        # USE MULTIPLE METRICS FOR RUN YARDS:
        # 1. EPA differential (team strength)
        epa_diff = self.offense.off_epa - self.defense.def_epa
        yards_adjustment = epa_diff * 12  # Each 0.1 EPA = 1.2 yards
        
        # 2. PFF OL/DL run blocking matchup
        if not hasattr(self.offense, 'ol_run_grade') or self.offense.ol_run_grade is None:
            raise ValueError(f"Offense {self.offense.team} missing ol_run_grade - PFF data required")
        if not hasattr(self.defense, 'dl_run_grade') or self.defense.dl_run_grade is None:
            raise ValueError(f"Defense {self.defense.team} missing dl_run_grade - PFF data required")
        
        grade_adjustment = (self.offense.ol_run_grade - self.defense.dl_run_grade) * 0.05
        yards_adjustment += grade_adjustment
        
        # 3. USE YPP METRIC: Team yards per play vs defense allowed
        # Strategy: YPP is highly predictive - teams winning YPP win 97% of games
        ypp_advantage = self.offense.off_yards_per_play - self.defense.def_yards_per_play_allowed
        yards_adjustment += ypp_advantage * 0.8  # Each 1 YPP advantage = 0.8 yards per run
        
        # Sample yards from distribution
        avg_yards = base_yards + yards_adjustment
        yards = int(np.random.normal(avg_yards, 3.5))
        
        # Clip to reasonable range
        yards = np.clip(yards, -5, 80)
        
        # Adjust for field position
        yards = min(yards, 100 - game_state.yardline)
        
        # Check for TD
        is_td = self._check_touchdown(yards, game_state)
        
        # CALIBRATION: Fumble on run - halved rate
        p_fumble_run = 0.50 * 0.010
        # USE TURNOVER REGRESSION FACTOR: Apply regression to fumble rate
        p_fumble_run = p_fumble_run * self.offense.turnover_regression_factor
        fumble = np.random.random() < p_fumble_run
        if fumble:
            fumble = np.random.random() < 0.50  # 50% recovery rate
        
        return {
            'type': 'run',
            'yards': yards,
            'td': is_td,
            'turnover': fumble,
            'fumble': fumble
        }
    
    def _check_touchdown(self, yards: int, game_state: GameState) -> bool:
        """Check if play results in touchdown."""
        return (game_state.yardline + yards) >= 100
    
    def simulate_field_goal(self, game_state: GameState) -> Dict:
        """
        Simulate field goal attempt.
        
        Uses team's FG make % from special teams data.
        
        Args:
            game_state: Current game state
        
        Returns:
            Dict with keys: type, made, points
        """
        # Distance: yardline + 17 (end zone + hold spot)
        distance = (100 - game_state.yardline) + 17
        
        # Base success probability based on distance
        # NFL average: ~85% from 30 yards, drops to ~50% at 50 yards
        if distance < 30:
            base_make_prob = 0.90
        elif distance < 40:
            base_make_prob = 0.85
        elif distance < 50:
            base_make_prob = 0.70
        else:
            base_make_prob = 0.50
        
        # USE SPECIAL TEAMS FG MAKE %: Adjust based on team's actual FG %
        # Strategy: Special teams is overlooked but field position matters
        league_avg_fg = 0.85  # League average ~85%
        fg_adjustment = self.offense.field_goal_make_pct - league_avg_fg
        make_prob = base_make_prob + fg_adjustment * 0.3  # Scale adjustment by 30%
        make_prob = np.clip(make_prob, 0.05, 0.98)  # Cap between 5-98%
        
        made = np.random.random() < make_prob
        
        return {
            'type': 'field_goal',
            'made': made,
            'points': 3 if made else 0
        }
    
    def simulate_punt(self, game_state: GameState) -> Dict:
        """
        Simulate punt.
        
        Uses team's punt net yards from special teams data.
        
        Args:
            game_state: Current game state
        
        Returns:
            Dict with keys: type, net_yards
        """
        # USE SPECIAL TEAMS PUNT NET YARDS: Use team's actual punt net average
        # Strategy: Special teams field position can decide games
        team_net = self.offense.punt_net_yards
        
        # Calculate net yards based on field position
        if game_state.yardline + 45 >= 100:  # Would result in touchback
            # Touchback: net = distance to goal - 20
            net_yards = (100 - game_state.yardline) - 20
        else:
            # Use team's net average (includes return yards)
            net_yards = int(np.random.normal(team_net, 5))
            net_yards = np.clip(net_yards, 15, 60)
        
        return {
            'type': 'punt',
            'net_yards': net_yards
        }

