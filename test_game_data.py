#!/usr/bin/env python3
"""
Test game page data with Playwright
"""
from playwright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("="*70)
    print("TESTING GAME PAGE DATA")
    print("="*70)
    
    # Navigate to game page
    print("\nLoading: http://localhost:9876/game/BAL/MIA")
    page.goto('http://localhost:9876/game/BAL/MIA', wait_until='networkidle')
    
    # Wait for content to load
    page.wait_for_selector('table', timeout=10000)
    
    # Get all text from the page
    content = page.content()
    
    # Check for data in the stats table
    print("\n📊 Checking Team Stats Table...")
    
    # Look for specific stats
    stats_to_check = [
        'Offensive EPA',
        'Passing EPA',
        'Rushing EPA',
        'Passing Yards',
        'Rushing Yards',
        'Turnovers'
    ]
    
    for stat in stats_to_check:
        # Find the row with this stat
        row = page.locator(f'tr:has-text("{stat}")').first
        if row.count() > 0:
            row_text = row.inner_text()
            # Extract numbers from the row
            numbers = re.findall(r'[-]?\d+\.?\d*', row_text)
            
            # Check if all values are 0
            non_zero = [n for n in numbers if float(n) != 0.0]
            
            if non_zero:
                print(f"  ✅ {stat:30s}: Has data {numbers}")
            else:
                print(f"  ❌ {stat:30s}: ALL ZEROS {numbers}")
        else:
            print(f"  ⚠️  {stat:30s}: NOT FOUND")
    
    # Check recent games section
    print("\n📅 Checking Recent Games...")
    
    games_text = page.locator('text="No game data available"').count()
    if games_text > 0:
        print(f"  ❌ Found {games_text} 'No game data available' messages")
    else:
        print("  ✅ Game data sections present")
    
    # Take screenshot
    print("\n📸 Taking screenshot...")
    page.screenshot(path='game_page_test.png', full_page=True)
    print("  ✅ Saved to: game_page_test.png")
    
    print("\n⏸️  Keeping browser open for 10 seconds to inspect...")
    import time
    time.sleep(10)
    
    browser.close()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

