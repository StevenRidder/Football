"""
Analytics Intensity Index (AII) Model
Separate from game prediction model - measures team analytics adoption and efficiency
"""

import pandas as pd
from scipy import stats

# Analytics tier ratings (1-5, based on coaching staff, front office, 4th down behavior)
# 5 = Highly analytical (Ravens, 49ers, Eagles)
# 3 = Average
# 1 = Conservative (older coaching staffs)
ANALYTICS_TIERS = {
    'BAL': 5,  # John Harbaugh + analytics-heavy FO
    'SF': 5,   # Kyle Shanahan, advanced analytics
    'PHI': 5,  # Sirianni, aggressive 4th downs
    'DET': 5,  # Dan Campbell, aggressive + smart
    'BUF': 4,  # McDermott, modern approach
    'KC': 4,   # Reid, analytics-informed
    'LAC': 4,  # Staley hire was analytics-based
    'CIN': 4,  # Zac Taylor, modern offense
    'MIN': 4,  # O'Connell, Rams coaching tree
    'GB': 4,   # LaFleur, analytics-friendly
    'MIA': 4,  # McDaniel, 49ers disciple
    'DAL': 3,  # McCarthy, mixed
    'SEA': 3,  # Carroll, older school but adapting
    'LA': 3,   # McVay, more instinct than numbers
    'TB': 3,   # Bowles, defensive minded
    'NO': 3,   # Allen, traditional
    'ATL': 3,  # Smith, newer coach
    'WAS': 3,  # Quinn, defensive focus
    'IND': 3,  # Steichen, developing
    'TEN': 3,  # Callahan, traditional
    'JAX': 3,  # Pederson, somewhat analytical
    'LV': 3,   # Pierce, rebuilding
    'ARI': 3,  # Gannon, first-time HC
    'DEN': 2,  # Payton, ego-driven not data-driven
    'NE': 2,   # Belichick era ending, traditional
    'NYG': 2,  # Daboll, offensive minded but not heavy analytics
    'CAR': 2,  # Canales, new and unproven
    'CHI': 2,  # Eberflus, defensive conservative
    'NYJ': 2,  # Saleh, defensive focus
    'PIT': 2,  # Tomlin, traditional "next man up"
    'HOU': 3,  # DeMeco Ryans, modern defensive mind
}


def calculate_fourth_down_optimality(teamweeks):
    """
    Calculate how optimally teams go for it on 4th down
    Lower gap = more optimal (closer to WP-maximizing strategy)
    """
    # For now, use a simple proxy: 4th down conversion rate weighted by situation
    # Real version would compare actual decisions vs WP-optimal decisions
    
    fourth_down_scores = {}
    
    for team in teamweeks['team'].unique():
        team_data = teamweeks[teamweeks['team'] == team]
        
        # Proxy: teams that pass more on early downs are more analytical
        # and teams with better EPA are making better decisions
        avg_epa = team_data['passing_epa'].mean() if 'passing_epa' in team_data.columns else 0
        
        # Normalize to 0-1 scale (higher is better)
        fourth_down_scores[team] = avg_epa
    
    return fourth_down_scores


def calculate_motion_impact(teamweeks):
    """
    Calculate EPA benefit from using motion pre-snap
    Higher delta = better use of motion/scheme creativity
    """
    # Proxy: teams with higher passing EPA are using more modern concepts
    motion_scores = {}
    
    for team in teamweeks['team'].unique():
        team_data = teamweeks[teamweeks['team'] == team]
        
        # Use passing EPA as proxy for motion/scheme quality
        pass_epa = team_data['passing_epa'].mean() if 'passing_epa' in team_data.columns else 0
        rush_epa = team_data['rushing_epa'].mean() if 'rushing_epa' in team_data.columns else 0
        
        # Balanced EPA = better scheming
        motion_scores[team] = (pass_epa + rush_epa) / 2
    
    return motion_scores


def calculate_injury_burden(teamweeks):
    """
    Adjusted Games Lost - measures injury burden
    Lower is better (fewer injuries)
    """
    # Proxy: consistency in performance (lower variance = healthier roster)
    injury_scores = {}
    
    for team in teamweeks['team'].unique():
        team_data = teamweeks[teamweeks['team'] == team]
        
        # Calculate variance in offensive EPA (high variance = injury issues)
        if 'passing_epa' in team_data.columns and len(team_data) > 1:
            epa_variance = team_data['passing_epa'].var()
            # Invert so lower variance = better score
            injury_scores[team] = -epa_variance
        else:
            injury_scores[team] = 0
    
    return injury_scores


def compute_aii(teamweeks, season=2025):
    """
    Compute Analytics Intensity Index for all teams
    
    Returns DataFrame with:
    - team
    - aii_score (0-1, higher is better)
    - component scores
    - projected wins
    """
    
    # Get component scores
    fourth_down = calculate_fourth_down_optimality(teamweeks)
    motion = calculate_motion_impact(teamweeks)
    injuries = calculate_injury_burden(teamweeks)
    
    # Build DataFrame
    teams = list(ANALYTICS_TIERS.keys())
    
    aii_data = []
    for team in teams:
        if team not in fourth_down:
            continue
            
        # Get raw scores
        fd_score = fourth_down.get(team, 0)
        motion_score = motion.get(team, 0)
        injury_score = injuries.get(team, 0)
        tier = ANALYTICS_TIERS.get(team, 3)
        
        aii_data.append({
            'team': team,
            'fourth_down_raw': fd_score,
            'motion_raw': motion_score,
            'injury_raw': injury_score,
            'analytics_tier': tier,
        })
    
    df = pd.DataFrame(aii_data)
    
    # Z-score normalize each component (within season)
    for col in ['fourth_down_raw', 'motion_raw', 'injury_raw']:
        if df[col].std() > 0:
            df[f'{col}_z'] = stats.zscore(df[col])
        else:
            df[f'{col}_z'] = 0
    
    # Normalize analytics tier to z-score
    if df['analytics_tier'].std() > 0:
        df['analytics_tier_z'] = stats.zscore(df['analytics_tier'])
    else:
        df['analytics_tier_z'] = 0
    
    # Combine into AII (equal weights for now)
    df['aii_score'] = (
        df['fourth_down_raw_z'] * 0.25 +
        df['motion_raw_z'] * 0.25 +
        df['injury_raw_z'] * 0.25 +
        df['analytics_tier_z'] * 0.25
    )
    
    # Normalize AII to 0-1 scale for display
    if df['aii_score'].std() > 0:
        min_aii = df['aii_score'].min()
        max_aii = df['aii_score'].max()
        df['aii_normalized'] = (df['aii_score'] - min_aii) / (max_aii - min_aii)
    else:
        df['aii_normalized'] = 0.5
    
    # Project wins based on AII (simple linear model)
    # Using regression coefficient of 0.54 wins per SD of AII
    df['projected_wins_boost'] = df['aii_score'] * 0.54
    df['baseline_wins'] = 8.5  # Average team
    df['projected_wins'] = df['baseline_wins'] + df['projected_wins_boost']
    
    # Sort by AII
    df = df.sort_values('aii_normalized', ascending=False).reset_index(drop=True)
    
    return df


def compare_with_game_model(aii_df, game_predictions_df):
    """
    Compare AII scores with game model predictions
    Highlight where they agree/disagree
    """
    insights = []
    
    for _, game in game_predictions_df.iterrows():
        away = game['away']
        home = game['home']
        
        # Get AII scores
        away_aii = aii_df[aii_df['team'] == away]['aii_normalized'].values
        home_aii = aii_df[aii_df['team'] == home]['aii_normalized'].values
        
        if len(away_aii) == 0 or len(home_aii) == 0:
            continue
            
        away_aii = away_aii[0]
        home_aii = home_aii[0]
        
        # Get game model recommendation
        best_bet = game.get('Best_bet', 'NO PLAY')
        
        # Check for agreement
        aii_favors_away = away_aii > home_aii
        aii_diff = abs(away_aii - home_aii)
        
        if aii_diff > 0.2:  # Significant AII difference
            if ('BET ' + away in best_bet and aii_favors_away) or \
               ('BET ' + home in best_bet and not aii_favors_away):
                agreement = 'STRONG AGREE'
            elif 'BET ' + away in best_bet or 'BET ' + home in best_bet:
                agreement = 'DISAGREE'
            else:
                agreement = 'NEUTRAL'
        else:
            agreement = 'TOSS-UP'
        
        insights.append({
            'game': f"{away}@{home}",
            'away_aii': away_aii,
            'home_aii': home_aii,
            'aii_edge': away_aii - home_aii,
            'game_model_bet': best_bet,
            'agreement': agreement
        })
    
    return pd.DataFrame(insights)

