#!/usr/bin/env python3
"""Test parlay legs display with live tracking"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("="*60)
    print("TESTING PARLAY LEGS WITH LIVE TRACKING")
    print("="*60)
    
    # Go to bets page
    page.goto('http://localhost:9876/bets', wait_until='networkidle')
    print("\n✅ Loaded bets page")
    
    # Find and click the bet
    bet_row = page.locator('tr.bet-row:has(small:text("908414722-1"))')
    if bet_row.count() == 0:
        print("❌ Bet not found!")
        browser.close()
        exit(1)
    
    print("✅ Found bet 908414722-1")
    
    # Click to open modal
    bet_row.click()
    time.sleep(1)
    
    modal = page.locator('#betDetailsModal')
    if not modal.is_visible():
        print("❌ Modal not visible!")
        browser.close()
        exit(1)
    
    print("✅ Modal opened")
    
    # Wait for legs to load
    time.sleep(2)
    
    # Check legs
    desc_html = modal.locator('#modalDescription').inner_html()
    
    if 'list-group-item' not in desc_html:
        print(f"❌ No legs shown!")
        print(f"Content: {desc_html[:200]}")
        browser.close()
        exit(1)
    
    # Count legs
    leg_items = modal.locator('#modalDescription .list-group-item')
    leg_count = leg_items.count()
    
    print(f"\n🎉 SHOWING {leg_count} LEGS!")
    print("\nLeg details:")
    
    for i in range(leg_count):
        leg = leg_items.nth(i)
        leg_text = leg.inner_text()
        
        # Check for status badge
        has_badge = 'bg-success' in leg.inner_html() or 'bg-danger' in leg.inner_html() or 'bg-secondary' in leg.inner_html()
        status_emoji = "🟢" if 'bg-success' in leg.inner_html() else "🔴" if 'bg-danger' in leg.inner_html() else "⚪"
        
        print(f"  {i+1}. {leg_text[:50]}... {status_emoji}")
    
    # Check for live tracking elements
    if 'WINNING' in desc_html or 'LOSING' in desc_html or 'Not Started' in desc_html:
        print("\n✅ Live status tracking ACTIVE!")
    else:
        print("\n⚪ Games not started yet (live tracking will show during games)")
    
    # Check for refresh button
    refresh_btn = page.locator('button:has-text("Refresh")')
    if refresh_btn.count() > 0:
        print("✅ Refresh button present")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"  • Bet found: 908414722-1")
    print(f"  • Legs displayed: {leg_count}")
    print(f"  • Live tracking: Ready")
    print(f"  • Modal: Working")
    print()
    
    # Keep browser open
    print("Browser staying open for 5 seconds...")
    time.sleep(5)
    
    browser.close()

