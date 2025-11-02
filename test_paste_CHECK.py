#!/usr/bin/env python3
"""Test bet pasting functionality"""
from playwright.sync_api import sync_playwright
import time

bet_data = """Ticket Number: 908414722-1
Accepted Date: 11/01/25 08:29 GMT-10
Type: Parlay
Product: Sportsbook
Amount: $30.00
To win: $1,460.37
Status: Pending
Description: Football - NFL - Chicago Bears vs Cincinnati Bengals - Parlay | 451 Chicago Bears -2½ -120 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Atlanta Falcons vs New England Patriots - Parlay | 456 New England Patriots -5 -110 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Indianapolis Colts vs Pittsburgh Steelers - Parlay | 457 Indianapolis Colts -3 -120 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Denver Broncos vs Houston Texans - Parlay | 463 Denver Broncos +2½ -110 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Jacksonville Jaguars vs Las Vegas Raiders - Parlay | 467 Jacksonville Jaguars -2½ -115 For Game | 11/02/2025 | 04:05:00 PM (EST) | PendingFootball - NFL - Carolina Panthers vs Green Bay Packers - Parlay | 460 Green Bay Packers -900 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Minnesota Vikings vs Detroit Lions - Parlay | 462 Detroit Lions -9 -105 For Game | 11/02/2025 | 01:00:00 PM (EST) | Pending"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("\n" + "="*80)
    print("🎯 TESTING BET PASTE FUNCTIONALITY")
    print("="*80 + "\n")
    
    # Navigate to bets page
    print("1. Loading bets page...")
    page.goto('http://localhost:9876/bets', wait_until='networkidle', timeout=15000)
    print("   ✅ Page loaded\n")
    
    # Check if paste textarea exists
    print("2. Checking for paste interface...")
    if page.locator('#bet-paste-area').count() > 0:
        print("   ✅ Paste textarea found\n")
    else:
        print("   ❌ Paste textarea NOT FOUND\n")
        browser.close()
        exit(1)
    
    # Paste the bet
    print("3. Pasting 7-leg parlay...")
    page.locator('#bet-paste-area').fill(bet_data)
    print("   ✅ Data pasted\n")
    
    # Click load button
    print("4. Clicking Load Bets button...")
    page.locator('button:has-text("Load Bets")').click()
    print("   ✅ Button clicked\n")
    
    # Wait for bet to appear in table
    print("5. Waiting for bet to appear in table...")
    try:
        page.wait_for_selector('text="908414722-1"', timeout=10000)
        print("   ✅ Bet found in table\n")
    except:
        print("   ❌ Bet NOT found in table\n")
        browser.close()
        exit(1)
    
    # Click on the bet row to open modal/legs
    print("6. Clicking bet to view legs...")
    page.locator('tr:has-text("908414722-1")').click()
    time.sleep(2)
    
    # Check if legs are displayed (either in modal or expanded row)
    print("7. Checking for parlay legs...")
    
    # Check for modal
    modal_visible = page.locator('.modal.show').count() > 0
    if modal_visible:
        print("   ✅ Modal opened")
        legs_count = page.locator('.modal.show').locator('tr').count()
        print(f"   Found {legs_count} leg rows in modal")
    else:
        # Check for expanded row
        expanded = page.locator('tr:has-text("CHI")').count() > 0
        if expanded:
            print("   ✅ Legs displayed in expanded row")
        else:
            print("   ❌ No legs displayed (no modal, no expanded row)")
    
    print("\n📸 Taking screenshot...")
    page.screenshot(path='paste_test.png', full_page=True)
    print("   Saved: paste_test.png")
    
    print("\n⏸️  Keeping browser open for 8 seconds...")
    time.sleep(8)
    browser.close()
    
    print("\n" + "="*80)
    print("✅ PASTE TEST COMPLETE")
    print("="*80)

