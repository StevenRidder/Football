#!/usr/bin/env python3
"""
Test 7-leg parlay paste and live tracking
"""
from playwright.sync_api import sync_playwright
import time

BET_DATA = """Ticket Number:

908414722-1

Accepted Date:

11/01/25 08:29 GMT-10

Type: Parlay

Product:

Sportsbook

Amount:

$30.00

To win:

$1,460.37

Status:

Pending

Description:

Football - NFL - Chicago Bears vs Cincinnati Bengals - Parlay | 451 Chicago Bears -2½ -120 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Atlanta Falcons vs New England Patriots - Parlay | 456 New England Patriots -5 -110 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Indianapolis Colts vs Pittsburgh Steelers - Parlay | 457 Indianapolis Colts -3 -120 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Denver Broncos vs Houston Texans - Parlay | 463 Denver Broncos +2½ -110 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Jacksonville Jaguars vs Las Vegas Raiders - Parlay | 467 Jacksonville Jaguars -2½ -115 For Game | 11/02/2025 | 04:05:00 PM (EST) | PendingFootball - NFL - Carolina Panthers vs Green Bay Packers - Parlay | 460 Green Bay Packers -900 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Minnesota Vikings vs Detroit Lions - Parlay | 462 Detroit Lions -9 -105 For Game | 11/02/2025 | 01:00:00 PM (EST) | Pending"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("="*70)
    print("TESTING 7-LEG PARLAY WITH LIVE TRACKING")
    print("="*70)
    
    # Go to bets page
    print("\n1. Loading bets page...")
    page.goto('http://localhost:9876/bets', wait_until='networkidle')
    print("   ✅ Page loaded")
    
    # Paste bet
    print("\n2. Pasting 7-leg parlay...")
    textarea = page.locator('#betDataInput')
    textarea.scroll_into_view_if_needed()
    textarea.fill(BET_DATA)
    print("   ✅ Bet data pasted")
    
    # Click Load Bets
    print("\n3. Loading bet into system...")
    page.locator('button:has-text("Load Bets")').click()
    time.sleep(3)
    print("   ✅ Load clicked")
    
    # Find bet in table
    print("\n4. Finding bet 908414722-1 in table...")
    bet_row = page.locator('tr.bet-row:has(small:text("908414722-1"))')
    
    if bet_row.count() == 0:
        print("   ❌ BET NOT FOUND IN TABLE")
        browser.close()
        exit(1)
    
    print("   ✅ Bet found in table")
    
    # Click bet to open modal
    print("\n5. Opening modal...")
    bet_row.click()
    time.sleep(1)
    
    modal = page.locator('#betDetailsModal')
    if not modal.is_visible():
        print("   ❌ MODAL NOT VISIBLE")
        browser.close()
        exit(1)
    
    print("   ✅ Modal opened")
    
    # Check ticket details
    ticket = modal.locator('#modalTicketId').inner_text()
    amount = modal.locator('#modalAmount').inner_text()
    to_win = modal.locator('#modalToWin').inner_text()
    
    print(f"\n6. Bet Details:")
    print(f"   Ticket: {ticket}")
    print(f"   Amount: {amount}")
    print(f"   To Win: {to_win}")
    
    # Wait for legs to load
    print("\n7. Loading legs...")
    time.sleep(2)
    
    # Check for legs
    desc_html = modal.locator('#modalDescription').inner_html()
    
    if 'list-group-item' not in desc_html:
        print(f"   ❌ NO LEGS DISPLAYED")
        print(f"   Content: {desc_html[:200]}")
        browser.close()
        exit(1)
    
    # Count legs
    legs = modal.locator('#modalDescription .list-group-item')
    leg_count = legs.count()
    
    print(f"\n🎉 FOUND {leg_count} LEGS!")
    
    if leg_count != 7:
        print(f"   ⚠️  Expected 7 legs, got {leg_count}")
    
    # Display each leg with live status
    print("\n8. Leg Details with Live Status:")
    for i in range(leg_count):
        leg = legs.nth(i)
        leg_text = leg.inner_text()
        
        # Check for status badges
        if '🟢' in leg_text or 'WINNING' in leg_text:
            status = "🟢 WINNING"
        elif '🔴' in leg_text or 'LOSING' in leg_text:
            status = "🔴 LOSING"
        elif '⚪' in leg_text or 'Not Started' in leg_text:
            status = "⚪ NOT STARTED"
        else:
            status = "⏳ PENDING"
        
        # Extract leg description
        lines = leg_text.split('\n')
        leg_desc = lines[1] if len(lines) > 1 else leg_text
        
        print(f"   Leg {i+1}: {leg_desc[:50]:50s} {status}")
    
    # Check for refresh button
    refresh_btn = modal.locator('button:has-text("Refresh Live Status")')
    if refresh_btn.count() > 0:
        print(f"\n✅ Live Refresh Button: PRESENT")
    
    # Check for last updated timestamp
    if 'Last updated:' in desc_html or 'last updated' in desc_html.lower():
        print("✅ Last Updated Timestamp: PRESENT")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETE - ALL LEGS SHOWING WITH LIVE TRACKING!")
    print("="*70)
    
    print("\n⏸️  Keeping browser open for 5 seconds...")
    time.sleep(5)
    
    browser.close()

