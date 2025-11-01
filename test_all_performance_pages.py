#!/usr/bin/env python3
"""
Comprehensive Playwright test for all performance pages
"""
from playwright.sync_api import sync_playwright
import sys

def test_performance_pages():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("="*60)
        print("TESTING NFL EDGE PERFORMANCE PAGES")
        print("="*60)
        
        # Test 1: /performance - Betting Performance Analytics
        print("\n📊 Test 1: /performance (Betting Performance)")
        response = page.goto('http://localhost:9876/performance')
        assert response.status == 200
        print("  ✓ Page loaded (200)")
        
        # Check for data
        assert page.locator('text=Total Profit/Loss').first.is_visible()
        profit = page.locator('.h1').first.inner_text()
        print(f"  ✓ Total Profit/Loss: {profit}")
        
        assert page.locator('text=/ROI/').first.is_visible()
        print("  ✓ ROI card present")
        
        assert page.locator('#chart-pl-by-week').is_visible()
        print("  ✓ Weekly P/L chart present")
        
        assert page.locator('#chart-bet-types').is_visible()
        print("  ✓ Bet types chart present")
        
        assert page.locator('text=Performance by Bet Type').first.is_visible()
        print("  ✓ Performance by Bet Type table present")
        
        assert page.locator('text=Recent Settled Bets').first.is_visible()
        print("  ✓ Recent Settled Bets table present")
        
        # Test 2: /model-performance - Model Performance by Conviction
        print("\n📈 Test 2: /model-performance (Model Backtest Performance)")
        response = page.goto('http://localhost:9876/model-performance')
        assert response.status == 200
        print("  ✓ Page loaded (200)")
        
        # Check for data
        assert page.locator('text=Model Performance by Conviction').first.is_visible()
        print("  ✓ Main heading present")
        
        assert page.locator('text=SPREAD BETS').first.is_visible()
        print("  ✓ Spread Bets section present")
        
        assert page.locator('text=TOTAL (O/U) BETS').first.is_visible()
        print("  ✓ Total Bets section present")
        
        # Check for conviction levels
        high_badges = page.locator('.badge.bg-red', has_text='HIGH')
        assert high_badges.count() >= 2  # At least one for spread, one for total
        print(f"  ✓ HIGH conviction badges found: {high_badges.count()}")
        
        medium_badges = page.locator('.badge.bg-orange', has_text='MEDIUM')
        assert medium_badges.count() >= 2
        print(f"  ✓ MEDIUM conviction badges found: {medium_badges.count()}")
        
        low_badges = page.locator('.badge.bg-secondary', has_text='LOW')
        assert low_badges.count() >= 2
        print(f"  ✓ LOW conviction badges found: {low_badges.count()}")
        
        # Test 3: Test a detail page link (spread/high)
        print("\n🔍 Test 3: /model-performance/spread/high (Detail Page)")
        spread_high_link = page.locator('a[href="/model-performance/spread/high"]').first
        assert spread_high_link.is_visible()
        spread_high_link.click()
        page.wait_for_load_state('networkidle')
        
        assert 'spread/high' in page.url
        print(f"  ✓ Navigated to detail page: {page.url}")
        
        assert page.locator('text=/Spread Bets/').first.is_visible()
        print("  ✓ Spread Bets detail page loaded")
        
        assert page.locator('.badge', has_text='HIGH').first.is_visible()
        print("  ✓ HIGH conviction badge present")
        
        # Check for data table
        assert page.locator('table').first.is_visible()
        print("  ✓ Data table present")
        
        # Test 4: Test navigation
        print("\n🧭 Test 4: Navigation Test")
        page.goto('http://localhost:9876/performance')
        page.wait_for_load_state('networkidle')
        
        # Check nav links
        nav_performance = page.locator('a.nav-link[href="/performance"]').first
        assert nav_performance.is_visible()
        nav_class = nav_performance.get_attribute('class') or ''
        if 'active' in nav_class:
            print("  ✓ Performance nav link is active")
        else:
            print("  ✓ Performance nav link is visible")
        
        # Navigate to model performance via button
        model_perf_button = page.locator('a[href="/model-performance"]').first
        if model_perf_button.is_visible():
            model_perf_button.click()
            page.wait_for_load_state('networkidle')
            assert 'model-performance' in page.url
            print("  ✓ Navigation to Model Performance works")
        
        browser.close()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nSummary:")
        print("  • /performance - Working with data ✓")
        print("  • /model-performance - Working with data ✓")
        print("  • Detail pages - Working ✓")
        print("  • Navigation - Working ✓")
        print()
        return True

if __name__ == '__main__':
    try:
        success = test_performance_pages()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

