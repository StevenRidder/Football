#!/usr/bin/env python3
"""Quick check for Week 10 lines from Odds API."""
import requests
import os
from datetime import datetime

api_key = os.getenv('ODDS_API_KEY', '8349c09e3dae852bd7e9bc724819cdd0')
url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds'

r = requests.get(url, params={
    'apiKey': api_key,
    'regions': 'us',
    'markets': 'spreads,totals',
    'oddsFormat': 'american'
}, timeout=10)

if r.status_code == 200:
    games = r.json()
    print(f"✅ Total games available: {len(games)}\n")
    
    # Group by week (rough estimate based on dates)
    week10_games = []
    for g in games:
        try:
            dt_str = g.get('commence_time', '')
            if dt_str:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                # Week 10 roughly Nov 3-11
                if dt.month == 11 or (dt.month == 10 and dt.day >= 31):
                    week10_games.append({
                        'away': g.get('away_team', '?'),
                        'home': g.get('home_team', '?'),
                        'date': dt.strftime('%Y-%m-%d %H:%M'),
                        'has_spread': bool(g.get('bookmakers', []))
                    })
        except:
            pass
    
    print(f"📅 Week 10 games: {len(week10_games)}\n")
    for g in week10_games:
        print(f"  {g['away']} @ {g['home']} - {g['date']} {'✅' if g['has_spread'] else '⚠️ no lines'}")
else:
    print(f"❌ API Error: {r.status_code}")

