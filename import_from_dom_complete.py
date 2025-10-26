#!/usr/bin/env python3
"""
Import complete bet data from the BetOnline DOM extraction into the database.
"""
import re
import sys
sys.path.insert(0, '/Users/steveridder/Git/Football')

from nfl_edge.bets.db import BettingDB

def parse_bets_from_text(text):
    """Parse bet data from the extracted text."""
    lines = text.split('\n')
    bets = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for ticket numbers
        if re.match(r'^\d{9}-\d+$', line):
            ticket_id = line
            
            # Next lines: date, description, type, status, amount, to_win
            if i + 6 < len(lines):
                date = lines[i + 1].strip()
                description = lines[i + 2].strip()
                bet_type = lines[i + 3].strip()
                status = lines[i + 4].strip()
                amount_line = lines[i + 5].strip()
                to_win_line = lines[i + 6].strip()
                
                # Only add if status is valid
                if status in ['Pending', 'Won', 'Lost', 'Cancelled']:
                    # Parse amount
                    amount_str = amount_line.replace('$', '').replace(',', '')
                    try:
                        amount = float(amount_str)
                    except:
                        amount = 0.0
                    
                    # Parse to_win
                    to_win_str = to_win_line.replace('$', '').replace(',', '').replace('-', '0')
                    try:
                        to_win = float(to_win_str)
                    except:
                        to_win = 0.0
                    
                    bets.append({
                        'ticket_id': ticket_id,
                        'date': date,
                        'description': description,
                        'type': bet_type,
                        'status': status,
                        'amount': amount,
                        'to_win': to_win
                    })
                    i += 7
                    continue
        i += 1
    
    return bets

def main():
    # Read the extracted data
    with open('/Users/steveridder/Git/Football/extracted_bets_complete.txt', 'r') as f:
        text = f.read()
    
    # Parse bets
    all_bets = parse_bets_from_text(text)
    print(f"Parsed {len(all_bets)} total bets")
    
    # Deduplicate by ticket_id
    unique_bets = {}
    for bet in all_bets:
        if bet['ticket_id'] not in unique_bets:
            unique_bets[bet['ticket_id']] = bet
    
    print(f"Found {len(unique_bets)} unique bets")
    
    # Calculate totals
    pending_total = sum(bet['amount'] for bet in unique_bets.values() if bet['status'] == 'Pending')
    pending_count = sum(1 for bet in unique_bets.values() if bet['status'] == 'Pending')
    
    print(f"Pending: {pending_count} bets, ${pending_total:.2f}")
    
    # Connect to database
    db = BettingDB()
    db.connect()
    
    # Clear existing data
    print("\nClearing existing database data...")
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM parlay_legs")
    cursor.execute("DELETE FROM bets")
    db.conn.commit()
    cursor.close()
    
    # Insert bets
    print("Inserting bets into database...")
    for bet in unique_bets.values():
        # Calculate profit
        profit = 0
        if bet['status'] == 'Won':
            profit = bet['to_win']
        elif bet['status'] == 'Lost':
            profit = -bet['amount']
        
        db.insert_bet({
            'ticket_id': bet['ticket_id'],
            'date': bet['date'],
            'description': bet['description'],
            'type': bet['type'],
            'status': bet['status'],
            'amount': bet['amount'],
            'to_win': bet['to_win'],
            'profit': profit
        })
    
    print(f"\n✓ Successfully imported {len(unique_bets)} bets")
    
    # Verify
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*),
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END)
        FROM bets
    """)
    result = cursor.fetchone()
    cursor.close()
    
    print("\nDatabase verification:")
    if result:
        print(f"  Result: {result}")
        print(f"  Result length: {len(result)}")
        if len(result) >= 3:
            total_bets, pending_count, pending_total = result
            print(f"  Total bets: {total_bets}")
            print(f"  Pending bets: {pending_count}")
            print(f"  Pending total: ${float(pending_total or 0):.2f}")
    
    db.close()

if __name__ == '__main__':
    main()
