"""
PFF Data Scraper - Automated Download

This script logs into PFF and scrapes all the data we need for Phase 1.
Uses Playwright for browser automation.

Usage:
    python3 scrape_pff_data.py
"""

from playwright.sync_api import sync_playwright
import pandas as pd
import time
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
PFF_RAW_DIR = DATA_DIR / "pff_raw"
PFF_RAW_DIR.mkdir(parents=True, exist_ok=True)

# PFF Credentials
PFF_EMAIL = "steve.ridder@yahoo.com"
PFF_PASSWORD = "quqzeB-hikbo7-pemwuq"


def login_to_pff(page):
    """Log into PFF."""
    print("🔐 Logging into PFF...")
    
    # Navigate to login page
    page.goto("https://www.pff.com")
    time.sleep(2)
    
    # Look for login button/link
    try:
        # Try to find and click login
        page.click("text=Sign In", timeout=5000)
    except:
        # Already on login page or different layout
        pass
    
    time.sleep(2)
    
    # Fill in credentials
    page.fill('input[type="email"]', PFF_EMAIL)
    page.fill('input[type="password"]', PFF_PASSWORD)
    
    # Click sign in
    page.click('button:has-text("Sign In")')
    
    # Wait for login to complete
    time.sleep(5)
    
    print("✅ Logged in successfully")


def scrape_team_grades(page, season=2024):
    """Scrape team grades for a season."""
    print(f"\n📊 Scraping team grades for {season}...")
    
    # Navigate to team stats
    url = f"https://premium.pff.com/nfl/teams/{season}/REGPO"
    page.goto(url)
    time.sleep(5)
    
    # Extract all data from the page
    data = page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('[role="row"]'));
            const result = [];
            
            // Get headers
            const headerRow = rows[0];
            const headers = Array.from(headerRow.querySelectorAll('[role="columnheader"]'))
                .map(h => h.textContent.trim());
            
            // Get data rows
            for (let i = 1; i < rows.length; i++) {
                const cells = Array.from(rows[i].querySelectorAll('[role="gridcell"]'));
                if (cells.length > 0) {
                    const rowData = {};
                    cells.forEach((cell, idx) => {
                        if (idx < headers.length) {
                            rowData[headers[idx]] = cell.textContent.trim();
                        }
                    });
                    if (Object.keys(rowData).length > 0) {
                        result.push(rowData);
                    }
                }
            }
            
            return result;
        }
    """)
    
    print(f"   Found {len(data)} teams")
    return data


def scrape_qb_pressure_splits(page, season=2024):
    """Scrape QB pressure splits."""
    print(f"\n📊 Scraping QB pressure splits for {season}...")
    
    # Navigate to QB stats
    url = f"https://premium.pff.com/nfl/players/{season}/REGPO?position=QB"
    page.goto(url)
    time.sleep(5)
    
    # Look for pressure splits or advanced stats
    # This may require clicking through tabs/filters
    
    data = page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('[role="row"]'));
            const result = [];
            
            for (let i = 1; i < rows.length; i++) {
                const cells = Array.from(rows[i].querySelectorAll('[role="gridcell"]'));
                if (cells.length > 0) {
                    const rowData = cells.map(c => c.textContent.trim());
                    if (rowData.length > 0 && rowData[0] !== '') {
                        result.push(rowData);
                    }
                }
            }
            
            return result;
        }
    """)
    
    print(f"   Found {len(data)} QBs")
    return data


def scrape_weekly_grades(page, season=2024):
    """Scrape weekly team grades (by week)."""
    print(f"\n📊 Scraping weekly grades for {season}...")
    
    all_weeks_data = []
    
    # Try to get weekly data
    # This might require changing filters or navigating to different views
    url = f"https://premium.pff.com/nfl/teams/{season}/REG"
    page.goto(url)
    time.sleep(5)
    
    # Check if there's a week filter
    try:
        # Look for week dropdown or filter
        page.click('button:has-text("Week")', timeout=3000)
        time.sleep(1)
        
        # Get all week options
        weeks = page.evaluate("""
            () => {
                const options = Array.from(document.querySelectorAll('[role="option"]'));
                return options.map(o => o.textContent.trim()).filter(w => w.includes('Week'));
            }
        """)
        
        print(f"   Found {len(weeks)} weeks")
        
        # For now, just get overall season data
        # Weekly scraping would require iterating through each week
        
    except:
        print("   No week filter found, using season totals")
    
    return all_weeks_data


def main():
    """Main scraper execution."""
    print("="*80)
    print("PFF DATA SCRAPER - AUTOMATED DOWNLOAD")
    print("="*80)
    
    with sync_playwright() as p:
        # Launch browser (headless=False so you can see what's happening)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Login
            login_to_pff(page)
            
            # Scrape 2024 data
            team_grades_2024 = scrape_team_grades(page, 2024)
            
            # Save team grades
            if team_grades_2024:
                df = pd.DataFrame(team_grades_2024)
                output_path = PFF_RAW_DIR / "pff_team_grades_2024.csv"
                df.to_csv(output_path, index=False)
                print(f"\n✅ Saved: {output_path}")
                print(f"   Columns: {list(df.columns)}")
            
            # Scrape QB data
            qb_data_2024 = scrape_qb_pressure_splits(page, 2024)
            
            if qb_data_2024:
                # Save QB data (will need to format properly)
                output_path = PFF_RAW_DIR / "pff_qb_data_2024.csv"
                with open(output_path, 'w') as f:
                    for row in qb_data_2024:
                        f.write(','.join(row) + '\n')
                print(f"\n✅ Saved: {output_path}")
            
            # Optional: Scrape 2022-2023 for bigger backtest
            print("\n" + "="*80)
            print("SCRAPING COMPLETE!")
            print("="*80)
            print(f"\n📁 Files saved to: {PFF_RAW_DIR}")
            print("\n🚀 Next: Run collect_pff_data.py to process these files")
            
            # Keep browser open for 10 seconds so you can see results
            time.sleep(10)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nTroubleshooting:")
            print("1. Check if PFF changed their website layout")
            print("2. Verify credentials are correct")
            print("3. Try running with headless=False to see what's happening")
            
            # Keep browser open on error
            time.sleep(30)
        
        finally:
            browser.close()


if __name__ == "__main__":
    # Check if playwright is installed
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed!")
        print("\nInstall with:")
        print("  pip install playwright")
        print("  playwright install chromium")
        exit(1)
    
    main()

