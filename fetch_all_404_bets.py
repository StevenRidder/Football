#!/usr/bin/env python3
"""
Fetch ALL 404 bets from BetOnline using Playwright.
This script will open a browser, wait for you to log in,
then automatically scroll and extract ALL bet data.
"""

from playwright.sync_api import sync_playwright
import json
import time

def fetch_all_bets():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to BetOnline
        print("Opening BetOnline...")
        page.goto('https://www.betonline.ag')
        
        # Wait for user to log in and navigate to bet history
        print("\n" + "="*70)
        print("PLEASE:")
        print("  1. Log in to BetOnline")
        print("  2. Navigate to: My Account → Bet History")
        print("  3. Wait for the page to load")
        print("="*70)
        print("\nWaiting 60 seconds for you to log in and navigate...")
        time.sleep(60)
        
        # Capture API responses
        all_responses = []
        
        def handle_response(response):
            if 'get-bet-history' in response.url:
                try:
                    data = response.json()
                    all_responses.append(data)
                    print(f"  ✓ Captured API response: {len(data.get('Data', []))} bets")
                except:
                    pass
        
        page.on('response', handle_response)
        
        # Scroll to top first
        print("\n1. Scrolling to TOP to load first 100 bets...")
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(3)
        
        # Scroll to bottom to trigger all API calls
        print("2. Scrolling to BOTTOM to load all remaining bets...")
        
        # Get initial height
        last_height = page.evaluate("document.body.scrollHeight")
        
        while True:
            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            # Calculate new height
            new_height = page.evaluate("document.body.scrollHeight")
            
            if new_height == last_height:
                # No more content, try one more time
                print("   Reached bottom, waiting for final load...")
                time.sleep(3)
                break
            
            last_height = new_height
            print(f"   Scrolled... (height: {new_height})")
        
        # Wait for any final API calls
        print("3. Waiting for final API calls...")
        time.sleep(5)
        
        # Collect all unique bets
        all_bets = {}
        for response in all_responses:
            for bet in response.get('Data', []):
                bet_id = bet['Id']
                if bet_id not in all_bets:
                    all_bets[bet_id] = bet
        
        print(f"\n{'='*70}")
        print(f"EXTRACTION COMPLETE!")
        print(f"{'='*70}")
        print(f"Total API responses captured: {len(all_responses)}")
        print(f"Total unique bets: {len(all_bets)}")
        
        # Calculate totals
        pending_bets = [bet for bet in all_bets.values() if bet['WagerStatus'] == 'Pending']
        pending_total = sum(float(bet['Risk']) for bet in pending_bets)
        
        print(f"Pending bets: {len(pending_bets)}")
        print(f"Pending total: ${pending_total:.2f}")
        print(f"Target: $561.33")
        
        if abs(pending_total - 561.33) < 0.01:
            print("\n✅ PERFECT MATCH!")
        else:
            print(f"\n⚠️  Difference: ${abs(pending_total - 561.33):.2f}")
        
        # Save to file
        output_file = '/Users/steveridder/Git/Football/artifacts/all_404_bets.json'
        with open(output_file, 'w') as f:
            json.dump(list(all_bets.values()), f, indent=2)
        
        print(f"\n✓ Saved to: {output_file}")
        
        browser.close()
        return list(all_bets.values())

if __name__ == "__main__":
    fetch_all_bets()

