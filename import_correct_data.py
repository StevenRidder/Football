#!/usr/bin/env python3
"""
Import correct betting data from pipe-delimited file
"""
from datetime import datetime
from nfl_edge.bets.db import BettingDB

def main():
    print("📊 Importing correct betting data...")
    
    # Read the file
    bets = []
    with open('correct_bets_data.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) < 7:
                continue
            
            # Format: ticket_id|date|description|type|status|amount|to_win
            # Description can contain pipes, so we need to extract from the end
            ticket_id = parts[0]
            date_str = parts[1]
            to_win_str = parts[-1]
            amount_str = parts[-2]
            status = parts[-3]
            bet_type = parts[-4]
            description = '|'.join(parts[2:-4])  # Everything in between
            
            # Parse date
            date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()
            
            # Parse amounts
            amount = float(amount_str)
            to_win = float(to_win_str)
            
            # Calculate profit
            if status == 'Won':
                profit = to_win
            elif status == 'Lost':
                profit = -amount
            else:
                profit = 0
            
            bets.append({
                'ticket_id': ticket_id,
                'date': date_obj,
                'description': description,
                'type': bet_type,
                'status': status,
                'amount': amount,
                'to_win': to_win,
                'profit': profit
            })
    
    print(f"✅ Parsed {len(bets)} bets")
    
    # Initialize database
    db = BettingDB()
    print("🔧 Clearing existing data...")
    conn = db.connect()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM parlay_legs")
        cur.execute("DELETE FROM bets")
    conn.commit()
    print("✅ Database cleared")
    
    # Import bets
    print(f"📥 Importing {len(bets)} bets...")
    imported = 0
    
    for bet in bets:
        try:
            bet_data = {
                'ticket_id': bet['ticket_id'],
                'date': bet['date'],
                'description': bet['description'],
                'type': bet['type'],
                'status': bet['status'],
                'amount': bet['amount'],
                'to_win': bet['to_win'],
                'profit': bet['profit'],
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
    
    print(f"\n📈 Summary:")
    print(f"   Total Bets: {summary['total_bets']}")
    print(f"   Total Wagered: ${summary['total_wagered']:.2f}")
    print(f"   Pending: {summary['pending_count']} (${summary['pending_amount']:.2f})")
    print(f"   Won: {summary['won_count']}")
    print(f"   Lost: {summary['lost_count']}")
    print(f"   Total Profit: ${summary['total_profit']:.2f}")

if __name__ == '__main__':
    main()

