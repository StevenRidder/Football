#!/usr/bin/env python3
"""
Test script to verify bet parsing logic
"""
import re

def simulate_parse_bet_online_data(text):
    """Simulate the JavaScript parseBetOnlineData function"""
    # Split by lines
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Check if ticket pattern exists
    has_ticket_pattern = bool(re.search(r'\d{9}-\d+', text))
    
    if has_ticket_pattern:
        print("✓ Detected ticket ID pattern, trying parseTableFormat...")
        # Simulate parseTableFormat
        result = simulate_parse_table_format(text)
        print(f"✓ parseTableFormat found {len(result)} bets")
        
        if result and len(result) > 0:
            first = result[0]
            if first['amount'] > 0 and first['description'] and len(first['description']) > 0:
                print("✓ Returning parseTableFormat results (valid)")
                return result
            else:
                print("✗ parseTableFormat returned invalid bets")
        else:
            print("✗ parseTableFormat returned empty")
    
    return []

def simulate_parse_table_format(text):
    """Simulate the JavaScript parseTableFormat function"""
    bets = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Remove header lines
    data_lines = [l for l in lines if not any(h in l for h in ['Ticket #', 'Date', 'Description', 'Type', 'Status', 'Amount', 'To Win'])]
    
    # Check if vertical format
    first_line = data_lines[0].strip() if data_lines else ''
    is_vertical = bool(re.match(r'^\d{9}-\d+$', first_line))
    
    if is_vertical:
        print("  Detected vertical format (7 lines per bet)")
        i = 0
        while i < len(data_lines):
            # Skip empty
            if not data_lines[i] or not data_lines[i].strip():
                i += 1
                continue
            
            trimmed = data_lines[i].strip()
            if not re.match(r'^\d{9}-\d+$', trimmed):
                i += 1
                continue
            
            if i + 6 >= len(data_lines):
                break
            
            ticket_id = trimmed
            date = data_lines[i + 1].strip() if i + 1 < len(data_lines) else ''
            description = data_lines[i + 2].strip() if i + 2 < len(data_lines) else ''
            bet_type = data_lines[i + 3].strip() if i + 3 < len(data_lines) else ''
            status = data_lines[i + 4].strip() if i + 4 < len(data_lines) else ''
            amount_str = data_lines[i + 5].replace('$', '').replace(',', '').strip() if i + 5 < len(data_lines) else ''
            to_win_str = data_lines[i + 6].replace('$', '').replace(',', '').strip() if i + 6 < len(data_lines) else ''
            
            amount = float(amount_str) if amount_str else 0
            to_win = float(to_win_str) if to_win_str else 0
            
            bets.append({
                'ticket_id': ticket_id,
                'date': date,
                'description': description,
                'bet_type': bet_type,
                'status': status,
                'amount': amount,
                'to_win': to_win
            })
            
            i += 7
    
    return bets

# Test with actual bet data
test_data = """ 909509859-14

11/04/2025

FOOTBALL - 109 Las Vegas Raiders +9 -110

Spread

Pending

$50.00

$45.45

 909509859-13

11/04/2025

FOOTBALL - 274 Los Angeles Chargers -2½ -125

Spread

Pending

$50.00

$40.00"""

print("=" * 60)
print("TESTING BET PARSER")
print("=" * 60)
print()

result = simulate_parse_bet_online_data(test_data)

print()
print("=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Total bets parsed: {len(result)}")
print()

for i, bet in enumerate(result, 1):
    print(f"Bet {i}:")
    print(f"  Ticket ID: {bet['ticket_id']}")
    print(f"  Date: {bet['date']}")
    print(f"  Description: {bet['description'][:60]}...")
    print(f"  Type: {bet['bet_type']}")
    print(f"  Status: {bet['status']}")
    print(f"  Amount: ${bet['amount']:.2f}")
    print(f"  To Win: ${bet['to_win']:.2f}")
    print(f"  Valid: {bet['amount'] > 0 and len(bet['description']) > 0}")
    print()

if len(result) == 2 and all(b['amount'] > 0 and len(b['description']) > 0 for b in result):
    print("✅ TEST PASSED - All bets parsed correctly!")
else:
    print("❌ TEST FAILED - Bets not parsed correctly")

