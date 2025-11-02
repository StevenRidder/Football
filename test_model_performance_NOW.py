#!/usr/bin/env python3
"""Validate model-performance page with Playwright"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("\n" + "="*80)
    print("🔍 TESTING MODEL-PERFORMANCE PAGE WITH PLAYWRIGHT")
    print("="*80 + "\n")
    
    # Test model-performance page
    url = 'http://localhost:9876/model-performance'
    print(f"Loading: {url}\n")
    
    try:
        page.goto(url, wait_until='networkidle', timeout=15000)
        print("✅ Page loaded\n")
        
        # Check for badges
        print("Checking for team/betting record badges:")
        badge_count = page.locator('.badge').count()
        print(f"  Found {badge_count} badge elements\n")
        
        if badge_count > 0:
            print("Sample badges found:")
            for i in range(min(5, badge_count)):
                badge_text = page.locator('.badge').nth(i).inner_text()
                print(f"  - {badge_text}")
        else:
            print("  ❌ NO BADGES FOUND!")
        
        print("\n" + "="*80)
        print("Checking page content:")
        
        # Check for key sections
        if page.locator('text="Model Performance"').count() > 0:
            print("  ✅ Model Performance title")
        
        if page.locator('text="Spread Bets"').count() > 0:
            print("  ✅ Spread Bets section")
        
        if page.locator('text="Total Bets"').count() > 0:
            print("  ✅ Total Bets section")
        
        if page.locator('text="HIGH"').count() > 0:
            print("  ✅ HIGH conviction data")
        
        if page.locator('text="MEDIUM"').count() > 0:
            print("  ✅ MEDIUM conviction data")
        
        if page.locator('text="LOW"').count() > 0:
            print("  ✅ LOW conviction data")
        
        # Check for any tables
        tables = page.locator('table').count()
        print(f"\n  Found {tables} tables")
        
        # Take screenshot
        print("\n📸 Taking screenshot...")
        page.screenshot(path='model_performance_NOW.png', full_page=True)
        print("  Saved: model_performance_NOW.png")
        
        print("\n⏸️  Keeping browser open for 10 seconds to inspect...")
        time.sleep(10)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        browser.close()
        print("\n✅ TEST COMPLETE")

