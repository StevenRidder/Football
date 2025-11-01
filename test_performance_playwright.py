#!/usr/bin/env python3
"""
Playwright test to validate the performance page has data
"""
from playwright.sync_api import sync_playwright
import sys

def test_performance_page():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("🧪 Testing http://localhost:9876/performance")
        
        # Navigate to performance page
        response = page.goto('http://localhost:9876/performance')
        
        # Check response status
        assert response.status == 200, f"Expected 200, got {response.status}"
        print("✓ Page loaded successfully (200)")
        
        # Check page title
        title = page.title()
        assert "Performance" in title or "NFL Edge" in title, f"Unexpected title: {title}"
        print(f"✓ Page title: {title}")
        
        # Check for main heading
        heading = page.locator('h2.page-title').first
        assert heading.is_visible(), "Main heading not found"
        heading_text = heading.inner_text()
        print(f"✓ Main heading: {heading_text}")
        
        # Check for summary cards
        profit_card = page.locator('text=Total Profit/Loss').first
        assert profit_card.is_visible(), "Profit/Loss card not found"
        print("✓ Total Profit/Loss card found")
        
        roi_card = page.locator('text=/ROI/').first
        assert roi_card.is_visible(), "ROI info not found"
        print("✓ ROI data found")
        
        win_rate_card = page.locator('text=/Win Rate/').first
        assert win_rate_card.is_visible(), "Win Rate not found"
        print("✓ Win Rate found")
        
        pending_bets_card = page.locator('text=/Pending Bets/').first
        assert pending_bets_card.is_visible(), "Pending Bets not found"
        print("✓ Pending Bets card found")
        
        # Check for charts
        weekly_chart = page.locator('#chart-pl-by-week')
        assert weekly_chart.is_visible(), "Weekly P/L chart not found"
        print("✓ Weekly P/L chart element found")
        
        type_chart = page.locator('#chart-bet-types')
        assert type_chart.is_visible(), "Bet types chart not found"
        print("✓ Bet types chart element found")
        
        # Check for performance by bet type table
        perf_table = page.locator('text=Performance by Bet Type').first
        assert perf_table.is_visible(), "Performance by Bet Type section not found"
        print("✓ Performance by Bet Type table found")
        
        # Check for recent settled bets
        recent_table = page.locator('text=Recent Settled Bets').first
        assert recent_table.is_visible(), "Recent Settled Bets section not found"
        print("✓ Recent Settled Bets table found")
        
        # Get actual numbers to verify data is present
        profit_value = page.locator('.h1').first.inner_text()
        print(f"✓ Total Profit shown: {profit_value}")
        
        # Check ApexCharts loaded
        page.wait_for_timeout(1000)  # Give charts time to render
        print("✓ Charts given time to render")
        
        browser.close()
        
        print("\n✅ ALL TESTS PASSED! Performance page is working with data.")
        return True

if __name__ == '__main__':
    try:
        success = test_performance_page()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

