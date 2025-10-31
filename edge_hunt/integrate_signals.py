"""
Integration module to add Edge Hunt signals to existing predictions.

This module enriches prediction data with high-conviction signals from Edge Hunt:
- Weather signals (wind, precipitation)
- QB/OL injury signals
- Detailed explanations for each signal

Usage:
    from edge_hunt.integrate_signals import enrich_predictions_with_signals
    
    predictions_df = pd.read_csv('predictions.csv')
    enriched_df = enrich_predictions_with_signals(predictions_df, week=9, season=2025)
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import sys
from pathlib import Path
import pickle
import hashlib

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from edge_hunt.weather_features import get_weather_snapshot
from edge_hunt.feature_transforms import weather_to_total_adjustment
from edge_hunt.qb_ol_features import calculate_game_injury_adjustment
from edge_hunt.llm_injury_detector import detect_injuries_openai, calculate_injury_impact
from edge_hunt.situational_factors_fast import get_all_situational_adjustments_fast
from market_implied_scores import market_to_implied_score, implied_score_to_spread_total
from nfl_edge.adjusted_recommendations import generate_adjusted_recommendations
import os

# OpenAI API key should be set via environment variable OPENAI_API_KEY
# Example: export OPENAI_API_KEY="your-key-here"

# Simple cache for signals (expires after 1 hour)
_SIGNAL_CACHE = {}
_CACHE_EXPIRY = 3600  # 1 hour in seconds


def estimate_kickoff_utc(week: int, season: int = 2025) -> datetime:
    """Estimate Sunday 1pm ET kickoff for a given week."""
    season_start = datetime(season, 9, 5)
    while season_start.weekday() != 6:  # 6 = Sunday
        season_start += timedelta(days=1)
    
    game_date = season_start + timedelta(weeks=week - 1)
    kickoff = game_date.replace(hour=18, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    
    return kickoff


def get_edge_hunt_signals(
    away: str, 
    home: str, 
    open_total: float, 
    open_spread: float,
    kickoff_utc: datetime
) -> Dict:
    """
    Get Edge Hunt signals for a game with detailed explanations.
    
    Uses 1-hour cache to avoid slow API calls on every page load.
    
    Returns:
        Dictionary with:
        - has_signal: bool
        - signals: list of signal dicts
        - total_edge: float
        - spread_edge: float
    """
    # Check cache first
    cache_key = f"{away}_{home}_{kickoff_utc.date()}"
    if cache_key in _SIGNAL_CACHE:
        cached_data, cached_time = _SIGNAL_CACHE[cache_key]
        if (datetime.now(timezone.utc) - cached_time).total_seconds() < _CACHE_EXPIRY:
            return cached_data
    
    signals = []
    total_edge = 0.0
    spread_edge = 0.0
    
    # 1. Check weather signals
    weather_snapshot = get_weather_snapshot(home, away, kickoff_utc)
    
    if weather_snapshot:
        weather_features = weather_to_total_adjustment(weather_snapshot)
        
        # High wind signal
        if weather_features.wind_mph >= 20:
            wind_impact = weather_features.wind_penalty_pts
            total_edge += abs(wind_impact)
            
            signals.append({
                'type': 'weather',
                'icon': '🌪️',
                'badge': 'HIGH WIND',
                'badge_color': 'warning',
                'severity': 'high' if weather_features.wind_mph >= 30 else 'medium',
                'bet_type': 'total',
                'bet_side': 'under',
                'edge_pts': abs(wind_impact),
                'explanation': f"Wind speed of {weather_features.wind_mph:.0f} mph will significantly reduce passing efficiency and scoring. Historical data shows games with wind >20 mph average {abs(wind_impact):.1f} fewer points.",
                'details': [
                    f"Wind Speed: {weather_features.wind_mph:.0f} mph ({weather_snapshot.wind_bin})",
                    f"Expected Impact: {wind_impact:.1f} points",
                    f"Recommended: BET UNDER {open_total}",
                    f"Research: Wind >20 mph reduces totals by 3-5 points on average"
                ],
                'confidence': 'HIGH' if weather_features.wind_mph >= 30 else 'MEDIUM'
            })
        
        # Precipitation signal
        if weather_features.precip_mmph >= 1.0:
            precip_impact = weather_features.precip_penalty_pts
            total_edge += abs(precip_impact)
            
            signals.append({
                'type': 'weather',
                'icon': '🌧️',
                'badge': 'HEAVY RAIN',
                'badge_color': 'info',
                'severity': 'high' if weather_features.precip_mmph >= 3.0 else 'medium',
                'bet_type': 'total',
                'bet_side': 'under',
                'edge_pts': abs(precip_impact),
                'explanation': f"Heavy precipitation ({weather_features.precip_mmph:.1f} mm/hr) affects ball handling, footing, and visibility. Expect {abs(precip_impact):.1f} fewer points scored.",
                'details': [
                    f"Precipitation: {weather_features.precip_mmph:.1f} mm/hr ({weather_snapshot.precip_bin})",
                    f"Expected Impact: {precip_impact:.1f} points",
                    f"Recommended: BET UNDER {open_total}",
                    f"Research: Heavy rain reduces totals by 1-2 points on average"
                ],
                'confidence': 'HIGH' if weather_features.precip_mmph >= 3.0 else 'MEDIUM'
            })
    
    # 2. Check QB/OL injury signals using LLM
    print(f"  🔍 Detecting injuries for {away} @ {home} using OpenAI...")
    
    # Use LLM to detect injuries
    injuries = detect_injuries_openai(away, home)
    injury_impacts = calculate_injury_impact(injuries)
    
    # Store ALL injuries for display (not just significant ones)
    all_injuries = []
    for injury in injuries:
        all_injuries.append({
            'team': injury.team,
            'player': injury.player_name,
            'position': injury.position,
            'status': injury.status,
            'injury_type': injury.injury_type,
            'impact_level': injury.impact_level,
            'estimated_impact': injury_impacts.get(injury.team, 0.0) if injury.status in ['out', 'doubtful'] else 0.0
        })
    
    # Calculate impacts per team
    away_qb_impact = 0.0
    home_qb_impact = 0.0
    away_ol_impact = 0.0
    home_ol_impact = 0.0
    
    for injury in injuries:
        if injury.status not in ["out", "doubtful"]:
            continue
        
        if injury.team == away:
            if injury.position == "QB":
                away_qb_impact += injury_impacts.get(away, 0.0)
            elif injury.position in ["LT", "LG", "C", "RG", "RT"]:
                away_ol_impact += -2.0
        elif injury.team == home:
            if injury.position == "QB":
                home_qb_impact += injury_impacts.get(home, 0.0)
            elif injury.position in ["LT", "LG", "C", "RG", "RT"]:
                home_ol_impact += -2.0
    
    # Calculate spread adjustment (positive = favors home)
    spread_adj = away_qb_impact - home_qb_impact + away_ol_impact - home_ol_impact
    injury_total_adj = away_qb_impact + home_qb_impact + away_ol_impact + home_ol_impact
    
    print(f"    Found {len(injuries)} injuries: {away} impact={injury_impacts.get(away, 0.0):.1f}, {home} impact={injury_impacts.get(home, 0.0):.1f}")
    
    # QB injury signal (using LLM-detected impacts)
    # away_qb_impact = injury_details['away_qb_drop_off']
    # home_qb_impact = injury_details['home_qb_drop_off']
    
    if away_qb_impact < -3.0:
        spread_edge += abs(spread_adj)
        total_edge += abs(away_qb_impact)
        
        signals.append({
            'type': 'injury',
            'icon': '🏈',
            'badge': 'BACKUP QB',
            'badge_color': 'danger',
            'severity': 'high',
            'bet_type': 'both',
            'bet_side': 'home_spread',
            'edge_pts': abs(spread_adj),
            'explanation': f"{away} backup QB starting. Historical data shows backup QBs reduce team scoring by 6-10 points and perform 3-5 points worse against the spread.",
            'details': [
                f"Team: {away} (Away)",
                f"Expected Impact: {away_qb_impact:.1f} points",
                f"Spread Adjustment: {spread_adj:.1f} points toward {home}",
                f"Recommended: BET {home} {open_spread:+.1f}",
                f"Also Consider: BET UNDER {open_total}",
                f"Research: Elite → Backup QB = -8 to -10 points"
            ],
            'confidence': 'HIGH'
        })
    
    if home_qb_impact < -3.0:
        spread_edge += abs(spread_adj)
        total_edge += abs(home_qb_impact)
        
        signals.append({
            'type': 'injury',
            'icon': '🏈',
            'badge': 'BACKUP QB',
            'badge_color': 'danger',
            'severity': 'high',
            'bet_type': 'both',
            'bet_side': 'away_spread',
            'edge_pts': abs(spread_adj),
            'explanation': f"{home} backup QB starting. Historical data shows backup QBs reduce team scoring by 6-10 points and perform 3-5 points worse against the spread.",
            'details': [
                f"Team: {home} (Home)",
                f"Expected Impact: {home_qb_impact:.1f} points",
                f"Spread Adjustment: {spread_adj:.1f} points toward {away}",
                f"Recommended: BET {away} {-open_spread:+.1f}",
                f"Also Consider: BET UNDER {open_total}",
                f"Research: Elite → Backup QB = -8 to -10 points"
            ],
            'confidence': 'HIGH'
        })
    
    # OL injury signal (already calculated above from LLM injuries)
    # away_ol_impact = injury_details['away_ol_penalty']
    # home_ol_impact = injury_details['home_ol_penalty']
    
    if away_ol_impact < -2.0:
        spread_edge += abs(away_ol_impact)
        
        signals.append({
            'type': 'injury',
            'icon': '⚠️',
            'badge': 'OL INJURIES',
            'badge_color': 'warning',
            'severity': 'medium',
            'bet_type': 'spread',
            'bet_side': 'home_spread',
            'edge_pts': abs(away_ol_impact),
            'explanation': f"{away} has multiple offensive line starters out. OL injuries significantly reduce offensive efficiency, protection, and rushing yards.",
            'details': [
                f"Team: {away} (Away)",
                f"Expected Impact: {away_ol_impact:.1f} points",
                f"Spread Adjustment: {away_ol_impact:.1f} points",
                f"Recommended: BET {home} {open_spread:+.1f}",
                f"Research: 2+ OL starters out = -4 points ATS"
            ],
            'confidence': 'MEDIUM'
        })
    
    if home_ol_impact < -2.0:
        spread_edge += abs(home_ol_impact)
        
        signals.append({
            'type': 'injury',
            'icon': '⚠️',
            'badge': 'OL INJURIES',
            'badge_color': 'warning',
            'severity': 'medium',
            'bet_type': 'spread',
            'bet_side': 'away_spread',
            'edge_pts': abs(home_ol_impact),
            'explanation': f"{home} has multiple offensive line starters out. OL injuries significantly reduce offensive efficiency, protection, and rushing yards.",
            'details': [
                f"Team: {home} (Home)",
                f"Expected Impact: {home_ol_impact:.1f} points",
                f"Spread Adjustment: {home_ol_impact:.1f} points",
                f"Recommended: BET {away} {-open_spread:+.1f}",
                f"Research: 2+ OL starters out = -4 points ATS"
            ],
            'confidence': 'MEDIUM'
        })
    
    # 3. Check situational factors (travel, home/away splits, divisional)
    print(f"  🎯 Checking situational factors for {away} @ {home}...")
    
    situational = get_all_situational_adjustments_fast(away, home)
    
    if situational['has_adjustment']:
        # Add situational adjustments to edges
        spread_edge += abs(situational['spread_adjustment'])
        total_edge += abs(situational['total_adjustment'])
        
        # Create signal for situational factors
        signals.append({
            'type': 'situational',
            'icon': '📊',
            'badge': 'SITUATIONAL EDGE',
            'badge_color': 'info',
            'severity': 'medium',
            'bet_type': 'both',
            'bet_side': 'varies',
            'edge_pts': abs(situational['spread_adjustment']) + abs(situational['total_adjustment']),
            'explanation': f"Multiple situational factors detected: {', '.join(situational['explanations'][:2])}",
            'details': situational['explanations'],
            'confidence': 'MEDIUM'
        })
        
        print(f"    Found {len(situational['explanations'])} situational factors:")
        for exp in situational['explanations']:
            print(f"      • {exp}")
    
    # 4. Create comprehensive "ALL ADJUSTMENTS" summary signal
    all_adjustment_details = []
    total_away_adj = situational.get('away_adjustment', 0.0) + injury_impacts.get(away, 0.0)
    total_home_adj = situational.get('home_adjustment', 0.0) + injury_impacts.get(home, 0.0)
    
    # Add weather details
    if weather_snapshot:
        wf = weather_to_total_adjustment(weather_snapshot)
        all_adjustment_details.append(f"🌤️ WEATHER: Wind {weather_snapshot.wind_mph:.1f} mph, {weather_snapshot.precip_bin} precip → {wf.total_adjustment_pts:+.1f} pts")
    else:
        all_adjustment_details.append("🌤️ WEATHER: No data available")
    
    # Add injury details
    if len(all_injuries) > 0:
        all_adjustment_details.append(f"🏥 INJURIES ({len(all_injuries)} total):")
        for inj in all_injuries:
            impact = inj.get('estimated_impact', 0)
            all_adjustment_details.append(f"  • {inj['team']} - {inj['player']} ({inj['position']}) {inj['status']}: {impact:+.1f} pts")
        all_adjustment_details.append(f"  Total: {away} {injury_impacts.get(away, 0.0):+.1f} pts, {home} {injury_impacts.get(home, 0.0):+.1f} pts")
    else:
        all_adjustment_details.append("🏥 INJURIES: None detected")
    
    # Add situational details (already have them from situational['explanations'])
    if situational['has_adjustment']:
        all_adjustment_details.append(f"📊 SITUATIONAL ({len(situational['explanations'])} factors):")
        for exp in situational['explanations']:
            all_adjustment_details.append(f"  • {exp}")
        all_adjustment_details.append(f"  Total: {away} {situational.get('away_adjustment', 0.0):+.2f} pts, {home} {situational.get('home_adjustment', 0.0):+.2f} pts")
    else:
        all_adjustment_details.append("📊 SITUATIONAL: No adjustments")
    
    # Add final summary
    all_adjustment_details.append("")
    all_adjustment_details.append(f"📈 TOTAL ADJUSTMENTS:")
    all_adjustment_details.append(f"  {away}: {total_away_adj:+.2f} pts")
    all_adjustment_details.append(f"  {home}: {total_home_adj:+.2f} pts")
    all_adjustment_details.append(f"  Spread impact: {total_away_adj - total_home_adj:+.2f} pts")
    all_adjustment_details.append(f"  Total impact: {total_away_adj + total_home_adj:+.2f} pts")
    
    # Add this comprehensive signal to the list
    if len(all_injuries) > 0 or situational['has_adjustment'] or (weather_snapshot and abs(wf.total_adjustment_pts) > 0.1):
        signals.append({
            'type': 'summary',
            'icon': '📋',
            'badge': 'ALL ADJUSTMENTS',
            'badge_color': 'primary',
            'severity': 'info',
            'bet_type': 'info',
            'bet_side': 'N/A',
            'edge_pts': abs(total_away_adj) + abs(total_home_adj),
            'explanation': f"Complete breakdown: Weather + Injuries + Situational factors",
            'details': all_adjustment_details,
            'confidence': 'DATA-DRIVEN'
        })
    
    result = {
        'has_signal': len(signals) > 0,
        'signals': signals,
        'total_edge': total_edge,
        'spread_edge': spread_edge,
        'signal_count': len(signals),
        'all_injuries': all_injuries,  # ALL injuries for both teams
        'away_total_impact': injury_impacts.get(away, 0.0),
        'home_total_impact': injury_impacts.get(home, 0.0),
        'situational_away_adj': situational.get('away_adjustment', 0.0),
        'situational_home_adj': situational.get('home_adjustment', 0.0),
        'situational_spread_adj': situational.get('spread_adjustment', 0.0),
        'situational_total_adj': situational.get('total_adjustment', 0.0)
    }
    
    # Cache the result
    _SIGNAL_CACHE[cache_key] = (result, datetime.now(timezone.utc))
    
    return result


def enrich_predictions_with_signals(
    predictions_df: pd.DataFrame,
    week: int,
    season: int = 2025
) -> pd.DataFrame:
    """
    Enrich predictions DataFrame with Edge Hunt signals.
    
    Args:
        predictions_df: DataFrame with predictions (must have 'away', 'home' columns)
        week: NFL week number
        season: NFL season year
    
    Returns:
        Enriched DataFrame with Edge Hunt signal columns
    """
    df = predictions_df.copy()
    
    # Estimate kickoff time
    kickoff_utc = estimate_kickoff_utc(week, season)
    
    # Add signal columns
    df['edge_hunt_signals'] = None
    df['has_edge_hunt_signal'] = False
    df['edge_hunt_signal_count'] = 0
    df['edge_hunt_total_edge'] = 0.0
    df['edge_hunt_spread_edge'] = 0.0
    
    # Add market-implied score columns
    df['market_implied_away'] = 0.0
    df['market_implied_home'] = 0.0
    df['adjusted_away'] = 0.0
    df['adjusted_home'] = 0.0
    df['adjusted_spread'] = 0.0
    df['adjusted_total'] = 0.0
    
    for idx, row in df.iterrows():
        away = row['away']
        home = row['home']
        
        # Get opening lines (use current predictions if not available)
        open_total = row.get('Total used', row.get('predicted_total', 47.0))
        open_spread = row.get('Spread used (home-)', row.get('predicted_spread', 0.0))
        
        # Calculate market-implied scores (don't round yet - need precision for adjustments)
        market_away, market_home = market_to_implied_score(open_spread, open_total)
        
        # Round for display only
        market_away_rounded = round(market_away * 2) / 2
        market_home_rounded = round(market_home * 2) / 2
        df.at[idx, 'market_implied_away'] = market_away_rounded
        df.at[idx, 'market_implied_home'] = market_home_rounded
        
        # Get Edge Hunt signals
        signals_data = get_edge_hunt_signals(
            away, home, open_total, open_spread, kickoff_utc
        )
        
        # Calculate adjusted scores based on signals
        # Apply per-team adjustments (not split evenly!)
        # Combine situational + injury adjustments
        away_adjustment = signals_data.get('situational_away_adj', 0.0) + signals_data.get('away_total_impact', 0.0)
        home_adjustment = signals_data.get('situational_home_adj', 0.0) + signals_data.get('home_total_impact', 0.0)
        
        # Apply adjustments to market-implied scores
        # Negative adjustment = lower scoring for that specific team
        adjusted_away = market_away + away_adjustment
        adjusted_home = market_home + home_adjustment
        
        # Round adjusted scores to nearest 0.5 for display and spread calculation
        rounded_away = round(adjusted_away * 2) / 2
        rounded_home = round(adjusted_home * 2) / 2
        
        # Store rounded scores
        df.at[idx, 'adjusted_away'] = rounded_away
        df.at[idx, 'adjusted_home'] = rounded_home
        
        # Calculate spread and total from rounded scores
        adj_spread = rounded_away - rounded_home
        adj_total = rounded_away + rounded_home
        
        df.at[idx, 'adjusted_spread'] = adj_spread
        df.at[idx, 'adjusted_total'] = adj_total
        
        # Store signal data
        df.at[idx, 'edge_hunt_signals'] = signals_data['signals']
        df.at[idx, 'has_edge_hunt_signal'] = signals_data['has_signal']
        df.at[idx, 'edge_hunt_signal_count'] = signals_data['signal_count']
        df.at[idx, 'edge_hunt_total_edge'] = signals_data['total_edge']
        df.at[idx, 'edge_hunt_spread_edge'] = signals_data['spread_edge']
        
        # Store injury data (ALL injuries for display) - convert to JSON string for pandas
        import json
        df.at[idx, 'all_injuries'] = json.dumps(signals_data.get('all_injuries', []))
        df.at[idx, 'away_injury_impact'] = signals_data.get('away_total_impact', 0.0)
        df.at[idx, 'home_injury_impact'] = signals_data.get('home_total_impact', 0.0)
    
    # Generate betting recommendations based on ADJUSTED vs MARKET
    # This REPLACES the old model-based recommendations
    print("\n🎯 Generating betting recommendations (ADJUSTED vs MARKET)...")
    df = generate_adjusted_recommendations(df, min_spread_edge=2.0, min_total_edge=2.0)
    
    return df


if __name__ == "__main__":
    # Test the integration
    print("Testing Edge Hunt integration...")
    
    # Create sample predictions
    test_predictions = pd.DataFrame({
        'away': ['BAL', 'CAR', 'BUF'],
        'home': ['MIA', 'GB', 'KC'],
        'Total used': [48.7, 44.0, 69.3],
        'Spread used (home-)': [12.7, -12.5, -6.1],
    })
    
    # Enrich with signals
    enriched = enrich_predictions_with_signals(test_predictions, week=9, season=2025)
    
    # Display results
    print(f"\n{'='*80}")
    print("ENRICHED PREDICTIONS WITH EDGE HUNT SIGNALS")
    print(f"{'='*80}\n")
    
    for idx, row in enriched.iterrows():
        print(f"{row['away']} @ {row['home']}")
        print(f"  Has Signal: {row['has_edge_hunt_signal']}")
        print(f"  Signal Count: {row['edge_hunt_signal_count']}")
        
        if row['has_edge_hunt_signal']:
            for signal in row['edge_hunt_signals']:
                print(f"\n  {signal['icon']} {signal['badge']} ({signal['confidence']})")
                print(f"  {signal['explanation']}")
                print(f"  Edge: {signal['edge_pts']:.1f} points")
        
        print()

