#!/usr/bin/env python3
"""
Import bets from manually copied Network tab responses
"""

import json
import sys
from pathlib import Path
from dateutil import parser as date_parser

sys.path.insert(0, str(Path(__file__).parent))
from nfl_edge.bets.db import BettingDB


def parse_responses_file(file_path: str):
    """Parse file with multiple JSON responses separated by ---RESPONSE---"""
    
    print(f"📖 Reading responses from: {file_path}...")
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split by separator or try to parse as single JSON or multiple JSONs
    all_bets = []
    
    # Try splitting by separator first
    if '---RESPONSE---' in content:
        parts = content.split('---RESPONSE---')
    else:
        # Try to split by }{ pattern (multiple JSON objects concatenated)
        parts = content.split('}{')
        parts = [
            (parts[0] if i == 0 else '{' + parts[i]) + ('}' if i < len(parts) - 1 else '')
            for i in range(len(parts))
        ]
    
    print(f"Found {len(parts)} response parts\n")
    
    for i, part in enumerate(parts, 1):
        part = part.strip()
        if not part:
            continue
            
        try:
            data = json.loads(part)
            
            if 'Data' in data and data['Data']:
                bets = data['Data']
                all_bets.extend(bets)
                print(f"  ✓ Response {i}: {len(bets)} bets (TotalRows: {data.get('TotalRows', '?')})")
            else:
                print(f"  ⚠️  Response {i}: No Data field")
                
        except json.JSONDecodeError as e:
            print(f"  ❌ Response {i}: Failed to parse JSON: {e}")
    
    # Deduplicate
    unique_bets = {}
    for bet in all_bets:
        key = f"{bet['TicketNumber']}-{bet.get('Date', bet.get('PlacedDate', ''))}"
        if key not in unique_bets:
            unique_bets[key] = bet
    
    bets = list(unique_bets.values())
    
    print(f"\n✅ Extracted {len(bets)} unique bets from {len(all_bets)} total")
    
    return bets


def import_bets(bets):
    """Import bets to database"""
    
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
            if len(errors) <= 5:
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
    file_path = '/Users/steveridder/Downloads/all_responses.txt'
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        print("\nTo create this file:")
        print("1. Go to BetOnline bet history")
        print("2. Open DevTools → Network tab")
        print("3. Clear network log")
        print("4. Scroll to load bets")
        print("5. Find ALL 'get-bet-history' requests")
        print("6. For EACH request:")
        print("   - Click it")
        print("   - Go to Response tab")
        print("   - Right-click → Copy value")
        print("   - Paste into text file")
        print("   - Add '---RESPONSE---' between each")
        print("7. Save as ~/Downloads/all_responses.txt")
        sys.exit(1)
    
    bets = parse_responses_file(file_path)
    
    if bets:
        import_bets(bets)
    else:
        print("❌ No bets found!")

