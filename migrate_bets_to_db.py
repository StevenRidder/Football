#!/usr/bin/env python3
"""
Migrate betting data from JSON to PostgreSQL database
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from nfl_edge.bets.db import BettingDB

def parse_date(date_str):
    """Parse date string to date object"""
    try:
        return datetime.strptime(date_str, '%m/%d/%Y').date()
    except:
        return datetime.now().date()

def parse_description_to_legs(description, bet_type):
    """Parse bet description into individual legs"""
    if '|' not in description:
        return []
    
    legs = []
    parts = [p.strip() for p in description.split('|') if p.strip()]
    
    for part in parts:
        leg = {'description': part}
        
        # Try to extract team, line, odds
        # Example: "271 New York Giants +7½ -115 for GAME"
        # Example: "VIKINGS - Team Total - OVER 17.5"
        if ' - ' in part:
            # Team total or special bet
            parts_split = part.split(' - ')
            if len(parts_split) >= 2:
                leg['team'] = parts_split[0].strip()
        
        # Extract odds (e.g., -115, +145)
        import re
        odds_match = re.search(r'([-+]\d+)(?:\s|$)', part)
        if odds_match:
            leg['odds'] = odds_match.group(1)
        
        # Extract line (e.g., +7½, -7, OVER 17.5)
        line_match = re.search(r'([+-]?\d+(?:½)?|(?:OVER|UNDER)\s+\d+\.?\d*)', part)
        if line_match:
            leg['line'] = line_match.group(1)
        
        legs.append(leg)
    
    return legs

def migrate_json_to_db(json_file='artifacts/betonline_bets.json', db_url=None):
    """Migrate bets from JSON file to PostgreSQL"""
    
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    bets = data.get('bets', [])
    
    print(f"📊 Found {len(bets)} bets to migrate")
    
    # Initialize database
    db = BettingDB(db_url)
    print("🔧 Initializing database schema...")
    db.init_schema()
    print("✅ Schema initialized")
    
    # Track round robin parents
    round_robin_groups = {}
    
    # First pass: identify round robin groups
    for bet in bets:
        ticket_id = bet['ticket_id']
        if '-' in ticket_id:
            # Normalize double dashes
            normalized_id = ticket_id.replace('--', '-')
            parts = normalized_id.rsplit('-', 1)
            if len(parts) == 2:
                base_ticket, suffix = parts
                try:
                    int(suffix)  # Check if suffix is numeric
                    if base_ticket not in round_robin_groups:
                        round_robin_groups[base_ticket] = []
                    round_robin_groups[base_ticket].append(bet)
                except ValueError:
                    pass
    
    # Filter out single-bet "groups"
    round_robin_groups = {k: v for k, v in round_robin_groups.items() if len(v) > 1}
    
    print(f"🎯 Identified {len(round_robin_groups)} round robin groups")
    
    # Track which bets are part of round robins
    round_robin_bet_ids = set()
    for group_bets in round_robin_groups.values():
        for bet in group_bets:
            round_robin_bet_ids.add(bet['ticket_id'])
    
    # Insert bets
    inserted_count = 0
    round_robin_count = 0
    
    for bet in bets:
        ticket_id = bet['ticket_id']
        
        # Skip if this is part of a round robin (we'll insert the parent instead)
        if ticket_id in round_robin_bet_ids:
            continue
        
        # Prepare bet data
        bet_data = {
            'ticket_id': ticket_id,
            'date': parse_date(bet.get('date', '')),
            'description': bet.get('description', ''),
            'type': bet.get('type', 'Unknown'),
            'status': bet.get('status', 'Pending'),
            'amount': float(bet.get('amount', 0)),
            'to_win': float(bet.get('to_win', 0)),
            'profit': float(bet.get('profit', 0)),
            'is_round_robin': False,
            'round_robin_parent': None
        }
        
        # Insert bet
        bet_id = db.insert_bet(bet_data)
        
        # Parse and insert parlay legs if applicable
        if '|' in bet_data['description']:
            legs = parse_description_to_legs(bet_data['description'], bet_data['type'])
            if legs:
                db.insert_parlay_legs(bet_id, legs)
        
        inserted_count += 1
    
    # Insert round robin parent bets
    for base_ticket, group_bets in round_robin_groups.items():
        total_amount = sum(float(b.get('amount', 0)) for b in group_bets)
        total_to_win = sum(float(b.get('to_win', 0)) for b in group_bets)
        
        # Determine status
        statuses = [b.get('status') for b in group_bets]
        if 'Won' in statuses:
            status = 'Won'
        elif all(s == 'Lost' for s in statuses):
            status = 'Lost'
        else:
            status = 'Pending'
        
        # Calculate profit
        if status == 'Won':
            profit = total_to_win
        elif status == 'Lost':
            profit = -total_amount
        else:
            profit = 0.0
        
        # Insert parent round robin bet
        parent_bet = {
            'ticket_id': f"{base_ticket}-RR",
            'date': parse_date(group_bets[0].get('date', '')),
            'description': f"Round Robin ({len(group_bets)} combinations)",
            'type': 'Round Robin',
            'status': status,
            'amount': total_amount,
            'to_win': total_to_win,
            'profit': profit,
            'is_round_robin': False,  # Parent is not marked as round robin
            'round_robin_parent': None
        }
        
        parent_id = db.insert_bet(parent_bet)
        round_robin_count += 1
        
        # Insert individual round robin bets as children
        for sub_bet in group_bets:
            sub_bet_data = {
                'ticket_id': sub_bet['ticket_id'],
                'date': parse_date(sub_bet.get('date', '')),
                'description': sub_bet.get('description', ''),
                'type': sub_bet.get('type', 'Parlay'),
                'status': sub_bet.get('status', 'Pending'),
                'amount': float(sub_bet.get('amount', 0)),
                'to_win': float(sub_bet.get('to_win', 0)),
                'profit': float(sub_bet.get('profit', 0)),
                'is_round_robin': True,
                'round_robin_parent': f"{base_ticket}-RR"
            }
            
            sub_bet_id = db.insert_bet(sub_bet_data)
            
            # Parse legs
            if '|' in sub_bet_data['description']:
                legs = parse_description_to_legs(sub_bet_data['description'], sub_bet_data['type'])
                if legs:
                    db.insert_parlay_legs(sub_bet_id, legs)
    
    db.close()
    
    print(f"\n✅ Migration complete!")
    print(f"   📝 Inserted {inserted_count} standalone bets")
    print(f"   🎯 Created {round_robin_count} round robin parent bets")
    print(f"   📊 Total: {inserted_count + round_robin_count} bets in database")
    
    # Show summary
    db2 = BettingDB(db_url)
    summary = db2.get_performance_summary()
    db2.close()
    
    print(f"\n📈 Summary:")
    print(f"   Total Bets: {summary['total_bets']}")
    print(f"   Total Wagered: ${summary['total_wagered']:.2f}")
    print(f"   Pending: {summary['pending_count']} (${summary['pending_amount']:.2f})")
    print(f"   Won: {summary['won_count']}")
    print(f"   Lost: {summary['lost_count']}")
    print(f"   Total Profit: ${summary['total_profit']:.2f}")
    print(f"   ROI: {summary['roi']:.2f}%")
    print(f"   Win Rate: {summary['win_rate']:.2f}%")

if __name__ == '__main__':
    import_file = 'artifacts/betonline_bets.json'
    if len(sys.argv) > 1:
        import_file = sys.argv[1]
    
    db_url = None
    if len(sys.argv) > 2:
        db_url = sys.argv[2]
    
    migrate_json_to_db(import_file, db_url)

