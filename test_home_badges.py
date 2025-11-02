#!/usr/bin/env python3
"""Check for team betting record badges on HOME page"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("\n" + "="*80)
    print("🔍 CHECKING HOME PAGE FOR TEAM BETTING RECORD BADGES")
    print("="*80 + "\n")
    
    url = 'http://localhost:9876/'
    print(f"Loading: {url}\n")
    
    page.goto(url, wait_until='networkidle', timeout=15000)
    page.wait_for_selector('table, .card', timeout=10000)
    
    print("✅ Page loaded\n")
    
    # Count all badges
    all_badges = page.locator('.badge').count()
    print(f"Total badges on page: {all_badges}\n")
    
    # Look for team records / ATS records
    print("Looking for team/betting record badges...")
    
    # Check for patterns like "3-2", "5-3", team names with records
    badges_text = []
    for i in range(min(30, all_badges)):
        try:
            badge = page.locator('.badge').nth(i)
            text = badge.inner_text()
            badges_text.append(text)
        except:
            pass
    
    print(f"\nFirst 30 badges found:")
    for text in badges_text[:30]:
        print(f"  - {text}")
    
    # Check for performance summary section
    print("\n" + "="*80)
    print("Checking for Performance Summary section:")
    if page.locator('#performance-summary').count() > 0:
        print("  ✅ Found #performance-summary div")
        is_visible = page.locator('#performance-summary').is_visible()
        print(f"  Visible: {is_visible}")
    else:
        print("  ❌ No #performance-summary div")
    
    if page.locator('#week-record').count() > 0:
        text = page.locator('#week-record').inner_text()
        print(f"  Week record: {text}")
    
    if page.locator('#season-record').count() > 0:
        text = page.locator('#season-record').inner_text()
        print(f"  Season record: {text}")
    
    # Take screenshot
    print("\n📸 Taking screenshot...")
    page.screenshot(path='home_badges_NOW.png', full_page=True)
    print("  Saved: home_badges_NOW.png")
    
    print("\n⏸️  Keeping browser open for 8 seconds...")
    time.sleep(8)
    browser.close()
    
    print("\n✅ TEST COMPLETE")

