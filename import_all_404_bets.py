#!/usr/bin/env python3
"""
Import ALL 404 bets from the complete JSON export
"""

import json
import sys
from datetime import datetime
from dateutil import parser as date_parser
from pathlib import Path

# Add nfl_edge to path
sys.path.insert(0, str(Path(__file__).parent))

from nfl_edge.bets.db import BettingDB


def import_bets(json_file: str):
    """Import all bets from JSON file"""
    
    print(f"📖 Reading {json_file}...")
    with open(json_file, 'r') as f:
        bets = json.load(f)
    
    print(f"✅ Loaded {len(bets)} bets from file")
    
    # Calculate expected totals
    pending_bets = [b for b in bets if b['WagerStatus'] == 'Pending']
    total_stake = sum(float(b['Risk']) for b in pending_bets)
    total_to_win = sum(float(b['ToWin']) for b in pending_bets)
    
    print(f"💰 Pending: {len(pending_bets)} bets, ${total_stake:.2f} stake, ${total_to_win:.2f} to win")
    
    # Connect to DB
    print("\n💾 Importing to database...")
    db = BettingDB()
    db.connect()
    
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM parlay_legs")
    cursor.execute("DELETE FROM bets")
    db.conn.commit()
    print("  ✓ Cleared existing data")
    
    # Import all
    imported = 0
    errors = []
    
    for bet in bets:
        try:
            # Parse date
            date_str = bet['Date']
            if not date_str.endswith('Z'):
                date_str += 'Z'
            if '.' not in date_str:
                date_str = date_str.replace('Z', '.000Z')
            elif len(date_str.split('.')[-1]) < 4:
                parts = date_str.split('.')
                ms = parts[1].replace('Z', '')
                ms = ms.ljust(3, '0')
                date_str = f"{parts[0]}.{ms}Z"
            
            parsed_date = date_parser.isoparse(date_str)
            
            bet_data = {
                'ticket_id': str(bet['TicketNumber']),
                'date': parsed_date,
                'description': bet['Description'],
                'bet_type': bet.get('WagerTypeDetail', bet.get('WagerType', 'Unknown')),
                'status': bet['WagerStatus'],
                'amount': float(bet['Risk']),
                'to_win': float(bet['ToWin']),
                'product': bet.get('Product', 'Sportsbook')
            }
            
            db.insert_bet(bet_data)
            imported += 1
            
            if imported % 100 == 0:
                print(f"  Imported {imported}/{len(bets)}...")
                
        except Exception as e:
            error_msg = f"Ticket {bet.get('TicketNumber')}: {e}"
            errors.append(error_msg)
            if len(errors) <= 5:  # Only print first 5 errors
                print(f"  ❌ {error_msg}")
    
    db.conn.commit()
    
    # Summary
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'Pending' THEN 1 END) as pending,
            SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END) as stake,
            SUM(CASE WHEN status = 'Pending' THEN to_win ELSE 0 END) as to_win
        FROM bets
    """)
    result = cursor.fetchone()
    
    print("\n" + "=" * 60)
    print("✅ IMPORT COMPLETE!")
    print("=" * 60)
    print(f"Total bets imported: {result['total']}")
    print(f"Pending bets: {result['pending']}")
    print(f"Total stake: ${float(result['stake'] or 0):.2f}")
    print(f"Total to win: ${float(result['to_win'] or 0):.2f}")
    
    if errors:
        print(f"\n⚠️  {len(errors)} errors occurred")
        if len(errors) > 5:
            print(f"   (showing first 5, {len(errors) - 5} more suppressed)")
    
    print("=" * 60)
    
    db.close()


if __name__ == '__main__':
    # Look for the JSON file
    json_file = '/Users/steveridder/Downloads/all_400_bets_complete.json'
    
    if not Path(json_file).exists():
        # Try alternate name
        json_file = '/Users/steveridder/Downloads/all_404_bets_complete.json'
    
    if not Path(json_file).exists():
        print(f"❌ File not found: {json_file}")
        print("\nPlease:")
        print("1. Go to https://sports.betonline.ag/my-account/bet-history")
        print("2. Open DevTools (F12) → Console tab")
        print("3. Copy/paste the contents of complete_bet_fetch.js")
        print("4. Wait for it to download all_400_bets_complete.json")
        print("5. Then run this script again")
        sys.exit(1)
    
    import_bets(json_file)

