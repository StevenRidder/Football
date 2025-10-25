#!/usr/bin/env python3
"""
Automatically fetch all bets from BetOnline using Playwright browser automation.
Run this script weekly to update your bet tracking.

Usage:
    python3 fetch_bets_from_browser.py

The script will:
1. Open a browser window to BetOnline
2. Wait for you to log in (if needed)
3. Navigate to your bet history
4. Extract all bet data
5. Save it to artifacts/betonline_bets.json
"""
import json
import re
import os
import sys
import time
from playwright.sync_api import sync_playwright

def extract_bets_from_page(page):
    """Extract all bet data from the current page using JavaScript."""
    print("📊 Extracting bet data from page...")
    
    result = page.evaluate("""
        () => {
            const bets = [];
            
            // Find all bet rows
            const betRows = document.querySelectorAll('[class*="bet"], [class*="row"]');
            
            for (const row of betRows) {
                const text = row.textContent;
                
                // Look for ticket numbers (9-digit numbers followed by -1)
                const ticketMatch = text.match(/(\\d{9}-\\d+)/);
                if (ticketMatch) {
                    // Extract all text from this row
                    const fullText = text.replace(/\\s+/g, ' ').trim();
                    bets.push(fullText);
                }
            }
            
            return { count: bets.length, all: bets.join('\\n---\\n') };
        }
    """)
    
    return result

def parse_bet_entries(all_text):
    """Parse the extracted text into structured bet data."""
    print("🔍 Parsing bet entries...")
    
    bet_entries = all_text.split('---')
    parsed_bets = []
    
    for entry in bet_entries:
        entry = entry.strip()
        if not entry or len(entry) < 50:
            continue
        
        # Look for "Ticket Number:" pattern
        ticket_match = re.search(r'Ticket Number:\s*(\d{9}-\d+)', entry)
        if not ticket_match:
            continue
        
        ticket = ticket_match.group(1)
        
        # Extract date
        date_match = re.search(r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})', entry)
        date = date_match.group(1) if date_match else ''
        
        # Extract type
        type_match = re.search(r'Type:\s*([^\n]+)', entry)
        bet_type = type_match.group(1).strip() if type_match else ''
        
        # Extract status
        status_match = re.search(r'Status\s*([A-Za-z]+)', entry)
        status = status_match.group(1) if status_match else 'Pending'
        
        # Extract amount
        amount_match = re.search(r'Amount\s*\$?([\d,]+\.?\d*)', entry)
        amount = f"${amount_match.group(1)}" if amount_match else ''
        
        # Extract to win
        to_win_match = re.search(r'To win\s*\$?([\d,]+\.?\d*)', entry)
        to_win = f"${to_win_match.group(1)}" if to_win_match else ''
        
        # Extract description
        desc_match = re.search(r'Description:\s*([^\n]+(?:\n(?!Type:|Status|Amount|To win)[^\n]+)*)', entry, re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip()
            description = re.sub(r'\s+', ' ', description)
            description = description.replace('Desktop - ', '')
        else:
            lines = entry.split('\n')
            description = ''
            for line in lines:
                if 'FOOTBALL' in line or 'Parlay' in line:
                    description = line.strip()
                    break
        
        # Limit description length
        if len(description) > 300:
            description = description[:300] + '...'
        
        parsed_bets.append({
            'ticket': ticket,
            'date': date,
            'description': description,
            'type': bet_type,
            'status': status,
            'amount': amount,
            'to_win': to_win
        })
    
    # Remove duplicates based on ticket number
    seen_tickets = set()
    unique_bets = []
    for bet in parsed_bets:
        if bet['ticket'] not in seen_tickets:
            seen_tickets.add(bet['ticket'])
            unique_bets.append(bet)
    
    return unique_bets

def calculate_summary(bets):
    """Calculate summary statistics."""
    def parse_amount(amt_str):
        if not amt_str or amt_str == '-':
            return 0.0
        return float(amt_str.replace('$', '').replace(',', ''))
    
    total_pending = sum(1 for b in bets if b['status'] == 'Pending')
    total_won = sum(1 for b in bets if b['status'] == 'Won')
    total_lost = sum(1 for b in bets if b['status'] == 'Lost')
    
    total_risked = sum(parse_amount(b['amount']) for b in bets if b['status'] == 'Pending')
    total_to_win = sum(parse_amount(b['to_win']) for b in bets if b['status'] == 'Pending')
    
    return {
        'total_bets': len(bets),
        'pending': total_pending,
        'won': total_won,
        'lost': total_lost,
        'total_risked': f"${total_risked:.2f}",
        'total_to_win': f"${total_to_win:.2f}"
    }

def main():
    print("🚀 BetOnline Bet Fetcher")
    print("=" * 50)
    
    with sync_playwright() as p:
        # Launch browser (visible so you can log in if needed)
        print("🌐 Opening browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to BetOnline bet history
        print("📍 Navigating to BetOnline...")
        page.goto('https://www.betonline.ag/my-account/pending-bets')
        
        # Wait for user to log in if needed
        print("\n⏳ Waiting for page to load...")
        print("   If you need to log in, please do so now.")
        print("   Once you see your bets, press Enter to continue...")
        input()
        
        # Extract bets
        result = extract_bets_from_page(page)
        print(f"✅ Found {result['count']} bet entries")
        
        # Parse bets
        bets = parse_bet_entries(result['all'])
        print(f"✅ Parsed {len(bets)} unique bets")
        
        # Calculate summary
        summary = calculate_summary(bets)
        
        # Save to JSON
        os.makedirs('artifacts', exist_ok=True)
        output = {
            'bets': bets,
            'summary': summary
        }
        
        with open('artifacts/betonline_bets.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print("\n" + "=" * 50)
        print("✅ Successfully loaded bets!")
        print(f"📊 Summary:")
        print(f"   Total Bets: {summary['total_bets']}")
        print(f"   Pending: {summary['pending']}")
        print(f"   Won: {summary['won']}")
        print(f"   Lost: {summary['lost']}")
        print(f"   Total Risked: {summary['total_risked']}")
        print(f"   Total To Win: {summary['total_to_win']}")
        print(f"\n💾 Saved to artifacts/betonline_bets.json")
        print(f"🌐 View at: http://localhost:9876/bets")
        
        # Close browser
        browser.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

