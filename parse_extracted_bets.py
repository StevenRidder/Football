#!/usr/bin/env python3
"""
Parse extracted bet data from BetOnline and format it for our system.
"""
import json
import re

# Read the raw extracted data
with open('/Users/steveridder/.cursor/browser-logs/browser_evaluate-2025-10-25T21-43-41-393Z.log', 'r') as f:
    content = f.read()

# Extract the JSON result
try:
    # Find the JSON object in the log
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    data = json.loads(content[json_start:json_end])
    
    all_text = data.get('all', '')
    bet_entries = all_text.split('---')
    
    print(f"Found {len(bet_entries)} bet entries")
    
    # Parse each bet entry
    parsed_bets = []
    for entry in bet_entries:
        entry = entry.strip()
        if not entry:
            continue
            
        # Look for ticket number
        ticket_match = re.search(r'(\d{9}-\d+)', entry)
        if not ticket_match:
            continue
            
        ticket = ticket_match.group(1)
        
        # Try to extract date (MM/DD/YYYY format)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', entry)
        date = date_match.group(1) if date_match else ''
        
        # Try to extract amounts ($X.XX format)
        amounts = re.findall(r'\$[\d,]+\.?\d*', entry)
        amount = amounts[0] if len(amounts) > 0 else ''
        to_win = amounts[1] if len(amounts) > 1 else ''
        
        # Try to identify bet type
        bet_type = ''
        if 'Parlay' in entry:
            # Extract parlay team count
            parlay_match = re.search(r'Parlay \((\d+) Teams?\)', entry)
            if parlay_match:
                bet_type = f"Parlay ({parlay_match.group(1)} Teams)"
            else:
                bet_type = 'Parlay'
        elif 'Same Game Parlay' in entry:
            bet_type = 'Same Game Parlay'
        elif 'Spread' in entry:
            bet_type = 'Spread'
        elif 'Total' in entry or 'Over' in entry or 'Under' in entry:
            bet_type = 'Total'
        elif 'Money' in entry or 'Moneyline' in entry:
            bet_type = 'Money Line'
        else:
            bet_type = 'Other'
        
        # Try to identify status
        status = 'Pending'
        if 'Won' in entry:
            status = 'Won'
        elif 'Lost' in entry:
            status = 'Lost'
        elif 'Cancelled' in entry:
            status = 'Cancelled'
        
        # Extract description (everything between ticket and type/status)
        # This is tricky - let's just take a reasonable chunk
        desc_start = entry.find(ticket) + len(ticket)
        desc_end = len(entry)
        description = entry[desc_start:desc_end].strip()
        
        # Clean up description - remove amounts and status
        for amt in amounts:
            description = description.replace(amt, '')
        description = description.replace('Pending', '').replace('Won', '').replace('Lost', '').strip()
        
        # Limit description length
        if len(description) > 200:
            description = description[:200] + '...'
        
        parsed_bets.append({
            'ticket': ticket,
            'date': date,
            'description': description,
            'type': bet_type,
            'status': status,
            'amount': amount,
            'to_win': to_win
        })
    
    # Save to JSON
    with open('artifacts/betonline_bets_extracted.json', 'w') as f:
        json.dump({
            'bets': parsed_bets,
            'total_bets': len(parsed_bets),
            'summary': {
                'total_pending': sum(1 for b in parsed_bets if b['status'] == 'Pending'),
                'total_won': sum(1 for b in parsed_bets if b['status'] == 'Won'),
                'total_lost': sum(1 for b in parsed_bets if b['status'] == 'Lost'),
            }
        }, f, indent=2)
    
    print(f"\nParsed {len(parsed_bets)} bets successfully!")
    print("Saved to artifacts/betonline_bets_extracted.json")
    
    # Show first 5 bets
    print("\nFirst 5 bets:")
    for bet in parsed_bets[:5]:
        print(f"  {bet['ticket']} | {bet['date']} | {bet['type']} | {bet['status']} | {bet['amount']} -> {bet['to_win']}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

