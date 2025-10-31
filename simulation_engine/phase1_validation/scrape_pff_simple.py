"""
Simple PFF Scraper - Extract data from the visible table

This extracts all team data from the PFF teams page that's already visible.
No need for popups - the data is right there in the table!

Usage:
    python3 scrape_pff_simple.py
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
    
    page.goto("https://auth.pff.com/")
    time.sleep(2)
    
    # Fill in credentials
    page.fill('input[type="email"]', PFF_EMAIL)
    page.fill('input[type="password"]', PFF_PASSWORD)
    
    # Click sign in
    page.click('button:has-text("Sign In")')
    
    # Wait for login to complete
    time.sleep(5)
    
    print("✅ Logged in successfully")


def scrape_team_table(page, season=2024):
    """Scrape the entire team table from the page."""
    print(f"\n📊 Scraping team data for {season}...")
    
    # Navigate to team stats
    url = f"https://premium.pff.com/nfl/teams/{season}/REGPO"
    page.goto(url)
    time.sleep(5)
    
    # Scroll down to ensure all teams are loaded
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    
    # Extract the entire table
    data = page.evaluate("""
        () => {
            // Get all rows
            const rows = Array.from(document.querySelectorAll('[role="row"]'));
            
            // Get headers from first row
            const headerRow = rows[0];
            const headerCells = Array.from(headerRow.querySelectorAll('[role="columnheader"]'));
            const headers = headerCells.map(cell => {
                const text = cell.textContent.trim();
                return text || 'BLANK';
            });
            
            console.log('Headers:', headers);
            
            // Get data from remaining rows
            const teamData = [];
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const cells = Array.from(row.querySelectorAll('[role="gridcell"]'));
                
                if (cells.length > 0) {
                    const rowData = {};
                    cells.forEach((cell, idx) => {
                        if (idx < headers.length) {
                            rowData[headers[idx]] = cell.textContent.trim();
                        }
                    });
                    
                    // Only add if we have a team name
                    if (rowData['Team'] && rowData['Team'] !== '') {
                        teamData.push(rowData);
                    }
                }
            }
            
            return {
                headers: headers,
                data: teamData
            };
        }
    """)
    
    print(f"   Found {len(data['data'])} teams")
    print(f"   Columns: {data['headers']}")
    
    return data


def scrape_qb_stats(page, season=2024):
    """Scrape QB stats including pressure data."""
    print(f"\n📊 Scraping QB data for {season}...")
    
    # Navigate to QB stats
    url = f"https://premium.pff.com/nfl/players/{season}/REGPO?position=QB"
    page.goto(url)
    time.sleep(5)
    
    # Scroll to load all QBs
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    
    # Extract QB table
    data = page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('[role="row"]'));
            
            // Get headers
            const headerRow = rows[0];
            const headerCells = Array.from(headerRow.querySelectorAll('[role="columnheader"]'));
            const headers = headerCells.map(cell => cell.textContent.trim() || 'BLANK');
            
            // Get QB data
            const qbData = [];
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const cells = Array.from(row.querySelectorAll('[role="gridcell"]'));
                
                if (cells.length > 0) {
                    const rowData = {};
                    cells.forEach((cell, idx) => {
                        if (idx < headers.length) {
                            rowData[headers[idx]] = cell.textContent.trim();
                        }
                    });
                    
                    // Only add if we have a player name
                    if (rowData['Player'] || rowData['Name']) {
                        qbData.push(rowData);
                    }
                }
            }
            
            return {
                headers: headers,
                data: qbData
            };
        }
    """)
    
    print(f"   Found {len(data['data'])} QBs")
    print(f"   Columns: {data['headers']}")
    
    return data


def main():
    """Main scraper execution."""
    print("="*80)
    print("PFF SIMPLE SCRAPER - EXTRACT TABLE DATA")
    print("="*80)
    
    with sync_playwright() as p:
        # Launch browser (visible so you can see what's happening)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Login
            login_to_pff(page)
            
            # Scrape 2024 team data
            team_data_2024 = scrape_team_table(page, 2024)
            
            # Save team data
            if team_data_2024['data']:
                df = pd.DataFrame(team_data_2024['data'])
                output_path = PFF_RAW_DIR / "pff_team_grades_2024.csv"
                df.to_csv(output_path, index=False)
                print(f"\n✅ Saved team data: {output_path}")
                print(f"   Shape: {df.shape}")
                print(f"   Columns: {list(df.columns)}")
                
                # Show sample
                print(f"\n📋 Sample data:")
                print(df[['Team', 'PBLK', 'PRSH']].head() if 'PBLK' in df.columns else df.head())
            
            # Scrape 2024 QB data
            qb_data_2024 = scrape_qb_stats(page, 2024)
            
            # Save QB data
            if qb_data_2024['data']:
                df = pd.DataFrame(qb_data_2024['data'])
                output_path = PFF_RAW_DIR / "pff_qb_stats_2024.csv"
                df.to_csv(output_path, index=False)
                print(f"\n✅ Saved QB data: {output_path}")
                print(f"   Shape: {df.shape}")
                print(f"   Columns: {list(df.columns)}")
            
            # Optional: Scrape 2022-2023
            print("\n" + "="*80)
            print("SCRAPING COMPLETE!")
            print("="*80)
            print(f"\n📁 Files saved to: {PFF_RAW_DIR}")
            print("\n🚀 Next: Run collect_pff_data.py to process these files")
            
            # Keep browser open for 10 seconds
            time.sleep(10)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Keep browser open on error
            time.sleep(30)
        
        finally:
            browser.close()


if __name__ == "__main__":
    main()

