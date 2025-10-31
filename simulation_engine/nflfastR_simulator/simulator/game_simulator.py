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
from typing import Dict, List

try:
    from .game_state import GameState
    from .team_profile import TeamProfile
    from .play_simulator import PlaySimulator
except ImportError:
    from game_state import GameState
    from team_profile import TeamProfile
    from play_simulator import PlaySimulator


class GameSimulator:
    """Simulates entire NFL game play-by-play."""
    
    def __init__(self, home_team: TeamProfile, away_team: TeamProfile, 
                 game_id: str = None, season: int = None, week: int = None):
        """
        Initialize game simulator.
        
        Args:
            home_team: Home team profile
            away_team: Away team profile
            game_id: Optional game ID to load situational factors
            season: Optional season for situational factors
            week: Optional week for situational factors
        """
        self.home_team = home_team
        self.away_team = away_team
        
        # Load situational factors if game info provided
        if game_id and season and week:
            self._load_situational_factors(game_id, season, week)
    
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
            self.home_team.set_situational_factors(
                home_rest=int(row.get('home_rest_days', 7)),
                away_rest=int(row.get('away_rest_days', 7)),
                is_dome=bool(row.get('is_dome', False)),
                temp=float(row.get('temp')) if pd.notna(row.get('temp')) else None,
                wind=float(row.get('wind')) if pd.notna(row.get('wind')) else None
            )
            self.away_team.set_situational_factors(
                home_rest=int(row.get('home_rest_days', 7)),
                away_rest=int(row.get('away_rest_days', 7)),
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
        
        # Home team receives opening kickoff
        game_state.possession = 'home'
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
        play_sim = PlaySimulator(offense, defense)
        
        # USE PACE METRIC: Determine max plays per drive based on team pace
        # Strategy: Pace controls drive length - faster teams = more plays per drive
        avg_plays_per_drive = offense.pace  # Loaded from team profile
        max_plays = int(avg_plays_per_drive * 1.5)  # Allow 50% over average
        max_plays = np.clip(max_plays, 10, 25)  # Safety limits
        plays_run = 0
        
        while plays_run < max_plays and not game_state.is_game_over():
            plays_run += 1
            
            # Check for end of quarter
            if game_state.time_remaining == 0 and game_state.quarter < 4:
                game_state.advance_quarter()
                continue
            
            # Check for 4th down decision
            if game_state.down == 4:
                if game_state.should_attempt_fg():
                    # Attempt field goal
                    fg_result = play_sim.simulate_field_goal(game_state)
                    if fg_result['made']:
                        game_state.add_points(3, game_state.possession)
                    game_state.switch_possession()
                    game_state.start_new_drive()
                    return
                
                elif game_state.should_punt():
                    # Punt
                    punt_result = play_sim.simulate_punt(game_state)
                    game_state.switch_possession()
                    game_state.yardline = 100 - (game_state.yardline + punt_result['net_yards'])
                    game_state.yardline = np.clip(game_state.yardline, 0, 100)
                    game_state.start_new_drive()
                    return
                
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
                return
            
            # Check if we switched possession (turnover on downs)
            if game_state.plays_this_drive == 0:
                return
    
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
    
    def get_betting_recommendations_centered(self, mc_results: Dict, market_spread: float, market_total: float) -> Dict:
        """
        Compare simulation results to market lines and identify value bets.
        
        Args:
            mc_results: Results from simulate_monte_carlo()
            market_spread: Market spread (negative = home favored)
            market_total: Market total (over/under)
        
        Returns:
            Dict with betting recommendations
        """
        # Spread analysis
        spread_dist = mc_results['spread_distribution']
        
        # Home covers if actual spread < market spread (home wins by more than expected)
        home_cover_prob = (spread_dist < market_spread).mean()
        away_cover_prob = 1 - home_cover_prob
        
        # Spread edge (difference between our prediction and market)
        spread_edge = mc_results['spread_median'] - market_spread
        
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
        
        # Total analysis
        total_dist = mc_results['total_distribution']
        
        # Over if actual total > market total
        over_prob = (total_dist > market_total).mean()
        under_prob = 1 - over_prob
        
        # Total edge
        total_edge = mc_results['total_median'] - market_total
        
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
            'home_win_prob': mc_results['home_win_prob']
        }

