#!/usr/bin/env python3
"""Test 5 different game pages with Playwright - games with sufficient history"""
from playwright.sync_api import sync_playwright
import re
import pandas as pd

# Load games from later weeks (teams have history)
df = pd.read_csv('artifacts/simulator_predictions.csv')
later_games = df[df['week'] >= 5][['away_team', 'home_team', 'week']].head(5)
games = [(row['away_team'], row['home_team'], int(row['week'])) for _, row in later_games.iterrows()]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("\n" + "="*80)
    print("TESTING 5 GAME PAGES FROM DIFFERENT WEEKS - DATA VALIDATION")
    print("="*80 + "\n")
    
    pass_count = 0
    for away, home, week in games:
        url = f'http://localhost:9876/game/{away}/{home}'
        print(f"📊 Week {week}: {away} @ {home}")
        
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
                        print(f"   ❌ {stat:20s}: ALL ZEROS")
                        all_good = False
            
            if all_good:
                print(f"   ✅✅ PASS - ALL DATA PRESENT, NO ZEROS\n")
                pass_count += 1
            else:
                print(f"   ❌❌ FAIL - SOME DATA MISSING\n")
                
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)[:80]}\n")
    
    print("="*80)
    print(f"FINAL RESULT: {pass_count}/5 games with complete data")
    print("="*80)
    
    import time
    time.sleep(8)
    browser.close()

