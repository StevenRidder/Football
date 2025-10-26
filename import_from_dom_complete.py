#!/usr/bin/env python3
"""
Import ALL bets from the DOM extracted file
"""
import re
from datetime import datetime
from nfl_edge.bets.db import BettingDB

def extract_all_bets_from_dom():
    """Extract all bets from the DOM file"""
    with open('extracted_bets_raw.txt', 'r') as f:
        content = f.read()
    
    # Pattern: ticket_id date ... Pending ... $amount
    pattern = r'(\d{9,10}-\d+)\s+(\d{2}/\d{2}/\d{4})[^$]*?Pending[^$]*?\$(\d+\.\d{2})'
    matches = re.findall(pattern, content)
    
    # Deduplicate by ticket_id (each bet appears multiple times in DOM)
    bets_dict = {}
    for ticket_id, date_str, amount_str in matches:
        if ticket_id not in bets_dict:
            bets_dict[ticket_id] = {
                'ticket_id': ticket_id,
                'date': date_str,
                'amount': float(amount_str),
                'status': 'Pending'
            }
    
    # Also get Won/Lost bets
    pattern_won = r'(\d{9,10}-\d+)\s+(\d{2}/\d{2}/\d{4})[^$]*?Won[^$]*?\$(\d+\.\d{2})'
    matches_won = re.findall(pattern_won, content)
    for ticket_id, date_str, amount_str in matches_won:
        if ticket_id not in bets_dict:
            bets_dict[ticket_id] = {
                'ticket_id': ticket_id,
                'date': date_str,
                'amount': float(amount_str),
                'status': 'Won'
            }
    
    pattern_lost = r'(\d{9,10}-\d+)\s+(\d{2}/\d{2}/\d{4})[^$]*?Lost[^$]*?\$(\d+\.\d{2})'
    matches_lost = re.findall(pattern_lost, content)
    for ticket_id, date_str, amount_str in matches_lost:
        if ticket_id not in bets_dict:
            bets_dict[ticket_id] = {
                'ticket_id': ticket_id,
                'date': date_str,
                'amount': float(amount_str),
                'status': 'Lost'
            }
    
    return list(bets_dict.values())

def main():
    print("📊 Importing ALL bets from DOM file...")
    
    bets = extract_all_bets_from_dom()
    print(f"✅ Found {len(bets)} unique bets in DOM file")
    
    # Calculate totals
    pending_total = sum(b['amount'] for b in bets if b['status'] == 'Pending')
    total_wagered = sum(b['amount'] for b in bets)
    
    print(f"\n📈 From DOM file:")
    print(f"   Total bets: {len(bets)}")
    print(f"   Pending: ${pending_total:.2f}")
    print(f"   Total wagered: ${total_wagered:.2f}")
    
    print(f"\n⚠️  NOTE: You expect $561.33 pending")
    print(f"   DOM file only has: ${pending_total:.2f}")
    print(f"   Missing: ${561.33 - pending_total:.2f}")
    print(f"\n   The DOM snapshot is incomplete!")
    print(f"   You need to scroll down on BetOnline to load ALL bets,")
    print(f"   then re-run the browser extraction script.")
    
    # Ask if user wants to import what we have
    print(f"\n❓ Import the {len(bets)} bets we DO have? (y/n)")
    response = input().strip().lower()
    
    if response != 'y':
        print("❌ Import cancelled")
        return
    
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
            date_obj = datetime.strptime(bet['date'], '%m/%d/%Y').date()
            
            # Determine bet type
            ticket_id = bet['ticket_id']
            if '-' in ticket_id and ticket_id.split('-')[0] == '905768987':
                bet_type = 'Parlay'
                description = f"Parlay (Round Robin)"
            elif bet['amount'] >= 10:
                bet_type = 'Parlay'
                description = f"Parlay"
            else:
                bet_type = 'Parlay'
                description = f"Parlay"
            
            # Calculate profit
            if bet['status'] == 'Won':
                profit = bet['amount']  # Simplified
            elif bet['status'] == 'Lost':
                profit = -bet['amount']
            else:
                profit = 0
            
            bet_data = {
                'ticket_id': ticket_id,
                'date': date_obj,
                'description': description,
                'type': bet_type,
                'status': bet['status'],
                'amount': bet['amount'],
                'to_win': 0,  # Not in DOM
                'profit': profit,
                'is_round_robin': False,
                'round_robin_parent': None
            }
            
            db.insert_bet(bet_data)
            imported += 1
            
        except Exception as e:
            print(f"⚠️  Error importing {bet['ticket_id']}: {e}")
            continue
    
    db.close()
    
    print(f"\n✅ Import complete!")
    print(f"   📝 Imported {imported} bets")
    
    # Show summary
    db2 = BettingDB()
    summary = db2.get_performance_summary()
    db2.close()
    
    print(f"\n📈 Database Summary:")
    print(f"   Total Bets: {summary['total_bets']}")
    print(f"   Total Wagered: ${summary['total_wagered']:.2f}")
    print(f"   Pending: {summary['pending_count']} (${summary['pending_amount']:.2f})")

if __name__ == '__main__':
    main()

