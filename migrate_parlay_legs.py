#!/usr/bin/env python3
"""
Migration script to parse existing parlay bets and populate parlay_legs table
"""
import sys
sys.path.insert(0, '/Users/steveridder/Git/Football')

from nfl_edge.bets.db import BettingDB
from nfl_edge.bets.leg_parser import ParlayLegParser
import psycopg2


def migrate_parlay_legs():
    """Parse all existing parlay bets and populate parlay_legs table"""
    print("=" * 70)
    print("MIGRATING PARLAY LEGS")
    print("=" * 70)
    
    db = BettingDB()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get all parlay bets
    cursor.execute("""
        SELECT id, ticket_id, bet_type, description
        FROM bets
        WHERE bet_type LIKE '%arlay%'
        ORDER BY id
    """)
    
    parlays = cursor.fetchall()
    print(f"\nFound {len(parlays)} parlay bets to process\n")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for bet in parlays:
        bet_id = bet['id']
        ticket_id = bet['ticket_id']
        bet_type = bet['bet_type']
        description = bet['description']
        
        try:
            # Check if legs already exist
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM parlay_legs
                WHERE bet_id = %s
            """, (bet_id,))
            existing_count = cursor.fetchone()['count']
            
            if existing_count > 0:
                print(f"  ⏭️  {ticket_id}: Already has {existing_count} legs, skipping")
                skip_count += 1
                continue
            
            # Parse legs
            legs = ParlayLegParser.parse_legs(description, bet_type)
            
            if not legs:
                print(f"  ⚠️  {ticket_id}: Could not parse legs from description")
                error_count += 1
                continue
            
            # Insert legs
            db.insert_parlay_legs(bet_id, legs)
            print(f"  ✅ {ticket_id}: Parsed and inserted {len(legs)} legs")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ {ticket_id}: Error - {e}")
            error_count += 1
            conn.rollback()
            continue
    
    db.close()
    
    print("\n" + "=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print(f"✅ Successfully migrated: {success_count} bets")
    print(f"⏭️  Skipped (already done): {skip_count} bets")
    print(f"❌ Errors: {error_count} bets")
    print("=" * 70)
    
    return success_count, skip_count, error_count


if __name__ == '__main__':
    migrate_parlay_legs()

