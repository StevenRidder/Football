#!/usr/bin/env python3
"""
Load round robin bets from CSV file into the database
"""
import sys
import csv
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nfl_edge.bets.db import BettingDB

def load_round_robin_bets(csv_path):
    """Load round robin bets from CSV file"""
    db = BettingDB()
    
    try:
        inserted = 0
        skipped = 0
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                parlay_id = row['parlay_id']
                size = int(row['size'])
                legs = row['legs']
                stake = float(row['stake'])
                to_win = float(row['to_win'])
                
                # Generate ticket ID
                ticket_id = f"round_robin_{parlay_id}"
                
                # Use today's date
                date = datetime.now().strftime('%Y-%m-%d')
                
                # Determine bet type
                bet_type = f"Round Robin {size}-Leg"
                
                # Create bet dictionary
                bet = {
                    'ticket_id': ticket_id,
                    'date': date,
                    'description': legs,  # Already formatted with " | " separator
                    'bet_type': bet_type,
                    'status': 'Pending',
                    'amount': stake,
                    'to_win': to_win,
                    'profit': 0.0,
                    'is_round_robin': True,
                    'round_robin_parent': 'round_robin_8teams_2-6'  # Group identifier
                }
                
                # Check if bet already exists
                conn = db.connect()
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM bets WHERE ticket_id = %s', (ticket_id,))
                    existing = cur.fetchone()
                    
                    if existing:
                        print(f"⏭️  Skipping {ticket_id} - already exists")
                        skipped += 1
                    else:
                        db.insert_bet(bet)
                        print(f"✅ Loaded {ticket_id}: {size}-leg parlay, ${stake:.2f} stake, ${to_win:.2f} to win")
                        inserted += 1
                
                conn.close()
        
        print(f"\n📊 Summary:")
        print(f"   ✅ Inserted: {inserted}")
        print(f"   ⏭️  Skipped: {skipped}")
        print(f"   📈 Total: {inserted + skipped}")
        
    except Exception as e:
        print(f"❌ Error loading bets: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    csv_path = "/Users/steveridder/Dropbox/Mac/Downloads/round_robin_8teams_2-6.csv"
    
    if not Path(csv_path).exists():
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    print("🔄 Loading round robin bets from CSV...")
    print(f"   File: {csv_path}\n")
    
    load_round_robin_bets(csv_path)

