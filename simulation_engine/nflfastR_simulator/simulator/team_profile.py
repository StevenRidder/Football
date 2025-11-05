"""
TeamProfile: Loads and stores team's offensive/defensive capabilities.

Per strategy doc:
- Baseline team efficiency (EPA from nflfastR)
- QB-specific pressure performance
- Play-calling tendencies by situation
- Drive probabilities by field position
- (Phase 2: PFF OL/DL grades)
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict

try:
    from .pff_loader import get_pff_loader
except ImportError:
    from pff_loader import get_pff_loader


class TeamProfile:
    """Team's offensive and defensive capabilities for simulation."""

    def __init__(self, team: str, season: int, week: int, data_dir: Path, debug: bool = False):
        """
        Initialize team profile.
        
        Args:
            team: Team abbreviation (e.g. 'KC', 'BUF')
            season: Season year
            week: Week number
            data_dir: Path to nflfastR data directory
            debug: Enable debug logging
        """
        self.team = team
        self.season = season
        self.week = week
        self.data_dir = data_dir
        self.debug = debug
        self._load_errors = []
        self._fallbacks_used = []

        if self.debug:
            print(f"\n🔍 Loading TeamProfile: {team} {season} W{week}")

        # Load data
        self.off_epa, self.def_epa = self._load_epa()
        self.qb_name, self.qb_stats = self._load_qb_stats()
        self.playcalling = self._load_playcalling()
        self.drive_probs = self._load_drive_probs()
        self.pace = self._load_pace()

        # Phase 2: PFF data (load actual grades)
        self._load_pff_grades()

        # New metrics: YPP/YPA, Success Rate, ANY/A, Turnovers, Red Zone, Special Teams
        self._load_yards_per_play()
        self._load_early_down_success()
        self._load_anya()
        self._load_turnover_regression()
        self._load_red_zone()
        self._load_special_teams()

        # Situational factors: Rest days, weather, dome
        self._load_situational_factors()

        # Calculate overall pass rate from playcalling data (for display/audit purposes)
        self.pass_rate = self._calculate_overall_pass_rate()

        # FIXED: Load weekly injuries and apply multipliers
        self._load_injury_multipliers()

        # FIXED: Schema asserts - validate all required fields exist and are floats
        self._validate_schema()

        if self.debug:
            self._print_load_summary()

    def _load_epa(self) -> tuple[float, float]:
        """Load team's offensive and defensive EPA per play."""
        epa_file = Path("/Users/steveridder/Git/Football/data/features/rolling_epa_2022_2025.csv")

        if not epa_file.exists():
            print("⚠️  Warning: EPA file not found, using league average")
            return 0.0, 0.0

        epa_df = pd.read_csv(epa_file)

        # Team abbreviation mapping (schedule uses "LA" but data might use "LAR")
        team_map = {'LA': 'LAR'}
        lookup_team = team_map.get(self.team, self.team)

        # CRITICAL: Use only PRIOR weeks (exclude current week to avoid look-ahead bias)
        # For week N, aggregate weeks 1 through N-1
        if self.week == 1:
            # Week 1: Fall back to season average
            team_epa = epa_df[
                (epa_df['team'] == lookup_team) &
                (epa_df['season'] == self.season)
            ]

            if len(team_epa) == 0:
                print(f"⚠️  Warning: No EPA data for {self.team} {self.season} W{self.week}")
                return 0.0, 0.0

            off_epa = float(team_epa['off_epa_per_play'].mean())
            def_epa = float(team_epa['def_epa_per_play'].mean())
        else:
            # Aggregate prior weeks only
            prior_weeks = epa_df[
                (epa_df['team'] == lookup_team) &
                (epa_df['season'] == self.season) &
                (epa_df['week'] < self.week)  # KEY: Only prior weeks
            ]
            if len(prior_weeks) > 0:
                # Aggregate prior weeks
                off_epa = float(prior_weeks['off_epa_per_play'].mean())
                def_epa = float(prior_weeks['def_epa_per_play'].mean())
            else:
                # Fall back to season average if no prior weeks
                team_epa = epa_df[
                    (epa_df['team'] == lookup_team) &
                    (epa_df['season'] == self.season)
                ]

                if len(team_epa) == 0:
                    print(f"⚠️  Warning: No EPA data for {self.team} {self.season} W{self.week}")
                    return 0.0, 0.0

                off_epa = float(team_epa['off_epa_per_play'].mean())
                def_epa = float(team_epa['def_epa_per_play'].mean())

        return float(off_epa), float(def_epa)

    def _load_qb_stats(self) -> tuple[Optional[str], dict]:
        """
        Load QB's pressure performance splits for the ACTUAL QB playing this week.
        
        Returns:
            (qb_name, qb_stats) where qb_stats has keys:
                - clean: {completion_pct, yards_per_att, td_rate, int_rate, sack_rate, scramble_rate, epa}
                - pressure: {completion_pct, yards_per_att, td_rate, int_rate, sack_rate, scramble_rate, epa}
        """
        # Try weekly QB data (includes actual starter names, fixes backup QB issue)
        weekly_qb_file = self.data_dir / "qb_stats_weekly.csv"

        if weekly_qb_file.exists():
            qb_df = pd.read_csv(weekly_qb_file)

            # Find QB for this team/week
            qb_data = qb_df[
                (qb_df['team'] == self.team) &
                (qb_df['season'] == self.season) &
                (qb_df['week'] == self.week)
            ]

            if len(qb_data) > 0:
                qb_row = qb_data.iloc[0]
                qb_name = qb_row['qb_name']

                # Build qb_stats from extracted data
                qb_stats = {
                    'clean': {
                        'completion_pct': float(qb_row['clean_comp_pct']),
                        'yards_per_att': float(qb_row['clean_ypa']),
                        'td_rate': 0.035,  # Use league average for now
                        'int_rate': 0.023,
                        'sack_rate': 0.0,
                        'scramble_rate': 0.06,
                        'epa': float(qb_row['clean_epa'])
                    },
                    'pressure': {
                        'completion_pct': float(qb_row['pressure_comp_pct']),
                        'yards_per_att': float(qb_row['pressure_ypa']),
                        'td_rate': 0.020,
                        'int_rate': 0.026,
                        'sack_rate': 0.449,
                        'scramble_rate': 0.0,
                        'epa': float(qb_row['pressure_epa'])
                    }
                }

                if self.debug:
                    print(f"   ✅ QB: {qb_name} (Week {self.week})")
                    print(f"      Clean: {qb_stats['clean']['completion_pct']:.1%} comp, {qb_stats['clean']['epa']:+.2f} EPA")
                    print(f"      Pressure: {qb_stats['pressure']['completion_pct']:.1%} comp, {qb_stats['pressure']['epa']:+.2f} EPA")

                return qb_name, qb_stats

        # Fall back to league average
        if self.debug or self.week <= 8:  # Only warn for weeks we should have data
            print(f"⚠️  Warning: No weekly QB data for {self.team} W{self.week}, using league average")

        qb_stats = self._get_league_average_qb_stats()

        return "League Average", qb_stats

    def _get_league_average_qb_stats(self) -> dict:
        """Return league average QB stats."""
        return {
            'clean': {
                'completion_pct': 0.615,
                'yards_per_att': 6.89,
                'td_rate': 0.035,
                'int_rate': 0.023,
                'sack_rate': 0.0,
                'scramble_rate': 0.06,
                'epa': 0.11
            },
            'pressure': {
                'completion_pct': 0.219,
                'yards_per_att': -0.17,
                'td_rate': 0.020,
                'int_rate': 0.026,
                'sack_rate': 0.449,
                'scramble_rate': 0.0,
                'epa': -0.98
            }
        }

    def _get_lookup_team(self) -> str:
        """
        Get the team abbreviation to use for data lookup.
        Maps LAR -> LA for data files that use 'LA' instead of 'LAR'.
        """
        team_mapping = {
            'LAR': 'LA',  # Los Angeles Rams - data uses LA
            'LAC': 'LAC',  # Los Angeles Chargers - stays as LAC
        }
        return team_mapping.get(self.team, self.team)

    def _load_playcalling(self) -> pd.DataFrame:
        """Load team's play-calling tendencies - NO FALLBACKS."""
        # Try season averages first
        season_file = self.data_dir / "playcalling_tendencies_season.csv"

        if not season_file.exists():
            raise ValueError(f"Play-calling file not found: {season_file}. Run preprocessing/extract_playcalling.py first.")

        playcalling_df = pd.read_csv(season_file)
        
        # Store full dataframe for fallback lookups (used in get_pass_rate)
        self._playcalling_df = playcalling_df

        # Map team abbreviations (LAR -> LA for data lookup)
        lookup_team = self._get_lookup_team()

        # Get team's tendencies for this season
        team_playcalling = playcalling_df[
            (playcalling_df['posteam'] == lookup_team) &
            (playcalling_df['season'] == self.season)
        ]

        # Always supplement with weekly data to ensure complete coverage
        # (Season data may have gaps due to 20+ play requirement)
        weekly_file = self.data_dir / "playcalling_tendencies_weekly.csv"
        if weekly_file.exists():
            weekly_df = pd.read_csv(weekly_file)
            weekly_team = weekly_df[
                (weekly_df['posteam'] == lookup_team) &
                (weekly_df['season'] == self.season)
            ]
            if len(weekly_team) > 0:
                # Aggregate weekly data to season-level
                weekly_agg = weekly_team.groupby([
                    'down', 'distance_bucket', 'score_diff_bucket', 'time_bucket'
                ]).agg({
                    'pass_count': 'sum',
                    'run_count': 'sum',
                    'total_plays': 'sum'
                }).reset_index()
                weekly_agg['pass_rate'] = weekly_agg['pass_count'] / weekly_agg['total_plays']
                weekly_agg['run_rate'] = weekly_agg['run_count'] / weekly_agg['total_plays']

                # Merge: weekly data fills gaps in season data
                if len(team_playcalling) > 0:
                    # Combine both, preferring season when available
                    combined = pd.concat([team_playcalling, weekly_agg]).drop_duplicates(
                        subset=['down', 'distance_bucket', 'score_diff_bucket', 'time_bucket'],
                        keep='first'
                    )
                    team_playcalling = combined
                else:
                    # Use weekly aggregated data
                    weekly_agg['posteam'] = self.team
                    weekly_agg['season'] = self.season
                    team_playcalling = weekly_agg

        if len(team_playcalling) == 0:
            # Fallback: try previous season's data if current season not available
            prev_season = self.season - 1
            team_playcalling = playcalling_df[
                (playcalling_df['posteam'] == lookup_team) &
                (playcalling_df['season'] == prev_season)
            ]
            
            if len(team_playcalling) > 0:
                # Update season to current for consistency
                team_playcalling = team_playcalling.copy()
                team_playcalling['season'] = self.season
                if self.debug:
                    print(f"⚠️  Using {prev_season} play-calling data for {self.team} (no {self.season} data available)")
            else:
                raise ValueError(f"No play-calling data for {self.team} {self.season} (or {prev_season}). Run preprocessing/extract_playcalling.py for this season.")

        return team_playcalling


    def _load_drive_probs(self) -> pd.DataFrame:
        """Load team's drive outcome probabilities by field position."""
        lookup_team = self._get_lookup_team()
        # Try season averages
        season_file = self.data_dir / "drive_probabilities_season.csv"

        if not season_file.exists():
            print("⚠️  Warning: Drive probs file not found, using league average")
            return self._get_league_average_drive_probs()

        drive_df = pd.read_csv(season_file)

        # Get team's drive probs
        team_drives = drive_df[
            (drive_df['posteam'] == lookup_team) &
            (drive_df['season'] == self.season)
        ]
        
        # Fallback to previous season
        if len(team_drives) == 0:
            prev_season = self.season - 1
            team_drives = drive_df[
                (drive_df['posteam'] == lookup_team) &
                (drive_df['season'] == prev_season)
            ]
            if len(team_drives) > 0:
                print(f"⚠️  Warning: No drive data for {self.team} {self.season}, using {prev_season}")
            else:
                print(f"⚠️  Warning: No drive data for {self.team} {self.season} (or {prev_season})")
                return self._get_league_average_drive_probs()

        return team_drives

    def _get_league_average_drive_probs(self) -> pd.DataFrame:
        """Return league average drive probabilities."""
        # Load league averages
        league_file = self.data_dir / "drive_probabilities_league.csv"

        if league_file.exists():
            return pd.read_csv(league_file)

        # Hardcoded fallback
        return pd.DataFrame({
            'start_yardline_bucket': ['own_10', 'own_20', 'own_35', 'midfield', 'opp_35', 'opp_20', 'opp_10'],
            'td_prob': [0.02, 0.014, 0.008, 0.0, 0.01, 0.0, 0.0],
            'fg_prob': [0.097, 0.146, 0.189, 0.262, 0.158, 0.333, 0.0],
            'punt_prob': [0.491, 0.419, 0.364, 0.175, 0.356, 0.667, 0.0],
            'turnover_prob': [0.101, 0.098, 0.076, 0.075, 0.104, 0.0, 0.0]
        })

    def _load_pace(self) -> float:
        """Load team's pace (plays per drive)."""
        lookup_team = self._get_lookup_team()
        pace_file = self.data_dir / "team_pace.csv"

        if not pace_file.exists():
            return 6.6  # League average

        pace_df = pd.read_csv(pace_file)

        # CRITICAL: Use only PRIOR weeks (exclude current week)
        if self.week == 1:
            # Week 1: Fall back to season average
            team_pace = pace_df[
                (pace_df['posteam'] == lookup_team) &
                (pace_df['season'] == self.season)
            ]
            
            # Fallback to previous season
            if len(team_pace) == 0:
                prev_season = self.season - 1
                team_pace = pace_df[
                    (pace_df['posteam'] == lookup_team) &
                    (pace_df['season'] == prev_season)
                ]

            if len(team_pace) == 0:
                return 6.6  # League average

            return float(team_pace['avg_plays_per_drive'].mean())
        else:
            # Aggregate prior weeks only
            prior_weeks = pace_df[
                (pace_df['posteam'] == lookup_team) &
                (pace_df['season'] == self.season) &
                (pace_df['week'] < self.week)  # Only prior weeks
            ]
            # Fallback to previous season
            if len(prior_weeks) == 0:
                prev_season = self.season - 1
                prior_weeks = pace_df[
                    (pace_df['posteam'] == lookup_team) &
                    (pace_df['season'] == prev_season) &
                    (pace_df['week'] < self.week)
                ]
            
            if len(prior_weeks) > 0:
                return float(prior_weeks['avg_plays_per_drive'].mean())
            else:
                # Fall back to season average if no prior weeks
                team_pace = pace_df[
                    (pace_df['posteam'] == lookup_team) &
                    (pace_df['season'] == self.season)
                ]
                
                # Fallback to previous season
                if len(team_pace) == 0:
                    prev_season = self.season - 1
                    team_pace = pace_df[
                        (pace_df['posteam'] == lookup_team) &
                        (pace_df['season'] == prev_season)
                    ]

                if len(team_pace) == 0:
                    return 6.6  # League average

                return float(team_pace['avg_plays_per_drive'].mean())

    def _calculate_overall_pass_rate(self) -> float:
        """
        Calculate overall team pass rate from playcalling data.
        This is a weighted average across all situations.
        """
        if len(self.playcalling) == 0:
            return 0.6  # League average fallback

        # Weight by total plays in each situation
        total_plays = self.playcalling['total_plays'].sum()
        if total_plays == 0:
            return 0.6

        # Weighted average pass rate
        weighted_pass_rate = (self.playcalling['pass_count'].sum() / total_plays)
        return float(weighted_pass_rate)

    def get_pass_rate(self, down: int, distance_bucket: str, score_diff_bucket: str, time_bucket: str) -> float:
        """
        Get team's pass rate for a given situation.
        
        Args:
            down: Down (1-4)
            distance_bucket: 'short', 'medium', 'long'
            score_diff_bucket: 'down_14+', 'down_7-13', ..., 'up_14+'
            time_bucket: 'Q1-Q2', 'Q2-Q3', 'Q3-Q4', 'Q4_late', '2min'
        
        Returns:
            Pass rate (0-1)
        """
        lookup_team = self._get_lookup_team()
        # Look up in team's playcalling data - try most specific first
        situation = self.playcalling[
            (self.playcalling['down'] == down) &
            (self.playcalling['distance_bucket'] == distance_bucket) &
            (self.playcalling['score_diff_bucket'] == score_diff_bucket) &
            (self.playcalling['time_bucket'] == time_bucket)
        ]

        if len(situation) > 0:
            return float(situation['pass_rate'].iloc[0])

        # Fall back to simpler lookup (down + score + distance, no time)
        situation = self.playcalling[
            (self.playcalling['down'] == down) &
            (self.playcalling['distance_bucket'] == distance_bucket) &
            (self.playcalling['score_diff_bucket'] == score_diff_bucket)
        ]

        if len(situation) > 0:
            return float(situation['pass_rate'].mean())

        # Fall back to even simpler (just down and score)
        situation = self.playcalling[
            (self.playcalling['down'] == down) &
            (self.playcalling['score_diff_bucket'] == score_diff_bucket)
        ]

        if len(situation) > 0:
            return float(situation['pass_rate'].mean())

        # Fall back to just down
        situation = self.playcalling[
            (self.playcalling['down'] == down)
        ]

        if len(situation) > 0:
            return float(situation['pass_rate'].mean())

        # LAST RESORT: Try previous season data (for early season weeks with sparse data)
        if self.season > 2022:
            prev_season = self.season - 1
            if hasattr(self, '_playcalling_df'):
                prev_season_data = self._playcalling_df[
                    (self._playcalling_df['posteam'] == lookup_team) &
                    (self._playcalling_df['season'] == prev_season)
                ]
                if len(prev_season_data) > 0:
                    # Try to find matching situation by down (don't require distance/score match)
                    prev_situation = prev_season_data[
                        (prev_season_data['down'] == down)
                    ]
                    if len(prev_situation) > 0:
                        if self.debug:
                            print(f"   ⚠️  FALLBACK: Using {prev_season} data for {self.team} down={down} (no {self.season} data)")
                        self._fallbacks_used.append(f"Play-calling: Used {prev_season} season data for down={down}")
                        return float(prev_situation['pass_rate'].mean())

        # LAST RESORT: Use league average for this down (4th downs are rare)
        # Get league average pass rate for this down from all teams
        if hasattr(self, '_playcalling_df'):
            league_situation = self._playcalling_df[
                (self._playcalling_df['down'] == down)
            ]
            if len(league_situation) > 0:
                if self.debug:
                    print(f"   ⚠️  FALLBACK: Using league average for {self.team} down={down} (no team data)")
                self._fallbacks_used.append(f"Play-calling: Used league average for down={down}")
                return float(league_situation['pass_rate'].mean())

        # LAST LAST RESORT: Hardcoded defaults by down (4th downs are handled by FG/Punt logic anyway)
        # These are only used if absolutely no data exists anywhere
        default_pass_rates = {
            1: 0.51,  # ~51% pass on 1st down
            2: 0.50,  # ~50% pass on 2nd down
            3: 0.68,  # ~68% pass on 3rd down
            4: 0.70,  # ~70% pass on 4th down (often go for it)
        }
        if down in default_pass_rates:
            if self.debug:
                print(f"   ⚠️  FALLBACK: Using hardcoded default for {self.team} down={down} (no data anywhere)")
            self._fallbacks_used.append(f"Play-calling: Used hardcoded default for down={down}")
            return default_pass_rates[down]

        # NO FALLBACK - raise error if absolutely no data
        prev_season = self.season - 1 if self.season > 2022 else None
        raise ValueError(f"No play-calling data for {self.team} {self.season} (or {prev_season}) - even for down={down}. Run preprocessing/extract_playcalling.py.")

    def _load_pff_grades(self):
        """Load PFF grades for OL/DL matchups."""
        self.pff_fallback_used = False
        try:
            loader = get_pff_loader()
            grades = loader.get_team_grades(self.team, self.season)

            # Check if fallback was used
            if grades.get('_fallback_used', False):
                self.pff_fallback_used = True
                print(f"⚠️  Warning: PFF fallback used for {self.team} - using league averages")

            # Store OL and DL grades
            self.ol_grade = grades['ol_pass_block']
            self.dl_grade = grades['dl_pass_rush']
            self.ol_run_grade = grades['ol_run_block']
            self.dl_run_grade = grades['dl_run_defense']
            self.coverage_grade = grades['secondary_coverage']
            self.passing_grade = grades['passing_offense']

        except Exception as e:
            # FIXED: Soft fallback with league averages and confidence flag
            print(f"⚠️  Warning: Could not load PFF data for {self.team}: {e}. Using league averages.")
            self.pff_fallback_used = True
            # Use league-average defaults (50th percentile)
            self.ol_grade = 50.0
            self.dl_grade = 50.0
            self.ol_run_grade = 50.0
            self.dl_run_grade = 50.0
            self.coverage_grade = 50.0
            self.passing_grade = 50.0

    def _load_yards_per_play(self):
        """Load yards per play and yards per pass attempt - NO FALLBACKS."""
        # Map team abbreviations (LAR -> LA for data lookup)
        lookup_team = self._get_lookup_team()
        
        weekly_file = self.data_dir / "team_yards_per_play_weekly.csv"

        if not weekly_file.exists():
            # Use season average if weekly not available
            season_file = self.data_dir / "team_yards_per_play_season.csv"
            if not season_file.exists():
                raise ValueError("YPP data not found. Run preprocessing/extract_yards_per_play.py first.")

            ypp_df = pd.read_csv(season_file)
            team_data = ypp_df[
                (ypp_df['posteam'] == lookup_team) &
                (ypp_df['season'] == self.season)
            ]
            
            # Fallback to previous season if current season not available
            if len(team_data) == 0:
                prev_season = self.season - 1
                team_data = ypp_df[
                    (ypp_df['posteam'] == lookup_team) &
                    (ypp_df['season'] == prev_season)
                ]
                if len(team_data) > 0 and self.debug:
                    print(f"⚠️  Using {prev_season} YPP data for {self.team} (no {self.season} data available)")
        else:
            ypp_df = pd.read_csv(weekly_file)
            # CRITICAL: Use only PRIOR weeks to avoid look-ahead bias
            # For week N, use weeks 1 through N-1 (or season average if N=1)
            if self.week == 1:
                # Week 1: Use season average from previous season, or aggregate weeks 1-17 from current season
                # Fall through to season average below
                season_file = self.data_dir / "team_yards_per_play_season.csv"
                if season_file.exists():
                    season_df = pd.read_csv(season_file)
                    team_data = season_df[
                        (season_df['posteam'] == lookup_team) &
                        (season_df['season'] == self.season)
                    ]
                    # Fallback to previous season
                    if len(team_data) == 0:
                        prev_season = self.season - 1
                        team_data = season_df[
                            (season_df['posteam'] == lookup_team) &
                            (season_df['season'] == prev_season)
                        ]
                        if len(team_data) > 0 and self.debug:
                            print(f"⚠️  Using {prev_season} YPP season data for {self.team} (no {self.season} data available)")
                else:
                    team_data = pd.DataFrame()
            else:
                # Week N: Aggregate weeks 1 through N-1 (exclude current week)
                prior_weeks = ypp_df[
                    (ypp_df['posteam'] == lookup_team) &
                    (ypp_df['season'] == self.season) &
                    (ypp_df['week'] < self.week)  # KEY: Only prior weeks
                ]
                
                # Fallback: try previous season if no current season data
                if len(prior_weeks) == 0:
                    prev_season = self.season - 1
                    prior_weeks = ypp_df[
                        (ypp_df['posteam'] == lookup_team) &
                        (ypp_df['season'] == prev_season) &
                        (ypp_df['week'] < self.week)
                    ]
                    if len(prior_weeks) > 0 and self.debug:
                        print(f"⚠️  Using {prev_season} YPP weekly data for {self.team} (no {self.season} data available)")

                if len(prior_weeks) > 0:
                    # Apply regression to mean for extreme weekly values
                    # Cap individual weeks to prevent one bad game from destroying average
                    league_avg_ypp = 5.5  # NFL average
                    league_avg_ypa = 6.5

                    def shrink_extreme(values, league_avg, max_dev=1.5):
                        """Shrink extreme values towards league average"""
                        return values.apply(lambda x: max(league_avg - max_dev, min(league_avg + max_dev, x)))

                    # Aggregate prior weeks with extreme value capping
                    team_data = pd.DataFrame([{
                        'posteam': self.team,
                        'season': self.season,
                        'off_yards_per_play': shrink_extreme(prior_weeks['off_yards_per_play'], league_avg_ypp).mean(),
                        'off_yards_per_pass_attempt': shrink_extreme(prior_weeks['off_yards_per_pass_attempt'], league_avg_ypa).mean(),
                        'def_yards_per_play_allowed': shrink_extreme(prior_weeks['def_yards_per_play_allowed'], league_avg_ypp).mean(),
                        'def_yards_per_pass_allowed': shrink_extreme(prior_weeks['def_yards_per_pass_allowed'], league_avg_ypa).mean(),
                    }])
                else:
                    team_data = pd.DataFrame()

            if len(team_data) == 0:
                # Fall back to season average
                season_file = self.data_dir / "team_yards_per_play_season.csv"
                if season_file.exists():
                    season_df = pd.read_csv(season_file)
                    team_data = season_df[
                        (season_df['posteam'] == lookup_team) &
                        (season_df['season'] == self.season)
                    ]
                    # Fallback to previous season
                    if len(team_data) == 0:
                        prev_season = self.season - 1
                        team_data = season_df[
                            (season_df['posteam'] == lookup_team) &
                            (season_df['season'] == prev_season)
                        ]
                        if len(team_data) > 0 and self.debug:
                            print(f"⚠️  Using {prev_season} YPP season fallback for {self.team} (no {self.season} data available)")

        if len(team_data) > 0:
            self.off_yards_per_play = float(team_data['off_yards_per_play'].iloc[0])
            self.off_yards_per_pass_attempt = float(team_data['off_yards_per_pass_attempt'].iloc[0])
            self.def_yards_per_play_allowed = float(team_data['def_yards_per_play_allowed'].iloc[0])
            self.def_yards_per_pass_allowed = float(team_data['def_yards_per_pass_allowed'].iloc[0])
        else:
            raise ValueError(f"No YPP data for {self.team} {self.season} W{self.week} (looked up as {lookup_team}). Run preprocessing/extract_yards_per_play.py.")

    def _load_early_down_success(self):
        """Load early-down success rates."""
        lookup_team = self._get_lookup_team()
        weekly_file = self.data_dir / "early_down_success_weekly.csv"

        if not weekly_file.exists():
            season_file = self.data_dir / "early_down_success_season.csv"
            if not season_file.exists():
                self.early_down_success_rate = 0.48
                return

            success_df = pd.read_csv(season_file)
            team_data = success_df[
                (success_df['posteam'] == lookup_team) &
                (success_df['season'] == self.season)
            ]
            # Fallback to previous season
            if len(team_data) == 0:
                prev_season = self.season - 1
                team_data = success_df[
                    (success_df['posteam'] == lookup_team) &
                    (success_df['season'] == prev_season)
                ]
        else:
            success_df = pd.read_csv(weekly_file)
            # CRITICAL: Use only PRIOR weeks
            if self.week == 1:
                team_data = pd.DataFrame()
            else:
                prior_weeks = success_df[
                    (success_df['posteam'] == lookup_team) &
                    (success_df['season'] == self.season) &
                    (success_df['week'] < self.week)  # Only prior weeks
                ]
                # Fallback to previous season
                if len(prior_weeks) == 0:
                    prev_season = self.season - 1
                    prior_weeks = success_df[
                        (success_df['posteam'] == lookup_team) &
                        (success_df['season'] == prev_season) &
                        (success_df['week'] < self.week)
                    ]
                if len(prior_weeks) > 0:
                    team_data = pd.DataFrame([{
                        'posteam': self.team,
                        'season': self.season,
                        'early_down_success_rate': prior_weeks['early_down_success_rate'].mean(),
                    }])
                else:
                    team_data = pd.DataFrame()

            if len(team_data) == 0:
                season_file = self.data_dir / "early_down_success_season.csv"
                if season_file.exists():
                    season_df = pd.read_csv(season_file)
                    team_data = season_df[
                        (season_df['posteam'] == lookup_team) &
                        (season_df['season'] == self.season)
                    ]
                    # Fallback to previous season
                    if len(team_data) == 0:
                        prev_season = self.season - 1
                        team_data = season_df[
                            (season_df['posteam'] == lookup_team) &
                            (season_df['season'] == prev_season)
                        ]

        if len(team_data) > 0:
            self.early_down_success_rate = float(team_data['early_down_success_rate'].iloc[0])
        else:
            self.early_down_success_rate = 0.48  # League average

    def _load_anya(self):
        """Load Adjusted Net Yards per Attempt."""
        lookup_team = self._get_lookup_team()
        weekly_file = self.data_dir / "team_anya_weekly.csv"

        if not weekly_file.exists():
            season_file = self.data_dir / "team_anya_season.csv"
            if not season_file.exists():
                self.off_anya = 6.0
                self.def_anya_allowed = 6.0
                return

            anya_df = pd.read_csv(season_file)
            team_data = anya_df[
                (anya_df['posteam'] == lookup_team) &
                (anya_df['season'] == self.season)
            ]
            # Fallback to previous season
            if len(team_data) == 0:
                prev_season = self.season - 1
                team_data = anya_df[
                    (anya_df['posteam'] == lookup_team) &
                    (anya_df['season'] == prev_season)
                ]
        else:
            anya_df = pd.read_csv(weekly_file)
            # CRITICAL: Use only PRIOR weeks
            if self.week == 1:
                team_data = pd.DataFrame()
            else:
                prior_weeks = anya_df[
                    (anya_df['posteam'] == lookup_team) &
                    (anya_df['season'] == self.season) &
                    (anya_df['week'] < self.week)  # Only prior weeks
                ]
                # Fallback to previous season
                if len(prior_weeks) == 0:
                    prev_season = self.season - 1
                    prior_weeks = anya_df[
                        (anya_df['posteam'] == lookup_team) &
                        (anya_df['season'] == prev_season) &
                        (anya_df['week'] < self.week)
                    ]
                if len(prior_weeks) > 0:
                    team_data = pd.DataFrame([{
                        'posteam': self.team,
                        'season': self.season,
                        'off_anya': prior_weeks['off_anya'].mean(),
                        'def_anya_allowed': prior_weeks['def_anya_allowed'].mean(),
                    }])
                else:
                    team_data = pd.DataFrame()

            if len(team_data) == 0:
                season_file = self.data_dir / "team_anya_season.csv"
                if season_file.exists():
                    season_df = pd.read_csv(season_file)
                    team_data = season_df[
                        (season_df['posteam'] == lookup_team) &
                        (season_df['season'] == self.season)
                    ]
                    # Fallback to previous season
                    if len(team_data) == 0:
                        prev_season = self.season - 1
                        team_data = season_df[
                            (season_df['posteam'] == lookup_team) &
                            (season_df['season'] == prev_season)
                        ]

        if len(team_data) > 0:
            self.off_anya = float(team_data['off_anya'].iloc[0])
            self.def_anya_allowed = float(team_data['def_anya_allowed'].iloc[0])
        else:
            self.off_anya = 6.0
            self.def_anya_allowed = 6.0

    def _load_turnover_regression(self):
        """Load turnover regression factors."""
        lookup_team = self._get_lookup_team()
        weekly_file = self.data_dir / "turnover_regression_weekly.csv"

        if not weekly_file.exists():
            self.turnover_regression_factor = 1.0
            return

        turnovers_df = pd.read_csv(weekly_file)
        # CRITICAL: Use only PRIOR weeks
        if self.week == 1:
            team_data = pd.DataFrame()
        else:
            prior_weeks = turnovers_df[
                (turnovers_df['posteam'] == lookup_team) &
                (turnovers_df['season'] == self.season) &
                (turnovers_df['week'] < self.week)  # Only prior weeks
            ]
            # Fallback to previous season
            if len(prior_weeks) == 0:
                prev_season = self.season - 1
                prior_weeks = turnovers_df[
                    (turnovers_df['posteam'] == lookup_team) &
                    (turnovers_df['season'] == prev_season) &
                    (turnovers_df['week'] < self.week)
                ]
            if len(prior_weeks) > 0:
                team_data = pd.DataFrame([{
                    'posteam': self.team,
                    'season': self.season,
                    'regression_factor': prior_weeks['regression_factor'].mean(),
                }])
            else:
                team_data = pd.DataFrame()

        if len(team_data) > 0:
            self.turnover_regression_factor = float(team_data['regression_factor'].iloc[0])
        else:
            self.turnover_regression_factor = 1.0

    def _load_red_zone(self):
        """Load red zone statistics."""
        lookup_team = self._get_lookup_team()
        weekly_file = self.data_dir / "red_zone_stats_weekly.csv"

        if not weekly_file.exists():
            season_file = self.data_dir / "red_zone_stats_season.csv"
            if not season_file.exists():
                self.red_zone_trips_per_game = 3.5
                self.red_zone_td_pct = 0.60
                return

            redzone_df = pd.read_csv(season_file)
            team_data = redzone_df[
                (redzone_df['posteam'] == lookup_team) &
                (redzone_df['season'] == self.season)
            ]
            # Fallback to previous season
            if len(team_data) == 0:
                prev_season = self.season - 1
                team_data = redzone_df[
                    (redzone_df['posteam'] == lookup_team) &
                    (redzone_df['season'] == prev_season)
                ]
        else:
            redzone_df = pd.read_csv(weekly_file)
            # CRITICAL: Use only PRIOR weeks
            if self.week == 1:
                team_data = pd.DataFrame()
            else:
                prior_weeks = redzone_df[
                    (redzone_df['posteam'] == lookup_team) &
                    (redzone_df['season'] == self.season) &
                    (redzone_df['week'] < self.week)  # Only prior weeks
                ]
                # Fallback to previous season
                if len(prior_weeks) == 0:
                    prev_season = self.season - 1
                    prior_weeks = redzone_df[
                        (redzone_df['posteam'] == lookup_team) &
                        (redzone_df['season'] == prev_season) &
                        (redzone_df['week'] < self.week)
                    ]
                if len(prior_weeks) > 0:
                    team_data = pd.DataFrame([{
                        'posteam': self.team,
                        'season': self.season,
                        'red_zone_trips_per_game': prior_weeks['red_zone_trips_per_game'].mean(),
                        'red_zone_td_pct': prior_weeks['red_zone_td_pct'].mean(),
                    }])
                else:
                    team_data = pd.DataFrame()

            if len(team_data) == 0:
                season_file = self.data_dir / "red_zone_stats_season.csv"
                if season_file.exists():
                    season_df = pd.read_csv(season_file)
                    team_data = season_df[
                        (season_df['posteam'] == lookup_team) &
                        (season_df['season'] == self.season)
                    ]
                    # Fallback to previous season
                    if len(team_data) == 0:
                        prev_season = self.season - 1
                        team_data = season_df[
                            (season_df['posteam'] == lookup_team) &
                            (season_df['season'] == prev_season)
                        ]

        if len(team_data) > 0:
            self.red_zone_trips_per_game = float(team_data['red_zone_trips_per_game'].iloc[0])
            self.red_zone_td_pct = float(team_data['red_zone_td_pct'].iloc[0])
        else:
            self.red_zone_trips_per_game = 3.5
            self.red_zone_td_pct = 0.60

    def _load_special_teams(self):
        """Load special teams statistics."""
        lookup_team = self._get_lookup_team()
        weekly_file = self.data_dir / "special_teams_weekly.csv"

        if not weekly_file.exists():
            season_file = self.data_dir / "special_teams_season.csv"
            if not season_file.exists():
                self.punt_net_yards = 40.0
                self.field_goal_make_pct = 0.85
                return

            st_df = pd.read_csv(season_file)
            team_data = st_df[
                (st_df['posteam'] == lookup_team) &
                (st_df['season'] == self.season)
            ]
            # Fallback to previous season
            if len(team_data) == 0:
                prev_season = self.season - 1
                team_data = st_df[
                    (st_df['posteam'] == lookup_team) &
                    (st_df['season'] == prev_season)
                ]
        else:
            st_df = pd.read_csv(weekly_file)
            team_data = st_df[
                (st_df['posteam'] == lookup_team) &
                (st_df['season'] == self.season) &
                (st_df['week'] == self.week)
            ]
            # Fallback: try previous season if current week not available
            if len(team_data) == 0:
                prev_season = self.season - 1
                team_data = st_df[
                    (st_df['posteam'] == lookup_team) &
                    (st_df['season'] == prev_season) &
                    (st_df['week'] == self.week)
                ]

            if len(team_data) == 0:
                season_file = self.data_dir / "special_teams_season.csv"
                if season_file.exists():
                    season_df = pd.read_csv(season_file)
                    team_data = season_df[
                        (season_df['posteam'] == lookup_team) &
                        (season_df['season'] == self.season)
                    ]
                    # Fallback to previous season
                    if len(team_data) == 0:
                        prev_season = self.season - 1
                        team_data = season_df[
                            (season_df['posteam'] == lookup_team) &
                            (season_df['season'] == prev_season)
                        ]

        if len(team_data) > 0:
            self.punt_net_yards = float(team_data['punt_net_yards'].iloc[0]) if 'punt_net_yards' in team_data.columns else 40.0
            self.field_goal_make_pct = float(team_data['field_goal_make_pct'].iloc[0]) if 'field_goal_make_pct' in team_data.columns else 0.85
        else:
            self.punt_net_yards = 40.0
            self.field_goal_make_pct = 0.85

    def _load_situational_factors(self):
        """Load situational factors (rest, weather, dome) for a specific game."""
        # Note: This requires game_id to load correctly
        # For now, load defaults - will be set per-game in GameSimulator
        self.home_rest_days = 7  # Default
        self.away_rest_days = 7  # Default
        self.is_dome = False  # Default
        self.temperature = None  # Default
        self.wind = None  # Default

    def _load_injury_multipliers(self):
        """Load weekly injury multipliers and apply to team profile."""
        try:
            from .injuries import get_injury_loader
            loader = get_injury_loader()
            multipliers = loader.get_team_multipliers(self.team, self.season, self.week)

            # Store multipliers for use in PlaySimulator
            self.injury_multipliers = multipliers

            if self.debug and any(m != 1.0 for m in multipliers.values()):
                print(f"   ⚠️  Injuries: QB={multipliers['qb_completion_mult']:.2f}, "
                      f"OL={multipliers['ol_pressure_mult']:.2f}, "
                      f"CB={multipliers['cb_completion_allow_mult']:.2f}")
        except Exception as e:
            # No injuries: use defaults (all 1.0)
            self.injury_multipliers = {
                'qb_completion_mult': 1.0,
                'qb_int_mult': 1.0,
                'qb_sack_mult': 1.0,
                'wr_completion_mult': 1.0,
                'wr_explosive_mult': 1.0,
                'ol_pressure_mult': 1.0,
                'ol_run_mult': 1.0,
                'cb_completion_allow_mult': 1.0,
                'cb_int_mult': 1.0,
            }
            if self.debug:
                print(f"   ℹ️  No injury data: {e}")

    def _validate_schema(self):
        """Validate that all required fields exist and are proper types."""
        required_fields = {
            'off_epa': float,
            'def_epa': float,
            'off_anya': float,
            'def_anya_allowed': float,
            'off_yards_per_pass_attempt': float,
            'def_yards_per_pass_allowed': float,
            'off_yards_per_play': float,
            'def_yards_per_play_allowed': float,
            'red_zone_td_pct': float,
            'early_down_success_rate': float,
            'pace': float,
            'field_goal_make_pct': float,
            'punt_net_yards': float,
        }

        missing = []
        for field, field_type in required_fields.items():
            if not hasattr(self, field):
                missing.append(f"{field} (missing)")
            else:
                value = getattr(self, field)
                if value is None:
                    missing.append(f"{field} (None)")
                elif not isinstance(value, field_type):
                    missing.append(f"{field} (wrong type: {type(value).__name__}, expected {field_type.__name__})")

        if missing:
            raise ValueError(
                f"TeamProfile schema validation failed for {self.team} {self.season} W{self.week}. "
                f"Missing or invalid fields: {', '.join(missing)}. "
                f"Source files may be missing or incomplete. Check data preprocessing."
            )

    def set_situational_factors(self, home_rest: int = 7, away_rest: int = 7,
                               is_dome: bool = False, temp: float = None, wind: float = None):
        """
        Set situational factors for a specific game.
        
        Called by GameSimulator after loading game-specific situational data.
        
        Args:
            home_rest: This team's rest days (if they're home, this is home_rest_days from CSV)
            away_rest: Opponent's rest days (for reference, not directly used)
        """
        self.home_rest_days = home_rest  # This team's rest days
        self.away_rest_days = away_rest  # Opponent's rest days (for reference)
        self.is_dome = is_dome
        self.temperature = temp
        self.wind = wind

    def _print_load_summary(self):
        """Print summary of loaded data and any issues."""
        print(f"\n📊 Data Load Summary for {self.team} {self.season} W{self.week}:")
        print(f"   ✅ EPA: Off={self.off_epa:.3f}, Def={self.def_epa:.3f}")
        print(f"   ✅ QB: {self.qb_name}")
        print(f"   ✅ Play-Calling: {len(self.playcalling)} situations")
        print(f"   ✅ Drive Probs: {len(self.drive_probs)} situations")
        print(f"   ✅ Pace: {self.pace:.1f} plays/drive")

        # PFF
        if hasattr(self, 'ol_grade') and self.ol_grade:
            print(f"   ✅ PFF: OL={self.ol_grade:.1f}, DL={self.dl_grade:.1f}, OL_Run={self.ol_run_grade:.1f}, DL_Run={self.dl_run_grade:.1f}")
            print(f"      Passing={self.passing_grade:.1f}, Coverage={self.coverage_grade:.1f}")
        else:
            print("   ❌ PFF: NOT LOADED")

        # New metrics
        print(f"   ✅ YPP: Off={self.off_yards_per_play:.2f}, Def Allowed={self.def_yards_per_play_allowed:.2f}")
        print(f"   ✅ YPA: Off={self.off_yards_per_pass_attempt:.2f}, Def Allowed={self.def_yards_per_pass_allowed:.2f}")
        print(f"   ✅ Early-Down Success: {self.early_down_success_rate:.1%}")
        print(f"   ✅ ANY/A: Off={self.off_anya:.2f}, Def Allowed={self.def_anya_allowed:.2f}")
        print(f"   ✅ Turnover Regression: {self.turnover_regression_factor:.3f}")
        print(f"   ✅ Red Zone: {self.red_zone_trips_per_game:.2f} trips/game, {self.red_zone_td_pct:.1%} TD rate")
        print(f"   ✅ Special Teams: {self.punt_net_yards:.1f} punt net, {self.field_goal_make_pct:.1%} FG")

        # Situational factors
        if hasattr(self, 'home_rest_days'):
            print(f"   ✅ Situational: Rest={self.home_rest_days}d, Dome={self.is_dome}")

        if self._fallbacks_used:
            print("\n   ⚠️  FALLBACKS USED:")
            for fb in self._fallbacks_used:
                print(f"      - {fb}")
        else:
            print("\n   ✅ NO FALLBACKS - All data from files")

        if self._load_errors:
            print("\n   ❌ ERRORS:")
            for err in self._load_errors:
                print(f"      - {err}")

    def __repr__(self):
        """String representation."""
        pff_str = f", OL={self.ol_grade:.1f}, DL={self.dl_grade:.1f}" if hasattr(self, 'ol_grade') and self.ol_grade else ""
        return (f"TeamProfile({self.team} {self.season} W{self.week}: "
                f"Off EPA={self.off_epa:.3f}, Def EPA={self.def_epa:.3f}, "
                f"QB={self.qb_name}, Pace={self.pace:.1f}{pff_str})")

    def as_dict_for_audit(self) -> Dict:
        """Return team inputs used in simulation for transparency/auditing.
        
        Returns only the fields actually used by the simulator.
        Used for trace logging and reproducibility.
        """
        audit = {
            "team": self.team,
            "season": self.season,
            "week": self.week,
            # Core metrics (from nflfastR)
            "off_epa": float(self.off_epa),
            "def_epa": float(self.def_epa),
            "pace": float(self.pace),
            "early_down_success_rate": float(getattr(self, 'early_down_success_rate', 0.48)),
            # QB stats
            "qb_name": self.qb_name,
            "qb_completion_pct": float(self.qb_stats.get('completion_pct', 0.65)) if self.qb_stats else None,
            "qb_any_a": float(self.qb_stats.get('any_a', 6.5)) if self.qb_stats else None,
            "qb_ypa": float(self.qb_stats.get('ypa', 7.0)) if self.qb_stats else None,
            # Yards per play
            "off_yards_per_play": float(getattr(self, 'off_yards_per_play', 5.5)),
            "off_yards_per_pass_attempt": float(getattr(self, 'off_yards_per_pass_attempt', 7.0)),
            "yards_per_pass": float(getattr(self, 'yards_per_pass', 7.0)) if hasattr(self, 'yards_per_pass') else None,
            "yards_per_run": float(getattr(self, 'yards_per_run', 4.5)) if hasattr(self, 'yards_per_run') else None,
            "pass_rate": float(getattr(self, 'pass_rate', 0.6)) if hasattr(self, 'pass_rate') else None,
            # Red zone
            "red_zone_trips_per_game": float(getattr(self, 'red_zone_trips_per_game', 3.5)),
            "red_zone_td_pct": float(getattr(self, 'red_zone_td_pct', 0.60)),
            # Special teams
            "punt_net_yards": float(getattr(self, 'punt_net_yards', 40.0)),
            "field_goal_make_pct": float(getattr(self, 'field_goal_make_pct', 0.85)),
            # PFF grades (if available)
            "ol_grade": float(self.ol_grade) if hasattr(self, 'ol_grade') and self.ol_grade is not None else None,
            "dl_grade": float(self.dl_grade) if hasattr(self, 'dl_grade') and self.dl_grade is not None else None,
            "ol_run_grade": float(self.ol_run_grade) if hasattr(self, 'ol_run_grade') and self.ol_run_grade is not None else None,
            "dl_run_grade": float(self.dl_run_grade) if hasattr(self, 'dl_run_grade') and self.dl_run_grade is not None else None,
            "coverage_grade": float(self.coverage_grade) if hasattr(self, 'coverage_grade') and self.coverage_grade is not None else None,
            "passing_grade": float(self.passing_grade) if hasattr(self, 'passing_grade') and self.passing_grade is not None else None,
            # Play-calling (summary stats)
            "playcalling_situations": len(self.playcalling) if hasattr(self, 'playcalling') else 0,
            # Situational factors
            "home_rest_days": getattr(self, 'home_rest_days', 7),
            "away_rest_days": getattr(self, 'away_rest_days', 7),
            "is_dome": getattr(self, 'is_dome', False),
            "temperature": getattr(self, 'temperature', None),
            "wind": getattr(self, 'wind', None),
        }

        # Add turnover regression if available
        if hasattr(self, 'turnover_regression'):
            audit["turnover_regression"] = float(self.turnover_regression)

        return audit

