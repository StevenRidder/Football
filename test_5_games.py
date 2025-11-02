#!/usr/bin/env python3
"""Test 5 different game pages with Playwright"""
from playwright.sync_api import sync_playwright
import re
import pandas as pd

# Load actual games from predictions
df = pd.read_csv('artifacts/simulator_predictions.csv')
games = []
for _, row in df[['away_team', 'home_team', 'week']].head(5).iterrows():
    games.append((row['away_team'], row['home_team'], f"Week {int(row['week'])}"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("\n" + "="*70)
    print("TESTING 5 GAME PAGES - DATA VALIDATION")
    print("="*70 + "\n")
    
    for away, home, week in games:
        url = f'http://localhost:9876/game/{away}/{home}'
        print(f"\n📊 {week}: {away} @ {home}")
        
        try:
            page.goto(url, wait_until='networkidle', timeout=15000)
            page.wait_for_selector('table', timeout=10000)
            
            # Check key stats
            all_good = True
            for stat in ['Passing EPA', 'Rushing EPA', 'Passing Yards', 'Rushing Yards']:
                row = page.locator(f'tr:has-text("{stat}")').first
                if row.count() > 0:
                    text = row.inner_text()
                    nums = re.findall(r'[-]?\d+\.?\d*', text)
                    non_zero = [n for n in nums if float(n) != 0.0]
                    
                    if non_zero:
                        print(f"   ✅ {stat:20s}: {nums}")
                    else:
                        print(f"   ❌ {stat:20s}: ZEROS {nums}")
                        all_good = False
            
            if all_good:
                print(f"   ✅ ALL DATA PRESENT - NO ZEROS")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n" + "="*70)
    print("✅ ALL 5 GAMES TESTED")
    print("="*70)
    
    import time
    time.sleep(8)
    browser.close()
