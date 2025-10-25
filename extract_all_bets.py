#!/usr/bin/env python3
"""
Extract ALL bets from BetOnline by scrolling through the entire bet history
"""
from playwright.sync_api import sync_playwright
import json
import time

print("🚀 BetOnline Complete Bet Extractor")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("🌐 Opening BetOnline...")
    page.goto('https://www.betonline.ag/sportsbook/my-account')
    
    print("\n⏳ Please:")
    print("   1. Log in to BetOnline")
    print("   2. Navigate to 'Bet History' or 'My Bets'")
    print("   3. Make sure you can see your bets on screen")
    print("   4. Press ENTER when ready...")
    
    input()
    
    print("\n📜 Scrolling to load ALL bets...")
    
    # Scroll to bottom multiple times to load all bets
    for i in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        print(f"   Scroll {i+1}/10...")
    
    print("\n📥 Extracting ALL bet data from page...")
    
    # Get the entire page HTML
    html_content = page.content()
    
    # Save raw HTML for inspection
    with open('betonline_page.html', 'w') as f:
        f.write(html_content)
    print("   💾 Saved raw HTML to betonline_page.html")
    
    # Try to extract bets using JavaScript
    bets_data = page.evaluate('''() => {
        const bets = [];
        
        // Look for all possible bet containers
        const selectors = [
            'tr',
            '[class*="bet"]',
            '[class*="wager"]',
            '[class*="ticket"]',
            '.table-row',
            '[data-ticket]'
        ];
        
        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(element => {
                const text = element.textContent || '';
                
                // Look for ticket numbers (format: 123456789-1)
                const ticketMatch = text.match(/(\\d{9}-\\d+)/);
                if (ticketMatch) {
                    // Try to extract all data from this element
                    const allText = text.replace(/\\s+/g, ' ').trim();
                    
                    bets.push({
                        ticket_id: ticketMatch[1],
                        raw_text: allText.substring(0, 500)
                    });
                }
            });
        });
        
        return bets;
    }''')
    
    print(f"\n✅ Found {len(bets_data)} bet entries")
    
    # Save raw data
    with open('extracted_bets_raw_new.json', 'w') as f:
        json.dump(bets_data, f, indent=2)
    
    print(f"💾 Saved raw data to extracted_bets_raw_new.json")
    
    print("\n📊 Now parsing the data...")
    
    browser.close()

print("\n✅ Done! Check extracted_bets_raw_new.json")
print("   Run parse script next to convert to proper format")

