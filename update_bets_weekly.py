#!/usr/bin/env python3
"""
Weekly Bet Update Script
Run this each week to:
1. Update bet statuses (Won/Lost/Pending)
2. Fetch any new bets you placed
3. Update your P&L

Usage:
    python3 update_bets_weekly.py
    
This will open a browser, you log in, navigate to bet history, then it auto-extracts everything.
"""
from playwright.sync_api import sync_playwright
import json
import re
import time
from pathlib import Path

def extract_bets_from_page(page):
    """Extract all bets from the current page"""
    print("📥 Extracting bet data from page...")
    
    # Scroll to load all bets
    for i in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
    
    # Get page content
    content = page.content()
    
    # Parse bets using regex
    pattern = r'Ticket Number:\s*(\d+-\d+).*?Date:(\d{2}/\d{2}/\d{4}).*?Description:(.*?)Type:(.*?)Status(Pending|Won|Lost).*?Amount\$(\d+\.\d+).*?To win\$(\d+\.\d+)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    bets = []
    seen_tickets = set()
    
    for match in matches:
        ticket_id, date, desc_raw, type_raw, status, amount, to_win = match
        
        if ticket_id in seen_tickets:
            continue
        seen_tickets.add(ticket_id)
        
        # Clean description and preserve parlay legs
        description = desc_raw.strip()
        description = re.sub(r'\s+', ' ', description)
        
        # Extract parlay legs
        if 'Desktop - FOOTBALL' in description or 'Mobile - FOOTBALL' in description:
            legs = re.findall(r'(Desktop|Mobile) - FOOTBALL[^DM]*', description)
            if len(legs) > 1:
                description = ' | '.join([leg.strip() for leg in legs if leg.strip()])
        
        description = description[:800]
        
        # Determine bet type
        bet_type = type_raw.strip()
        if not bet_type:
            if 'Parlay' in description or 'Parlay' in desc_raw:
                bet_type = 'Parlay'
            elif 'Same Game' in description:
                bet_type = 'Same Game Parlay'
            elif 'Spread' in description:
                bet_type = 'Spread'
            else:
                bet_type = 'Straight'
        
        bets.append({
            'ticket_id': ticket_id,
            'date': date,
            'description': description,
            'type': bet_type,
            'status': status,
            'amount': float(amount),
            'to_win': float(to_win)
        })
    
    return bets

def calculate_summary(bets):
    """Calculate summary statistics"""
    won_bets = [b for b in bets if b['status'] == 'Won']
    lost_bets = [b for b in bets if b['status'] == 'Lost']
    pending_bets = [b for b in bets if b['status'] == 'Pending']
    
    total_amount = sum(b['amount'] for b in bets)
    pending_amount = sum(b['amount'] for b in pending_bets)
    potential_win = sum(b['to_win'] for b in pending_bets)
    
    won_profit = sum(b['to_win'] for b in won_bets)
    lost_loss = sum(b['amount'] for b in lost_bets)
    total_profit = won_profit - lost_loss
    
    return {
        'total_bets': len(bets),
        'pending': len(pending_bets),
        'won': len(won_bets),
        'lost': len(lost_bets),
        'total_risked': f'${total_amount:.2f}',
        'total_to_win': f'${potential_win:.2f}',
        'total_profit': total_profit,
        'total_amount': total_amount,
        'pending_amount': pending_amount,
        'potential_win': potential_win,
        'won_count': len(won_bets),
        'lost_count': len(lost_bets),
        'pending_count': len(pending_bets),
        'win_rate': (len(won_bets) / (len(won_bets) + len(lost_bets)) * 100) if (len(won_bets) + len(lost_bets)) > 0 else 0
    }

def main():
    print("🎰 Weekly Bet Update Script")
    print("=" * 60)
    
    # Check if we have existing bets
    bets_file = Path("artifacts/betonline_bets.json")
    old_bets = []
    if bets_file.exists():
        with open(bets_file, 'r') as f:
            data = json.load(f)
            old_bets = data.get('bets', [])
        print(f"📊 Found {len(old_bets)} existing bets")
    
    print("\n🌐 Opening browser...")
    print("   You'll need to:")
    print("   1. Log in to BetOnline")
    print("   2. Navigate to 'Bet History' or 'My Bets'")
    print("   3. Wait 5 seconds for the script to extract data")
    print("\n   Browser will open in 3 seconds...")
    time.sleep(3)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.goto('https://www.betonline.ag/sportsbook/my-account')
        
        print("\n⏳ Waiting 60 seconds for you to log in and navigate to bet history...")
        print("   (Script will auto-extract after 60 seconds)")
        time.sleep(60)
        
        # Extract bets
        bets = extract_bets_from_page(page)
        
        browser.close()
    
    print(f"\n✅ Extracted {len(bets)} bets from BetOnline")
    
    # Calculate summary
    summary = calculate_summary(bets)
    
    print("\n📊 Summary:")
    print(f"   Total bets: {summary['total_bets']}")
    print(f"   Pending: {summary['pending']} (${summary['pending_amount']:.2f})")
    print(f"   Won: {summary['won']} (+${sum(b['to_win'] for b in bets if b['status']=='Won'):.2f})")
    print(f"   Lost: {summary['lost']} (-${sum(b['amount'] for b in bets if b['status']=='Lost'):.2f})")
    print(f"   Total P/L: ${summary['total_profit']:.2f}")
    
    # Compare with old data
    if old_bets:
        old_summary = calculate_summary(old_bets)
        print("\n📈 Changes since last update:")
        print(f"   New bets: +{summary['total_bets'] - old_summary['total_bets']}")
        print(f"   Status changes: {abs(summary['pending'] - old_summary['pending'])} bets settled")
        print(f"   P/L change: ${summary['total_profit'] - old_summary['total_profit']:.2f}")
    
    # Save to JSON
    output = {
        'bets': bets,
        'summary': summary,
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('artifacts/betonline_bets.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n✅ Saved to artifacts/betonline_bets.json")
    print("🔄 Refresh http://localhost:9876/bets to see updates!")

if __name__ == '__main__':
    main()

