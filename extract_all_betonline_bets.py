#!/usr/bin/env python3
"""
Extract ALL bets from BetOnline by controlling the browser
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def extract_all_bets():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to BetOnline login page first
        print("🌐 Navigating to BetOnline...")
        try:
            await page.goto('https://www.betonline.ag/login', timeout=60000)
        except Exception as e:
            print(f"Navigation error (might be OK): {e}")
        
        # Wait for user to log in and navigate to bet history
        print("⏳ Please log in and navigate to 'My Account' -> 'Bet History'")
        print("⏳ Waiting 60 seconds for you to do this...")
        await asyncio.sleep(60)
        
        print("📥 Extracting bet data from page...")
        
        # Try multiple methods to extract data
        all_bets = []
        
        # Method 1: Extract from table rows
        try:
            rows = await page.query_selector_all('table tbody tr')
            print(f"Found {len(rows)} table rows")
            
            for row in rows:
                text = await row.inner_text()
                if text and 'Pending' in text:
                    all_bets.append({'raw': text})
        except Exception as e:
            print(f"Table extraction failed: {e}")
        
        # Method 2: Intercept network requests
        print("🔍 Setting up network interception...")
        
        captured_bets = []
        
        async def handle_response(response):
            if 'get-bet-history' in response.url:
                try:
                    data = await response.json()
                    if data.get('Data'):
                        captured_bets.extend(data['Data'])
                        print(f"📦 Captured {len(data['Data'])} bets from API")
                except:
                    pass
        
        page.on('response', handle_response)
        
        # Scroll to trigger more API calls
        print("📜 Scrolling to load all bets...")
        for i in range(20):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
        
        # Wait for any pending requests
        await asyncio.sleep(5)
        
        print(f"✅ Captured {len(captured_bets)} bets from network!")
        
        # Save to file
        output_file = '/Users/steveridder/Git/Football/artifacts/betonline_all_bets_extracted.json'
        with open(output_file, 'w') as f:
            json.dump(captured_bets, f, indent=2)
        
        print(f"💾 Saved to: {output_file}")
        
        # Calculate summary
        pending = [b for b in captured_bets if b.get('WagerStatus') == 'Pending']
        total_stake = sum(float(b.get('Risk', 0)) for b in pending)
        total_to_win = sum(float(b.get('ToWin', 0)) for b in pending)
        
        print("=" * 60)
        print(f"Total bets: {len(captured_bets)}")
        print(f"Pending: {len(pending)}")
        print(f"Stake: ${total_stake:.2f}")
        print(f"To Win: ${total_to_win:.2f}")
        print("=" * 60)
        
        await browser.close()
        
        return captured_bets

if __name__ == '__main__':
    asyncio.run(extract_all_bets())

