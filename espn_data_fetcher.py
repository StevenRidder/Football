"""
Comprehensive ESPN API data fetcher for detailed game and team information
"""
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from math import radians, cos, sin, asin, sqrt


class ESPNDataFetcher:
    """Fetch comprehensive data from ESPN API"""
    
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    STATS_URL = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
    
    # Team abbreviation mapping
    TEAM_MAP = {
        'ARI': '22', 'ATL': '1', 'BAL': '33', 'BUF': '2', 'CAR': '29',
        'CHI': '3', 'CIN': '4', 'CLE': '5', 'DAL': '6', 'DEN': '7',
        'DET': '8', 'GB': '9', 'HOU': '34', 'IND': '11', 'JAX': '30',
        'KC': '12', 'LV': '13', 'LAC': '24', 'LA': '14', 'MIA': '15',
        'MIN': '16', 'NE': '17', 'NO': '18', 'NYG': '19', 'NYJ': '20',
        'PHI': '21', 'PIT': '23', 'SF': '25', 'SEA': '26', 'TB': '27',
        'TEN': '10', 'WAS': '28'
    }
    
    @classmethod
    def get_team_id(cls, abbr: str) -> Optional[str]:
        """Get ESPN team ID from abbreviation"""
        return cls.TEAM_MAP.get(abbr.upper())
    
    @classmethod
    def fetch_team_season_stats(cls, team_abbr: str, season: int = 2025) -> Dict:
        """Fetch comprehensive team season statistics"""
        team_id = cls.get_team_id(team_abbr)
        if not team_id:
            return {}
        
        try:
            # Get team info
            url = f"{cls.BASE_URL}/teams/{team_id}"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            team = data.get('team', {})
            
            # Extract record
            record_items = team.get('record', {}).get('items', [])
            overall_record = next((r for r in record_items if r.get('type') == 'total'), {})
            home_record = next((r for r in record_items if r.get('type') == 'home'), {})
            away_record = next((r for r in record_items if r.get('type') == 'road'), {})
            
            # Get next event
            next_event = team.get('nextEvent', [{}])[0] if team.get('nextEvent') else {}
            
            return {
                'abbreviation': team.get('abbreviation', team_abbr),
                'display_name': team.get('displayName', ''),
                'color': team.get('color', ''),
                'logo': team.get('logos', [{}])[0].get('href', '') if team.get('logos') else '',
                'record': {
                    'overall': overall_record.get('summary', '0-0'),
                    'home': home_record.get('summary', '0-0'),
                    'away': away_record.get('summary', '0-0'),
                    'wins': overall_record.get('stats', [{}])[0].get('value', 0) if overall_record.get('stats') else 0,
                    'losses': overall_record.get('stats', [{}])[1].get('value', 0) if overall_record.get('stats') and len(overall_record.get('stats', [])) > 1 else 0,
                },
                'next_event': {
                    'name': next_event.get('name', ''),
                    'date': next_event.get('date', ''),
                } if next_event else {}
            }
        except Exception as e:
            print(f"Error fetching team stats for {team_abbr}: {e}")
            return {}
    
    @classmethod
    def fetch_team_detailed_stats(cls, team_abbr: str, season: int = 2025) -> Dict:
        """Fetch detailed offensive/defensive statistics"""
        team_id = cls.get_team_id(team_abbr)
        if not team_id:
            return {}
        
        try:
            url = f"{cls.STATS_URL}/seasons/{season}/types/2/teams/{team_id}/statistics"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            stats_dict = {}
            
            # Parse statistics
            for category in data.get('splits', {}).get('categories', []):
                cat_name = category.get('name', '')
                for stat in category.get('stats', []):
                    stat_name = stat.get('name', '')
                    stat_value = stat.get('value', 0)
                    stat_display = stat.get('displayValue', '0')
                    stats_dict[f"{cat_name}_{stat_name}"] = {
                        'value': stat_value,
                        'display': stat_display
                    }
            
            return stats_dict
        except Exception as e:
            print(f"Error fetching detailed stats for {team_abbr}: {e}")
            return {}
    
    @classmethod
    def fetch_game_summary(cls, game_id: str) -> Dict:
        """Fetch comprehensive game summary including odds, injuries, weather"""
        try:
            url = f"{cls.BASE_URL}/summary?event={game_id}"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            
            # Extract odds
            odds = {}
            if data.get('pickcenter'):
                for provider in data['pickcenter']:
                    if provider.get('provider', {}).get('name') == 'consensus':
                        odds = {
                            'spread': provider.get('spread', {}).get('displayValue', 'N/A'),
                            'over_under': provider.get('overUnder', {}).get('displayValue', 'N/A'),
                            'home_moneyline': provider.get('homeTeamOdds', {}).get('moneyLine', 'N/A'),
                            'away_moneyline': provider.get('awayTeamOdds', {}).get('moneyLine', 'N/A'),
                        }
                        break
            
            # Extract injuries
            injuries = {'away': [], 'home': []}
            if data.get('injuries'):
                for injury_list in data['injuries']:
                    team_id = injury_list.get('team', {}).get('id')
                    team_injuries = []
                    for injury in injury_list.get('injuries', []):
                        team_injuries.append({
                            'player': injury.get('longComment', ''),
                            'status': injury.get('status', ''),
                            'details': injury.get('details', {}).get('detail', '')
                        })
                    
                    # Determine if home or away based on team_id
                    # This would need to be matched with competition data
                    injuries['away' if len(injuries['away']) == 0 else 'home'] = team_injuries
            
            # Extract weather
            weather = {}
            game_info = data.get('gameInfo', {})
            if game_info.get('weather'):
                w = game_info['weather']
                # Map condition IDs to descriptions
                condition_map = {
                    '1': 'Clear', '2': 'Mostly Clear', '3': 'Partly Cloudy',
                    '4': 'Intermittent Clouds', '5': 'Hazy Sunshine', '6': 'Mostly Cloudy',
                    '7': 'Cloudy', '8': 'Overcast', '11': 'Fog', '12': 'Showers',
                    '13': 'Mostly Cloudy w/ Showers', '14': 'Partly Sunny w/ Showers',
                    '15': 'T-Storms', '16': 'Mostly Cloudy w/ T-Storms',
                    '17': 'Partly Sunny w/ T-Storms', '18': 'Rain', '19': 'Flurries',
                    '20': 'Mostly Cloudy w/ Flurries', '21': 'Partly Sunny w/ Flurries',
                    '22': 'Snow', '23': 'Mostly Cloudy w/ Snow', '24': 'Ice',
                    '25': 'Sleet', '26': 'Freezing Rain', '29': 'Rain and Snow',
                    '30': 'Hot', '31': 'Cold', '32': 'Windy', '33': 'Clear (Night)',
                    '34': 'Mostly Clear (Night)', '35': 'Partly Cloudy (Night)',
                    '36': 'Intermittent Clouds (Night)', '37': 'Hazy Moonlight',
                    '38': 'Mostly Cloudy (Night)', '39': 'Partly Cloudy w/ Showers (Night)',
                    '40': 'Mostly Cloudy w/ Showers (Night)', '41': 'Partly Cloudy w/ T-Storms (Night)',
                    '42': 'Mostly Cloudy w/ T-Storms (Night)', '43': 'Mostly Cloudy w/ Flurries (Night)',
                    '44': 'Mostly Cloudy w/ Snow (Night)'
                }
                
                condition_id = str(w.get('conditionId', '7'))
                condition_desc = condition_map.get(condition_id, 'Cloudy')
                
                weather = {
                    'temperature': w.get('temperature', 0),
                    'condition': condition_desc,
                    'condition_id': condition_id,
                    'gust': w.get('gust', 0),
                    'precipitation': w.get('precipitation', 0),
                    'display': f"{w.get('temperature', 0)}°F, {condition_desc}"
                }
            
            # Extract venue
            venue = {}
            if game_info.get('venue'):
                venue = {
                    'name': game_info['venue'].get('fullName', 'N/A'),
                    'city': game_info['venue'].get('address', {}).get('city', 'N/A'),
                    'state': game_info['venue'].get('address', {}).get('state', 'N/A'),
                    'indoor': game_info['venue'].get('indoor', False)
                }
            
            return {
                'odds': odds,
                'injuries': injuries,
                'weather': weather,
                'venue': venue,
                'attendance': game_info.get('attendance', 0)
            }
        except Exception as e:
            print(f"Error fetching game summary for {game_id}: {e}")
            return {}
    
    @classmethod
    def fetch_team_leaders(cls, team_abbr: str) -> Dict:
        """Fetch team statistical leaders from scoreboard"""
        try:
            url = f"{cls.BASE_URL}/scoreboard"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            
            # Find the team in current games
            for event in data.get('events', []):
                for comp in event.get('competitions', []):
                    for team in comp.get('competitors', []):
                        if team.get('team', {}).get('abbreviation') == team_abbr:
                            leaders = {}
                            for leader in team.get('leaders', []):
                                leader_type = leader.get('name', '')
                                leader_data = leader.get('leaders', [{}])[0] if leader.get('leaders') else {}
                                leaders[leader_type] = {
                                    'player': leader_data.get('athlete', {}).get('displayName', 'N/A'),
                                    'value': leader_data.get('displayValue', 'N/A')
                                }
                            return leaders
            
            return {}
        except Exception as e:
            print(f"Error fetching team leaders for {team_abbr}: {e}")
            return {}
    
    @classmethod
    def calculate_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles using Haversine formula"""
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in miles
        r = 3956
        
        return c * r
    
    @classmethod
    def get_city_coordinates(cls, city: str, state: str) -> Tuple[float, float]:
        """Get approximate coordinates for NFL cities"""
        # NFL city coordinates (approximate)
        coords = {
            ('Kansas City', 'MO'): (39.0997, -94.5786),
            ('Landover', 'MD'): (38.9076, -76.8645),  # Washington
            ('Glendale', 'AZ'): (33.5276, -112.2626),  # Arizona
            ('Atlanta', 'GA'): (33.7490, -84.3880),
            ('Baltimore', 'MD'): (39.2904, -76.6122),
            ('Orchard Park', 'NY'): (42.7737, -78.7869),  # Buffalo
            ('Charlotte', 'NC'): (35.2271, -80.8431),
            ('Chicago', 'IL'): (41.8781, -87.6298),
            ('Cincinnati', 'OH'): (39.1031, -84.5120),
            ('Cleveland', 'OH'): (41.4993, -81.6944),
            ('Arlington', 'TX'): (32.7473, -97.0945),  # Dallas
            ('Denver', 'CO'): (39.7392, -104.9903),
            ('Detroit', 'MI'): (42.3314, -83.0458),
            ('Green Bay', 'WI'): (44.5133, -88.0133),
            ('Houston', 'TX'): (29.7604, -95.3698),
            ('Indianapolis', 'IN'): (39.7684, -86.1581),
            ('Jacksonville', 'FL'): (30.3322, -81.6557),
            ('Paradise', 'NV'): (36.1699, -115.1398),  # Las Vegas
            ('Inglewood', 'CA'): (33.9534, -118.3390),  # LA Rams/Chargers
            ('Miami Gardens', 'FL'): (25.9580, -80.2389),  # Miami
            ('Minneapolis', 'MN'): (44.9778, -93.2650),
            ('Foxborough', 'MA'): (42.0909, -71.2643),  # New England
            ('New Orleans', 'LA'): (29.9511, -90.0715),
            ('East Rutherford', 'NJ'): (40.8128, -74.0742),  # NY Giants/Jets
            ('Philadelphia', 'PA'): (39.9526, -75.1652),
            ('Pittsburgh', 'PA'): (40.4406, -80.0158),
            ('Santa Clara', 'CA'): (37.3541, -121.9693),  # San Francisco
            ('Seattle', 'WA'): (47.6062, -122.3321),
            ('Tampa', 'FL'): (27.9506, -82.4572),
            ('Nashville', 'TN'): (36.1627, -86.7816),  # Tennessee
        }
        
        return coords.get((city, state), (0, 0))
    
    @classmethod
    def fetch_team_schedule(cls, team_abbr: str, season: int = 2025) -> List[Dict]:
        """Fetch team's schedule to calculate rest days"""
        team_id = cls.get_team_id(team_abbr)
        if not team_id:
            return []
        
        try:
            url = f"{cls.BASE_URL}/teams/{team_id}/schedule"
            params = {'season': season}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return []
            
            data = response.json()
            games = []
            
            # Helper to normalize team abbreviations (ESPN uses WSH, we use WAS)
            def normalize_abbr(abbr):
                return 'WAS' if abbr == 'WSH' else abbr
            
            team_abbr_normalized = normalize_abbr(team_abbr)
            
            for event in data.get('events', []):
                competition = event.get('competitions', [{}])[0]
                game_date = event.get('date', '')
                
                # Get opponent
                for competitor in competition.get('competitors', []):
                    comp_abbr = competitor.get('team', {}).get('abbreviation', '')
                    comp_abbr = normalize_abbr(comp_abbr)
                    if comp_abbr != team_abbr_normalized:
                        opponent = comp_abbr
                        break
                else:
                    opponent = 'Unknown'
                
                # Get venue
                venue = competition.get('venue', {})
                
                # Get result for completed games
                status = competition.get('status', {}).get('type', {}).get('name', '')
                result = None
                if status == 'STATUS_FINAL':
                    for competitor in competition.get('competitors', []):
                        comp_abbr = competitor.get('team', {}).get('abbreviation', '')
                        comp_abbr = normalize_abbr(comp_abbr)
                        score_val = competitor.get('score', 0)
                        if isinstance(score_val, dict):
                            score = int(score_val.get('value', 0))
                        else:
                            score = int(score_val) if score_val else 0
                        
                        if comp_abbr == team_abbr_normalized:
                            team_score = score
                        else:
                            opp_score = score
                    
                    result = 'W' if team_score > opp_score else ('L' if team_score < opp_score else 'T')
                
                games.append({
                    'date': game_date,
                    'opponent': opponent,
                    'venue': venue.get('fullName', ''),
                    'city': venue.get('address', {}).get('city', ''),
                    'state': venue.get('address', {}).get('state', ''),
                    'result': result
                })
            
            return games
        except Exception as e:
            print(f"Error fetching schedule for {team_abbr}: {e}")
            return []
    
    @classmethod
    def calculate_rest_days(cls, team_schedule: List[Dict], current_game_date: str) -> int:
        """Calculate days of rest before current game"""
        if not team_schedule or not current_game_date:
            return 7  # Default to 7 days
        
        try:
            current_dt = datetime.fromisoformat(current_game_date.replace('Z', '+00:00'))
            
            # Find previous game
            prev_game = None
            for game in sorted(team_schedule, key=lambda x: x['date']):
                game_dt = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
                if game_dt < current_dt:
                    prev_game = game
                elif game_dt >= current_dt:
                    break
            
            if prev_game:
                prev_dt = datetime.fromisoformat(prev_game['date'].replace('Z', '+00:00'))
                rest_days = (current_dt - prev_dt).days
                return rest_days
            
            return 7  # Default
        except Exception as e:
            print(f"Error calculating rest days: {e}")
            return 7
    
    @classmethod
    def fetch_last_five_games(cls, team_abbr: str, season: int = 2025) -> List[Dict]:
        """Fetch last 5 games for recent form analysis"""
        # Use fetch_team_historical_games which has the WSH/WAS fix and gets scores
        all_games = cls.fetch_team_historical_games(team_abbr, season)
        
        # Return last 5
        return all_games[-5:] if len(all_games) >= 5 else all_games
    
    @classmethod
    def fetch_team_historical_games(cls, team_abbr: str, season: int = 2025) -> List[Dict]:
        """Fetch all completed games for a team with scores and venue details"""
        team_id = cls.get_team_id(team_abbr)
        if not team_id:
            return []
        
        try:
            # Fetch team schedule
            url = f"{cls.BASE_URL}/teams/{team_id}/schedule"
            params = {'season': season}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return []
            
            data = response.json()
            games = []
            
            # Helper to normalize team abbreviations (ESPN uses WSH, we use WAS)
            def normalize_abbr(abbr):
                return 'WAS' if abbr == 'WSH' else abbr
            
            # Normalize the input team abbreviation for comparison
            team_abbr_normalized = normalize_abbr(team_abbr)
            
            for event in data.get('events', []):
                competition = event.get('competitions', [{}])[0]
                status = competition.get('status', {}).get('type', {}).get('name', '')
                
                # Only include completed games
                if status != 'STATUS_FINAL':
                    continue
                
                # Get week number
                week = event.get('week', {}).get('number', 0)
                
                # Get teams and scores
                home_team = None
                away_team = None
                home_score = 0
                away_score = 0
                is_home = False
                
                for competitor in competition.get('competitors', []):
                    team_abbr_comp = competitor.get('team', {}).get('abbreviation', '')
                    # Normalize ESPN abbreviation
                    team_abbr_comp = normalize_abbr(team_abbr_comp)
                    
                    # Score might be a string, int, or dict - handle all cases
                    score_val = competitor.get('score', 0)
                    if isinstance(score_val, dict):
                        score = int(score_val.get('value', 0))
                    else:
                        score = int(score_val) if score_val else 0
                    
                    if competitor.get('homeAway') == 'home':
                        home_team = team_abbr_comp
                        home_score = score
                        if team_abbr_comp == team_abbr_normalized:
                            is_home = True
                    else:
                        away_team = team_abbr_comp
                        away_score = score
                
                # Get venue details
                venue = competition.get('venue', {})
                is_indoor = venue.get('indoor', False)
                is_grass = venue.get('grass', True)
                
                # Determine team's score and opponent's score
                if is_home:
                    team_score = home_score
                    opp_score = away_score
                    opponent = away_team
                else:
                    team_score = away_score
                    opp_score = home_score
                    opponent = home_team
                
                # Calculate result
                if team_score > opp_score:
                    result = 'W'
                elif team_score < opp_score:
                    result = 'L'
                else:
                    result = 'T'
                
                games.append({
                    'week': week,
                    'opponent': opponent,
                    'is_home': is_home,
                    'team_score': team_score,
                    'opp_score': opp_score,
                    'result': result,
                    'is_indoor': is_indoor,
                    'is_grass': is_grass,
                    'venue_name': venue.get('fullName', ''),
                    'date': event.get('date', '')
                })
            
            return games
        except Exception as e:
            print(f"Error fetching historical games for {team_abbr}: {e}")
            return []
    
    @classmethod
    def calculate_performance_splits(cls, team_abbr: str, season: int = 2025) -> Dict:
        """Calculate performance splits: home/away, grass/turf, indoor/outdoor"""
        games = cls.fetch_team_historical_games(team_abbr, season)
        
        if not games:
            return {
                'home': {'games': 0, 'ppg': 0, 'papg': 0, 'record': '0-0', 'diff': 0},
                'away': {'games': 0, 'ppg': 0, 'papg': 0, 'record': '0-0', 'diff': 0},
                'grass': {'games': 0, 'ppg': 0, 'papg': 0, 'record': '0-0', 'diff': 0},
                'turf': {'games': 0, 'ppg': 0, 'papg': 0, 'record': '0-0', 'diff': 0},
                'indoor': {'games': 0, 'ppg': 0, 'papg': 0, 'record': '0-0', 'diff': 0},
                'outdoor': {'games': 0, 'ppg': 0, 'papg': 0, 'record': '0-0', 'diff': 0},
                'overall': {'games': 0, 'ppg': 0, 'papg': 0}
            }
        
        # Calculate overall stats
        total_games = len(games)
        total_pf = sum(g['team_score'] for g in games)
        total_pa = sum(g['opp_score'] for g in games)
        overall_ppg = total_pf / total_games if total_games > 0 else 0
        overall_papg = total_pa / total_games if total_games > 0 else 0
        
        # Helper function to calculate split stats
        def calc_split(filtered_games):
            if not filtered_games:
                return {'games': 0, 'ppg': 0, 'papg': 0, 'record': '0-0', 'wins': 0, 'losses': 0, 'diff': 0}
            
            games_count = len(filtered_games)
            pf = sum(g['team_score'] for g in filtered_games)
            pa = sum(g['opp_score'] for g in filtered_games)
            wins = sum(1 for g in filtered_games if g['team_score'] > g['opp_score'])
            losses = games_count - wins
            
            ppg = pf / games_count
            papg = pa / games_count
            ppg_diff = ppg - overall_ppg
            
            return {
                'games': games_count,
                'ppg': round(ppg, 1),
                'papg': round(papg, 1),
                'record': f"{wins}-{losses}",
                'wins': wins,
                'losses': losses,
                'diff': round(ppg_diff, 1)
            }
        
        # Calculate splits
        home_games = [g for g in games if g['is_home']]
        away_games = [g for g in games if not g['is_home']]
        grass_games = [g for g in games if g['is_grass']]
        turf_games = [g for g in games if not g['is_grass']]
        indoor_games = [g for g in games if g['is_indoor']]
        outdoor_games = [g for g in games if not g['is_indoor']]
        
        return {
            'home': calc_split(home_games),
            'away': calc_split(away_games),
            'grass': calc_split(grass_games),
            'turf': calc_split(turf_games),
            'indoor': calc_split(indoor_games),
            'outdoor': calc_split(outdoor_games),
            'overall': {
                'games': total_games,
                'ppg': round(overall_ppg, 1),
                'papg': round(overall_papg, 1)
            }
        }
    
    @classmethod
    def fetch_comprehensive_game_data(cls, away_abbr: str, home_abbr: str, game_id: Optional[str] = None) -> Dict:
        """Fetch all available data for a game - optimized version"""
        print(f"Fetching ESPN data for {away_abbr} @ {home_abbr}...")
        
        result = {
            'away': {
                'team_info': cls.fetch_team_season_stats(away_abbr),
                'detailed_stats': {},  # Skip for now
                'leaders': cls.fetch_team_leaders(away_abbr),
                'schedule': [],
                'last_five': cls.fetch_last_five_games(away_abbr),
                'splits': cls.calculate_performance_splits(away_abbr),
                'rest_days': None,
                'travel_distance': None
            },
            'home': {
                'team_info': cls.fetch_team_season_stats(home_abbr),
                'detailed_stats': {},  # Skip for now
                'leaders': cls.fetch_team_leaders(home_abbr),
                'schedule': [],
                'last_five': cls.fetch_last_five_games(home_abbr),
                'splits': cls.calculate_performance_splits(home_abbr),
                'rest_days': None,
                'travel_distance': None
            },
            'game_summary': {}  # Default empty, will be populated if game_id provided
        }
        
        if game_id:
            game_summary = cls.fetch_game_summary(game_id)
            result['game_summary'] = game_summary
            
            # Calculate rest days and travel distance
            if game_summary.get('venue'):
                venue = game_summary['venue']
                game_city = venue.get('city', '')
                game_state = venue.get('state', '')
                
                # Get game date from somewhere (would need to pass it in)
                # For now, use current date as placeholder
                game_date = datetime.now().isoformat()
                
                # Calculate rest days
                result['away']['rest_days'] = cls.calculate_rest_days(
                    result['away']['schedule'], game_date
                )
                result['home']['rest_days'] = cls.calculate_rest_days(
                    result['home']['schedule'], game_date
                )
                
                # Calculate travel distance for away team
                if result['away']['schedule']:
                    # Find away team's home city (last home game)
                    away_home_city = None
                    away_home_state = None
                    for game in reversed(result['away']['schedule']):
                        # This is simplified - would need to check if team was home
                        if game.get('city') and game.get('state'):
                            away_home_city = game['city']
                            away_home_state = game['state']
                            break
                    
                    if away_home_city and away_home_state:
                        away_coords = cls.get_city_coordinates(away_home_city, away_home_state)
                        game_coords = cls.get_city_coordinates(game_city, game_state)
                        
                        if away_coords != (0, 0) and game_coords != (0, 0):
                            distance = cls.calculate_distance(
                                away_coords[0], away_coords[1],
                                game_coords[0], game_coords[1]
                            )
                            result['away']['travel_distance'] = round(distance, 1)
                        else:
                            result['away']['travel_distance'] = 0
                    else:
                        result['away']['travel_distance'] = 0
                else:
                    result['away']['travel_distance'] = 0
                
                # Home team doesn't travel
                result['home']['travel_distance'] = 0
        
        return result

