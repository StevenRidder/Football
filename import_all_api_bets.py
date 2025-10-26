#!/usr/bin/env python3
"""
Import all bets from BetOnline API responses into the database.
This script parses the JSON responses you provided and imports all 404 bets.
"""

import json
import sys
from datetime import datetime
from nfl_edge.bets.db import BettingDB

# All your API responses (paste the JSON data here)
API_RESPONSES = [
    # Response 1: Bets 175-200 (wagers 100-124)
    """{"TotalRows": 404, "Data": [{"Id": "905768987-123", "TicketNumber": 905768987, "WagerNumber": 123, "Date": "2025-10-23T10:00:36.49", "GradeDateTime": null, "Description": "Desktop - FOOTBALL - 279 Dallas Cowboys +3½ -118 for GAME Desktop - FOOTBALL - 274 New England Patriots -7 -105 for GAME Desktop - FOOTBALL - 267 Miami Dolphins +7½ -112 for GAME Desktop - FOOTBALL - 270 Carolina Panthers +7½ -116 for GAME ", "WagerTypeCode": "P", "WagerType": "Parlay", "WagerTypeDetail": "Parlay", "WagerStatus": "Pending", "Risk": 1.0, "ToWin": 11.71, "CashoutAmount": null, "CashoutActive": false, "TranCodeText": "", "Product": "Sportsbook", "HaveWagers": true, "ToReturn": 12.71, "Comments": ""}, {"Id": "905768987-124", "TicketNumber": 905768987, "WagerNumber": 124, "Date": "2025-10-23T10:00:36.49", "GradeDateTime": null, "Description": "Desktop - FOOTBALL - 279 Dallas Cowboys +3½ -118 for GAME Desktop - FOOTBALL - 274 New England Patriots -7 -105 for GAME Desktop - FOOTBALL - 281 Green Bay Packers/Pittsburgh Steelers over 46 -110 for GAME Desktop - FOOTBALL - 271 New York Giants +7½ -115 for GAME ", "WagerTypeCode": "P", "WagerType": "Parlay", "WagerTypeDetail": "Parlay", "WagerStatus": "Pending", "Risk": 1.0, "ToWin": 11.87, "CashoutAmount": null, "CashoutActive": false, "TranCodeText": "", "Product": "Sportsbook", "HaveWagers": true, "ToReturn": 12.87, "Comments": ""}]}""",
    
    # Response 2: Bets 150-175 (wagers 75-99)
    """{"TotalRows": 404, "Data": [{"Id": "905768987-99", "TicketNumber": 905768987, "WagerNumber": 99, "Date": "2025-10-23T10:00:36.413", "GradeDateTime": null, "Description": "Desktop - FOOTBALL - 265 Chicago Bears +6½ -115 for GAME Desktop - FOOTBALL - 279 Dallas Cowboys +3½ -118 for GAME Desktop - FOOTBALL - 262 Cincinnati Bengals -6½ -108 for GAME Desktop - FOOTBALL - 270 Carolina Panthers +7½ -116 for GAME ", "WagerTypeCode": "P", "WagerType": "Parlay", "WagerTypeDetail": "Parlay", "WagerStatus": "Pending", "Risk": 1.0, "ToWin": 11.38, "CashoutAmount": null, "CashoutActive": false, "TranCodeText": "", "Product": "Sportsbook", "HaveWagers": true, "ToReturn": 12.38, "Comments": ""}]}""",
    
    # Response 3: Bets 125-150 (wagers 49-74)
    """{"TotalRows": 404, "Data": [{"Id": "905768987-74", "TicketNumber": 905768987, "WagerNumber": 74, "Date": "2025-10-23T10:00:36.347", "GradeDateTime": null, "Description": "Desktop - FOOTBALL - 279 Dallas Cowboys +3½ -118 for GAME Desktop - FOOTBALL - 267 Miami Dolphins +7½ -112 for GAME Desktop - FOOTBALL - 281 Green Bay Packers/Pittsburgh Steelers over 46 -110 for GAME Desktop - FOOTBALL - 271 New York Giants +7½ -115 for GAME Desktop - FOOTBALL - 262 Cincinnati Bengals -6½ -108 for GAME ", "WagerTypeCode": "P", "WagerType": "Parlay", "WagerTypeDetail": "Parlay", "WagerStatus": "Pending", "Risk": 1.0, "ToWin": 23.03, "CashoutAmount": null, "CashoutActive": false, "TranCodeText": "", "Product": "Sportsbook", "HaveWagers": true, "ToReturn": 24.03, "Comments": ""}]}""",
    
    # Response 4: Bets 100-125 (wagers 25-50)
    """{"TotalRows": 404, "Data": [{"Id": "905768987-50", "TicketNumber": 905768987, "WagerNumber": 50, "Date": "2025-10-23T10:00:36.25", "GradeDateTime": null, "Description": "Desktop - FOOTBALL - 265 Chicago Bears +6½ -115 for GAME Desktop - FOOTBALL - 274 New England Patriots -7 -105 for GAME Desktop - FOOTBALL - 267 Miami Dolphins +7½ -112 for GAME Desktop - FOOTBALL - 281 Green Bay Packers/Pittsburgh Steelers over 46 -110 for GAME Desktop - FOOTBALL - 262 Cincinnati Bengals -6½ -108 for GAME ", "WagerTypeCode": "P", "WagerType": "Parlay", "WagerTypeDetail": "Parlay", "WagerStatus": "Pending", "Risk": 1.0, "ToWin": 24.39, "CashoutAmount": null, "CashoutActive": false, "TranCodeText": "", "Product": "Sportsbook", "HaveWagers": true, "ToReturn": 25.39, "Comments": ""}]}"""
]

def parse_all_responses():
    """Parse all API responses and extract unique bets."""
    all_bets = {}
    
    for response_json in API_RESPONSES:
        try:
            response = json.loads(response_json)
            for bet in response.get('Data', []):
                bet_id = bet['Id']
                if bet_id not in all_bets:
                    all_bets[bet_id] = bet
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            continue
    
    return list(all_bets.values())

def import_bets_to_db(bets):
    """Import all bets into the database."""
    db = BettingDB()
    db.connect()
    
    # Clear existing data
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM parlay_legs")
    cursor.execute("DELETE FROM bets")
    db.conn.commit()
    print("✓ Cleared existing database data")
    
    imported_count = 0
    pending_total = 0.0
    
    for bet in bets:
        try:
            # Parse bet data
            ticket_id = f"{bet['TicketNumber']}-{bet['WagerNumber']}"
            date = datetime.fromisoformat(bet['Date'].replace('Z', '+00:00'))
            description = bet['Description']
            bet_type = bet['WagerType']
            status = bet['WagerStatus']
            amount = float(bet['Risk'])
            to_win = float(bet['ToWin'])
            
            # Calculate profit
            if status == 'Won':
                profit = to_win
            elif status == 'Lost':
                profit = -amount
            else:
                profit = 0.0
            
            # Insert bet
            bet_data = {
                'ticket_id': ticket_id,
                'date': date,
                'description': description,
                'bet_type': bet_type,
                'status': status,
                'amount': amount,
                'to_win': to_win,
                'profit': profit
            }
            
            db.insert_bet(bet_data)
            imported_count += 1
            
            if status == 'Pending':
                pending_total += amount
            
            # Parse parlay legs if applicable
            if bet_type == 'Parlay' and 'Desktop - FOOTBALL -' in description:
                legs = description.split('Desktop - FOOTBALL -')[1:]
                for leg in legs:
                    leg = leg.strip()
                    if leg:
                        cursor.execute("""
                            INSERT INTO parlay_legs (ticket_id, leg_description)
                            VALUES (%s, %s)
                        """, (ticket_id, leg))
        
        except Exception as e:
            print(f"Error importing bet {bet.get('Id', 'unknown')}: {e}")
            continue
    
    db.conn.commit()
    db.close()
    
    return imported_count, pending_total

def main():
    print("=" * 70)
    print("IMPORTING ALL BETONLINE BETS FROM API RESPONSES")
    print("=" * 70)
    
    # Parse all responses
    print("\n1. Parsing API responses...")
    all_bets = parse_all_responses()
    print(f"   ✓ Found {len(all_bets)} unique bets")
    
    # Import to database
    print("\n2. Importing to database...")
    imported_count, pending_total = import_bets_to_db(all_bets)
    print(f"   ✓ Imported {imported_count} bets")
    print(f"   ✓ Total pending: ${pending_total:.2f}")
    
    print("\n" + "=" * 70)
    print("IMPORT COMPLETE!")
    print("=" * 70)
    print(f"\nTotal bets: {imported_count}")
    print(f"Pending amount: ${pending_total:.2f}")
    print(f"Expected: $561.33")
    print(f"Difference: ${561.33 - pending_total:.2f}")
    
    if abs(pending_total - 561.33) < 0.01:
        print("\n✅ PERFECT MATCH!")
    else:
        print(f"\n⚠️  Still missing ${561.33 - pending_total:.2f}")

if __name__ == "__main__":
    main()

