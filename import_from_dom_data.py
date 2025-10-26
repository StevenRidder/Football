#!/usr/bin/env python3
"""
Import bets directly from the DOM-extracted raw data into PostgreSQL
This is the source of truth - not the JSON file
"""
import json
import re
from datetime import datetime
from nfl_edge.bets.db import BettingDB

def parse_dom_data(file_path='extracted_bets_raw.txt'):
    """Parse the raw DOM data file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the JSON data
    json_start = content.find('{')
    if json_start == -1:
        raise ValueError("No JSON found in file")
    
    # Find the matching closing brace
    brace_count = 0
    json_end = json_start
    for i in range(json_start, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break
    
    # Parse JSON
    json_str = content[json_start:json_end]
    data = json.loads(json_str)
    
    # Extract bets from the preview data
    preview_text = ' '.join(data.get('preview', []))
    
    # Parse bets from the text
    # Format: Ticket# Date Description Type Status Amount ToWin
    bets = []
    
    # Split by ticket numbers (they start with a space and are 9-10 digits)
    ticket_pattern = r'\s+(\d{9,10}(?:-\d+)?)\s+'
    parts = re.split(ticket_pattern, preview_text)
    
    # Process pairs (ticket_id, data)
    for i in range(1, len(parts), 2):
        if i + 1 >= len(parts):
            break
            
        ticket_id = parts[i].strip()
        bet_text = parts[i + 1].strip()
        
        # Parse the bet data
        # Expected format: Date Description Type Status Amount ToWin
        bet_parts = bet_text.split()
        
        if len(bet_parts) < 4:
            continue
        
        # Date is first (MM/DD/YYYY)
        date_str = bet_parts[0] if '/' in bet_parts[0] else None
        
        # Status is one of: Pending, Won, Lost
        status = None
        status_idx = -1
        for idx, part in enumerate(bet_parts):
            if part in ['Pending', 'Won', 'Lost', 'Push']:
                status = part
                status_idx = idx
                break
        
        if not status:
            continue
        
        # Amount and ToWin are after status
        amount_str = bet_parts[status_idx + 1] if status_idx + 1 < len(bet_parts) else '0'
        to_win_str = bet_parts[status_idx + 2] if status_idx + 2 < len(bet_parts) else '0'
        
        # Clean currency
        amount = float(amount_str.replace('$', '').replace(',', '')) if amount_str != '-' else 0
        to_win = float(to_win_str.replace('$', '').replace(',', '')) if to_win_str != '-' else 0
        
        # Type is before status
        bet_type = bet_parts[status_idx - 1] if status_idx > 0 else 'Unknown'
        
        # Description is everything between date and type
        description = ' '.join(bet_parts[1:status_idx-1])
        
        bets.append({
            'ticket_id': ticket_id,
            'date': date_str,
            'description': description,
            'type': bet_type,
            'status': status,
            'amount': amount,
            'to_win': to_win
        })
    
    return bets

def main():
    print("📊 Importing bets from DOM-extracted data...")
    
    # Parse the DOM data
    try:
        bets = parse_dom_data()
        print(f"✅ Parsed {len(bets)} bets from DOM data")
    except Exception as e:
        print(f"❌ Error parsing DOM data: {e}")
        print("\n⚠️  Falling back to manual parsing...")
        # If parsing fails, we'll need to manually structure the data
        return
    
    if not bets:
        print("❌ No bets found in DOM data")
        return
    
    # Show sample
    print("\n📝 Sample bets:")
    for bet in bets[:3]:
        print(f"  {bet['ticket_id']}: {bet['type']} - ${bet['amount']:.2f} → ${bet['to_win']:.2f}")
    
    # Initialize database
    db = BettingDB()
    print("\n🔧 Clearing existing data...")
    conn = db.connect()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM parlay_legs")
        cur.execute("DELETE FROM bets")
    conn.commit()
    print("✅ Database cleared")
    
    # Import bets
    print(f"\n📥 Importing {len(bets)} bets...")
    imported = 0
    
    for bet in bets:
        try:
            # Parse date
            date_str = bet.get('date', '')
            if date_str and '/' in date_str:
                date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()
            else:
                date_obj = datetime.now().date()
            
            # Calculate profit
            if bet['status'] == 'Won':
                profit = bet['to_win']
            elif bet['status'] == 'Lost':
                profit = -bet['amount']
            else:
                profit = 0
            
            # Insert bet
            bet_data = {
                'ticket_id': bet['ticket_id'],
                'date': date_obj,
                'description': bet.get('description', ''),
                'type': bet.get('type', 'Unknown'),
                'status': bet['status'],
                'amount': bet['amount'],
                'to_win': bet['to_win'],
                'profit': profit,
                'is_round_robin': False,
                'round_robin_parent': None
            }
            
            db.insert_bet(bet_data)
            imported += 1
            
        except Exception as e:
            print(f"⚠️  Error importing {bet.get('ticket_id')}: {e}")
            continue
    
    db.close()
    
    print("\n✅ Import complete!")
    print(f"   📝 Imported {imported} bets")
    
    # Show summary
    db2 = BettingDB()
    summary = db2.get_performance_summary()
    db2.close()
    
    print("\n📈 Summary:")
    print(f"   Total Bets: {summary['total_bets']}")
    print(f"   Total Wagered: ${summary['total_wagered']:.2f}")
    print(f"   Pending: {summary['pending_count']} (${summary['pending_amount']:.2f})")
    print(f"   Won: {summary['won_count']}")
    print(f"   Lost: {summary['lost_count']}")

if __name__ == '__main__':
    main()

