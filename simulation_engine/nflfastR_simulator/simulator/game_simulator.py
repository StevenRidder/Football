"""
GameSimulator: Orchestrates full game simulation play-by-play.

Per strategy doc:
1. Initialize game state
2. Simulate each drive
3. For each play:
   - Decide play type based on situation
   - Simulate play outcome
   - Update game state
4. Handle special situations (4th down, FG, punt)
5. Track game flow and score
6. Run Monte Carlo (10,000 simulations)
"""

import numpy as np
from typing import Dict, List, Optional

try:
    from .game_state import GameState
    from .team_profile import TeamProfile
    from .play_simulator import PlaySimulator
    from .tracing import SimTrace
except ImportError:
    from game_state import GameState
    from team_profile import TeamProfile
    from play_simulator import PlaySimulator
    from tracing import SimTrace


class GameSimulator:
    """Simulates entire NFL game play-by-play."""
    
    def __init__(self, home_team: TeamProfile, away_team: TeamProfile, 
                 game_id: str = None, season: int = None, week: int = None,
                 trace: Optional[SimTrace] = None, seed: Optional[int] = None):
        """
        Initialize game simulator.
        
        Args:
            home_team: Home team profile
            away_team: Away team profile
            game_id: Optional game ID to load situational factors
            season: Optional season for situational factors
            week: Optional week for situational factors
            trace: Optional SimTrace for logging (creates new one if None)
            seed: Optional random seed for reproducibility
        """
        self.home_team = home_team
        self.away_team = away_team
        
        # Initialize trace
        if trace is None:
            game_id_str = game_id or f"{season}_{week}_{away_team.team}_{home_team.team}"
            trace = SimTrace(game_id=game_id_str, seed=seed)
        self.trace = trace
        
        # Set random seed if provided
        if seed is not None:
            np.random.seed(seed)
        
        # Load situational factors if game info provided
        if game_id and season and week:
            self._load_situational_factors(game_id, season, week)
        
        # Log input audit
        self.trace.log("inputs.audit", {
            "home": self.home_team.as_dict_for_audit(),
            "away": self.away_team.as_dict_for_audit(),
            "situational": {
                "is_dome": getattr(self.home_team, 'is_dome', False),
                "temp": getattr(self.home_team, 'temperature', None),
                "wind": getattr(self.home_team, 'wind', None),
                "home_rest_days": getattr(self.home_team, 'home_rest_days', 7),
                "away_rest_days": getattr(self.away_team, 'away_rest_days', 7)
            },
            "seed": seed
        })
    
    def _load_situational_factors(self, game_id: str, season: int, week: int):
        """Load situational factors from CSV for this specific game."""
        from pathlib import Path
        import pandas as pd
        
        data_dir = Path(__file__).parent.parent / "data" / "nflfastR"
        factors_file = data_dir / "situational_factors.csv"
        
        if not factors_file.exists():
            return  # Use defaults
        
        factors_df = pd.read_csv(factors_file)
        game_factors = factors_df[
            (factors_df['game_id'] == game_id) |
            ((factors_df['season'] == season) & 
             (factors_df['week'] == week) &
             (factors_df['home_team'] == self.home_team.team) &
             (factors_df['away_team'] == self.away_team.team))
        ]
        
        if len(game_factors) > 0:
            row = game_factors.iloc[0]
            # FIXED: Home team gets home_rest_days, away team gets away_rest_days
            # Note: set_situational_factors uses home_rest for the team's own rest days
            self.home_team.set_situational_factors(
                home_rest=int(row.get('home_rest_days', 7)),  # Home team's rest days
                away_rest=int(row.get('away_rest_days', 7)),  # Opponent's rest days
                is_dome=bool(row.get('is_dome', False)),
                temp=float(row.get('temp')) if pd.notna(row.get('temp')) else None,
                wind=float(row.get('wind')) if pd.notna(row.get('wind')) else None
            )
            self.away_team.set_situational_factors(
                home_rest=int(row.get('away_rest_days', 7)),  # Away team's rest days
                away_rest=int(row.get('home_rest_days', 7)),  # Opponent's rest days
                is_dome=bool(row.get('is_dome', False)),
                temp=float(row.get('temp')) if pd.notna(row.get('temp')) else None,
                wind=float(row.get('wind')) if pd.notna(row.get('wind')) else None
            )
    
    def simulate_game(self) -> Dict:
        """
        Run one simulation of the game.
        
        Returns:
            Dict with keys:
                - home_score: Final home score
                - away_score: Final away score
                - spread: Away score - home score
                - total: Combined score
        """
        # Initialize game state
        game_state = GameState()
        
        # FIXED: Randomize opening possession (coin toss simulation)
        # Real NFL: coin toss winner chooses to receive or defer
        # We'll randomize: 50% home, 50% away
        opening_possession = 'home' if np.random.random() < 0.5 else 'away'
        game_state.possession = opening_possession
        game_state.start_new_drive()
        
        # Simulate until game is over
        while not game_state.is_game_over():
            # Determine which team has possession
            if game_state.possession == 'home':
                offense, defense = self.home_team, self.away_team
            else:
                offense, defense = self.away_team, self.home_team
            
            # Simulate drive
            self._simulate_drive(game_state, offense, defense)
        
        # Calculate game metrics for realism guards
        all_drives = self.trace.get_events("drive.summary")
        total_drives = len(all_drives)
        drives_per_team = total_drives / 2 if total_drives > 0 else 0
        
        td_count = sum(1 for d in all_drives if d.get('result') == 'TD')
        fg_count = sum(1 for d in all_drives if 'FG' in str(d.get('result', '')))
        to_count = sum(1 for d in all_drives if 'Turnover' in str(d.get('result', '')))
        
        total_plays = sum(d.get('plays', 0) for d in all_drives)
        plays_per_drive = total_plays / total_drives if total_drives > 0 else 0
        
        td_pct = td_count / total_drives if total_drives > 0 else 0
        fg_pct = fg_count / total_drives if total_drives > 0 else 0
        to_pct = to_count / total_drives if total_drives > 0 else 0
        
        # Get explosive plays from anchor_slice events
        anchor_slices = self.trace.get_events("anchor_slice")
        explosive_count = sum(s.get('explosive_count', 0) for s in anchor_slices)
        explosive_rate = explosive_count / total_plays if total_plays > 0 else 0
        
        # Get pass rate from play events
        play_events = self.trace.get_events("call.pass_run")
        pass_count = sum(1 for p in play_events if p.get('choice') == 'pass')
        pass_rate = pass_count / len(play_events) if len(play_events) > 0 else 0
        
        # Log game summary
        self.trace.log("game.summary", {
            "home_score": game_state.home_score,
            "away_score": game_state.away_score,
            "spread": game_state.away_score - game_state.home_score,
            "total": game_state.home_score + game_state.away_score,
            "drives_per_team": drives_per_team,
            "plays_per_drive": plays_per_drive,
            "td_pct": td_pct,
            "fg_pct": fg_pct,
            "turnover_pct": to_pct,
            "explosive_rate": explosive_rate,
            "pass_rate": pass_rate
        })
        
        # Run realism guards
        self._check_realism_guards(
            plays_per_drive, drives_per_team, td_pct, fg_pct, to_pct,
            explosive_rate, pass_rate, game_state.home_score + game_state.away_score
        )
        
        return {
            'home_score': game_state.home_score,
            'away_score': game_state.away_score,
            'spread': game_state.away_score - game_state.home_score,
            'total': game_state.home_score + game_state.away_score
        }
    
    def _simulate_drive(self, game_state: GameState, offense: TeamProfile, defense: TeamProfile):
        """
        Simulate one drive.
        
        Args:
            game_state: Current game state
            offense: Offensive team profile
            defense: Defensive team profile
        """
        play_sim = PlaySimulator(offense, defense, trace=self.trace)
        
        # Track drive metrics for anchor_slice logging
        drive_start_state = {
            "drive_num": game_state.drive_number,
            "team": game_state.possession,
            "start_yardline": game_state.yardline,
            "start_quarter": game_state.quarter,
            "start_time": game_state.time_remaining
        }
        drive_plays = 0
        drive_points = 0
        drive_successful_plays = 0
        drive_explosive_plays = 0
        drive_start_time = game_state.time_remaining
        result_text = "Unknown"  # Initialize
        
        # FIXED: Possessions-first clock model targeting 10-15 possessions per team
        # Strategy: Let clock drive drive endings, not fixed play caps
        # Pace influences time-per-play and out-of-bounds rates
        
        # Target: 10-15 possessions per team = 20-30 total drives
        # 60 minutes = 3600 seconds / ~30 drives = ~120 seconds per drive
        # But we need to account for scoring plays (TD = ~0 seconds, FG = ~0 seconds)
        # Average drive: ~6 plays × variable time per play
        
        # Calculate time per play based on pace (faster teams = less time per play)
        # Pace range: ~5-7 plays/drive typically
        # Faster teams (higher pace) = less time per snap
        base_time_per_play = 40.0  # Base: 40 seconds per play
        pace_factor = offense.pace / 6.0  # Normalize pace (6.0 = league average)
        time_per_play = base_time_per_play * (1.0 / pace_factor)  # Faster = less time
        
        # Clamp to reasonable range
        time_per_play = np.clip(time_per_play, 25.0, 50.0)
        
        # Two-minute drill: reduce time per play
        if game_state.game_seconds_remaining < 120:
            time_per_play = 25.0  # Hurry-up
        
        # Drive ends when: score, turnover, clock expires, or 4th down decision
        plays_run = 0
        max_plays_safety = 30  # Absolute safety limit (prevents infinite loops)
        
        while plays_run < max_plays_safety and not game_state.is_game_over():
            plays_run += 1
            
            # Check for 4th down decision
            if game_state.down == 4:
                # Log 4th down decision with counterfactuals
                fg_decision, fg_reasoning = game_state.should_attempt_fg()
                punt_decision, punt_reasoning = game_state.should_punt()
                
                # Calculate counterfactual EPAs (simplified)
                # FG: expected points from FG attempt
                fg_epa = 0.85 * 3.0 if fg_decision else -3.0  # Simplified
                # Punt: expected field position value
                punt_epa = -0.5  # Simplified (negative field position)
                # Go for it: expected points from conversion
                go_epa = 2.0 if game_state.yardline >= 50 else -2.0  # Simplified
                
                decision_taken = None
                if fg_decision:
                    decision_taken = "FG"
                elif punt_decision:
                    decision_taken = "Punt"
                else:
                    decision_taken = "Go"
                
                self.trace.log("policy_decision", {
                    "quarter": game_state.quarter,
                    "time_remaining": game_state.time_remaining,
                    "yardline": game_state.yardline,
                    "to_go": game_state.ydstogo,
                    "score_diff": game_state.score_differential,
                    "fg_epa": fg_epa,
                    "punt_epa": punt_epa,
                    "go_epa": go_epa,
                    "decision": decision_taken,
                    "fg_reasoning": fg_reasoning,
                    "punt_reasoning": punt_reasoning
                })
                
                if fg_decision:
                    # Attempt field goal
                    fg_result = play_sim.simulate_field_goal(game_state)
                    if fg_result['made']:
                        game_state.add_points(3, game_state.possession)
                        drive_points = 3
                    game_state.switch_possession()
                    game_state.start_new_drive()
                    result_text = "FG" if fg_result['made'] else "Missed_FG"
                    break
                
                elif punt_decision:
                    # Punt
                    punt_result = play_sim.simulate_punt(game_state)
                    game_state.switch_possession()
                    game_state.yardline = 100 - (game_state.yardline + punt_result['net_yards'])
                    game_state.yardline = np.clip(game_state.yardline, 0, 100)
                    game_state.start_new_drive()
                    result_text = "Punt"
                    break
                
                # Otherwise, go for it on 4th down (fall through to normal play)
            
            # Decide play type
            play_type = play_sim.decide_play_type(game_state)
            
            # Simulate play
            if play_type == 'pass':
                play_result = play_sim.simulate_pass_play(game_state)
            else:
                play_result = play_sim.simulate_run_play(game_state)
            
            # Update game state FIRST (needed for down/distance checks)
            # We'll apply early-down success logic AFTER state update
            yards_before = game_state.yardline
            ydstogo_before = game_state.ydstogo
            down_before = game_state.down
            
            # Update game state
            game_state.update_from_play(play_result)
            
            # FIXED: Advance clock based on pace-adjusted time per play
            # Clock stops on: incompletions (out of bounds), scores, turnovers, timeouts
            # Clock runs on: runs, completions in bounds
            
            # Check if play stops clock (incomplete, out of bounds, timeout)
            clock_stops = (
                play_result.get('type') == 'incomplete' or
                play_result.get('type') == 'sack' or
                play_result.get('turnover', False)
            )
            
            if not clock_stops:
                # Clock runs: advance by time_per_play
                game_state.time_remaining = max(0, game_state.time_remaining - int(time_per_play))
            
            # Check if quarter expired
            if game_state.time_remaining == 0 and game_state.quarter < 4:
                game_state.advance_quarter()
                # Continue drive if possession doesn't change
                if game_state.possession == drive_start_state["team"]:
                    continue
                else:
                    # Possession changed (end of half)
                    break
            
            # Track drive metrics
            drive_plays += 1
            if play_result.get('td', False):
                drive_points = 7 if play_result.get('xp', True) else 6
                result_text = "TD"
            if play_result.get('yards', 0) >= 15:
                drive_explosive_plays += 1
            # Track successful plays (simplified: first down or TD)
            if game_state.down == 1 or play_result.get('td', False):
                drive_successful_plays += 1
            
            # USE EARLY-DOWN SUCCESS RATE: Adjust first down probability on early downs
            # Strategy: Teams with higher early-down success extend drives more
            # After state update, check if we're on early down and adjust continuation probability
            if down_before <= 2 and not play_result.get('turnover', False):
                yards_gained = play_result.get('yards', 0)
                
                # Determine if play was successful (per strategy: 40% of needed on 1st, 50% on 2nd)
                if down_before == 1:
                    is_successful = yards_gained >= (0.4 * ydstogo_before)
                else:  # down == 2
                    is_successful = yards_gained >= (0.5 * ydstogo_before)
                
                # If successful but didn't get first down, check for bonus conversion
                if is_successful and game_state.down > 1:  # Didn't convert to first down
                    team_success_rate = offense.early_down_success_rate
                    league_avg_success = 0.48  # ~48% league average
                    success_advantage = team_success_rate - league_avg_success
                    
                    # Small bonus chance to convert: each +10% success rate = +3% conversion bonus
                    first_down_bonus = max(0, success_advantage * 0.3)  # Only positive bonuses
                    
                    # Only apply if close to first down (within 20% of needed)
                    if yards_gained >= (ydstogo_before * 0.8):
                        if np.random.random() < first_down_bonus:
                            # Grant first down bonus
                            game_state.down = 1
                            game_state.ydstogo = min(10, 100 - game_state.yardline)
            
            # Check if drive ended (TD, turnover, etc.)
            if play_result.get('td', False) or play_result.get('turnover', False):
                if play_result.get('turnover', False):
                    result_text = "Turnover"
                break
            
            # Check if we switched possession (turnover on downs)
            if game_state.plays_this_drive == 0:
                result_text = "Turnover_on_Downs"
                break
        
        # Log drive summary with anchor_slice
        drive_time_used = drive_start_time - game_state.time_remaining
        drive_success_rate = drive_successful_plays / drive_plays if drive_plays > 0 else 0
        drive_explosive_rate = drive_explosive_plays / drive_plays if drive_plays > 0 else 0
        
        self.trace.log("drive.summary", {
            "drive_no": drive_start_state["drive_num"],
            "team": drive_start_state["team"],
            "plays": drive_plays,
            "points": drive_points,
            "time_used": drive_time_used,
            "result": result_text,
            "start_state": drive_start_state,
            "end_state": {
                "yardline": game_state.yardline,
                "quarter": game_state.quarter,
                "time_remaining": game_state.time_remaining
            }
        })
        
        # Log anchor_slice per drive
        self.trace.log("anchor_slice", {
            "drive_no": drive_start_state["drive_num"],
            "team": drive_start_state["team"],
            "pace": drive_plays,  # Plays in this drive
            "success_rate": drive_success_rate,
            "explosive_rate": drive_explosive_rate,
            "explosive_count": drive_explosive_plays,
            "result": result_text
        })
    
    def simulate_monte_carlo(self, n_sims: int = 10000) -> Dict:
        """
        Run Monte Carlo simulation (multiple game simulations).
        
        Args:
            n_sims: Number of simulations to run
        
        Returns:
            Dict with keys:
                - results: List of individual game results
                - home_score_avg: Average home score
                - away_score_avg: Average away score
                - spread_avg: Average spread
                - total_avg: Average total
                - home_win_prob: Probability home team wins
                - spread_distribution: Array of spread results
                - total_distribution: Array of total results
        """
        results = []
        
        for _ in range(n_sims):
            result = self.simulate_game()
            results.append(result)
        
        # Aggregate results
        home_scores = [r['home_score'] for r in results]
        away_scores = [r['away_score'] for r in results]
        spreads = [r['spread'] for r in results]
        totals = [r['total'] for r in results]
        
        return {
            'results': results,
            'home_score_avg': np.mean(home_scores),
            'home_score_median': np.median(home_scores),
            'away_score_avg': np.mean(away_scores),
            'away_score_median': np.median(away_scores),
            'spread_avg': np.mean(spreads),
            'spread_median': np.median(spreads),
            'total_avg': np.mean(totals),
            'total_median': np.median(totals),
            'home_win_prob': sum(1 for r in results if r['home_score'] > r['away_score']) / n_sims,
            'spread_distribution': np.array(spreads),
            'total_distribution': np.array(totals)
        }
    
    def get_betting_recommendations(self, mc_results: Dict, market_spread: float, market_total: float) -> Dict:
        """Alias for get_betting_recommendations_centered for backward compatibility."""
        return self.get_betting_recommendations_centered(mc_results, market_spread, market_total)
    
    def get_betting_recommendations_centered(self, mc_results: Dict, market_spread: float, market_total: float) -> Dict:
        """
        FIXED: Uses market centering for consistency with backtest pipeline.
        
        Compare simulation results to market lines and identify value bets.
        
        Args:
            mc_results: Results from simulate_monte_carlo()
            market_spread: Market spread (negative = home favored)
            market_total: Market total (over/under)
        
        Returns:
            Dict with betting recommendations
        """
        # FIXED: Use market centering for consistency with backtest
        try:
            from .market_centering import center_to_market
            
            # Convert MC results to format expected by center_to_market
            # If we have spread/total distributions, reconstruct home/away scores
            if 'spread_distribution' in mc_results and 'total_distribution' in mc_results:
                spread_raw = mc_results['spread_distribution']
                total_raw = mc_results['total_distribution']
                # Reconstruct home/away scores
                home_raw = (total_raw + spread_raw) / 2
                away_raw = (total_raw - spread_raw) / 2
                mc_results['home_score_distribution'] = home_raw
                mc_results['away_score_distribution'] = away_raw
            
            # Center the MC results to market
            centered_results = center_to_market(mc_results, market_spread, market_total)
            # Use centered distributions for betting decisions
            spread_dist = centered_results['spread_distribution']
            total_dist = centered_results['total_distribution']
        except ImportError:
            # Fallback if market_centering not available
            spread_dist = mc_results['spread_distribution']
            total_dist = mc_results['total_distribution']
        
        # Spread analysis (using centered distributions)
        # Home covers if actual spread < market spread (home wins by more than expected)
        home_cover_prob = (spread_dist < market_spread).mean()
        away_cover_prob = 1 - home_cover_prob
        
        # Spread edge (difference between our prediction and market)
        spread_edge = np.median(spread_dist) - market_spread
        
        # Spread recommendation
        if abs(spread_edge) >= 1.5:  # At least 1.5 point edge
            if spread_edge < 0:
                spread_bet = 'home'
                spread_confidence = home_cover_prob
            else:
                spread_bet = 'away'
                spread_confidence = away_cover_prob
        else:
            spread_bet = None
            spread_confidence = 0.5
        
        # Total analysis (using centered distributions)
        # Over if actual total > market total
        over_prob = (total_dist > market_total).mean()
        under_prob = 1 - over_prob
        
        # Total edge
        total_edge = np.median(total_dist) - market_total
        
        # Total recommendation
        if abs(total_edge) >= 2.0:  # At least 2 point edge
            if total_edge > 0:
                total_bet = 'over'
                total_confidence = over_prob
            else:
                total_bet = 'under'
                total_confidence = under_prob
        else:
            total_bet = None
            total_confidence = 0.5
        
        return {
            'spread_bet': spread_bet,
            'spread_edge': spread_edge,
            'spread_confidence': spread_confidence,
            'home_cover_prob': home_cover_prob,
            'away_cover_prob': away_cover_prob,
            'total_bet': total_bet,
            'total_edge': total_edge,
            'total_confidence': total_confidence,
            'over_prob': over_prob,
            'under_prob': under_prob,
            'home_win_prob': (spread_dist < 0).mean()  # Home wins if spread < 0
        }
    
    def _check_realism_guards(self, plays_per_drive: float, drives_per_team: float,
                              td_pct: float, fg_pct: float, to_pct: float,
                              explosive_rate: float, pass_rate: float, total_points: int):
        """Check if simulation output matches NFL reality."""
        
        guards = [
            ("plays_per_drive", plays_per_drive, (5.5, 7.0)),
            ("drives_per_team", drives_per_team, (9.5, 12.5)),
            ("td_pct", td_pct, (0.18, 0.26)),
            ("fg_pct", fg_pct, (0.08, 0.12)),
            ("turnover_pct", to_pct, (0.09, 0.12)),
            ("explosive_rate", explosive_rate, (0.10, 0.12)),
            ("pass_rate", pass_rate, (0.58, 0.62)),
            ("total_points", total_points, (42, 46))
        ]
        
        violations = []
        for metric, observed, (min_val, max_val) in guards:
            if not (min_val <= observed <= max_val):
                violations.append({
                    "metric": metric,
                    "observed": observed,
                    "target_range": (min_val, max_val),
                    "violation": "too_low" if observed < min_val else "too_high"
                })
        
        if violations:
            self.trace.log("anchors.violation", {
                "violations": violations,
                "severity": "warning" if len(violations) <= 2 else "critical"
            })
        else:
            self.trace.log("anchors.pass", {
                "message": "All realism guards passed"
            })

