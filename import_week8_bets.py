#!/usr/bin/env python3
"""
Import ALL 404 bets from the week 8.txt file
"""
import json
from dateutil import parser as date_parser
from nfl_edge.bets.db import BettingDB

# Read the file
print("📖 Reading week 8 .txt file...")
with open('/Users/steveridder/Dropbox/Mac/Downloads/week 8 .txt', 'r') as f:
    content = f.read()

# Split into multiple JSON objects
# The file has multiple {"TotalRows": 404, "Data": [...]} objects
print("🔍 Parsing multiple JSON responses...")
json_objects = []
current_pos = 0

while True:
    # Find the start of next JSON object
    start = content.find('{', current_pos)
    if start == -1:
        break
    
    # Find the matching closing brace
    brace_count = 0
    end = start
    for i in range(start, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break
    
    if end > start:
        json_str = content[start:end]
        try:
            obj = json.loads(json_str)
            if 'Data' in obj and 'TotalRows' in obj:
                json_objects.append(obj)
                print(f"  ✓ Found response with {len(obj['Data'])} bets")
        except:
            pass
        current_pos = end
    else:
        break

print(f"\n✅ Found {len(json_objects)} API responses")

# Extract all unique bets
all_bets = {}
for response in json_objects:
    for bet in response.get('Data', []):
        bet_id = bet['Id']
        if bet_id not in all_bets:
            all_bets[bet_id] = bet

bets = list(all_bets.values())
print(f"📊 Total unique bets: {len(bets)}")

# Connect to database
print("\n💾 Importing to database...")
db = BettingDB()
db.connect()

# Clear existing data
cursor = db.conn.cursor()
cursor.execute("DELETE FROM parlay_legs")
cursor.execute("DELETE FROM bets")
db.conn.commit()
print("  ✓ Cleared existing data")

# Import all bets
imported = 0
errors = 0

for bet in bets:
    try:
        # Parse date - handle missing milliseconds
        date_str = bet['Date']
        if not date_str.endswith('Z'):
            date_str += 'Z'
        # Add milliseconds if missing
        if '.' not in date_str:
            date_str = date_str.replace('Z', '.000Z')
        elif len(date_str.split('.')[-1]) < 4:  # Less than 3 digits + Z
            # Pad milliseconds to 3 digits
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
        
        if imported % 50 == 0:
            print(f"  Imported {imported}/{len(bets)} bets...")
            
    except Exception as e:
        errors += 1
        if errors <= 5:  # Only show first 5 errors
            print(f"  ❌ Error importing bet {bet.get('Id')}: {e}")

db.conn.commit()

# Get summary
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
print(f"Pending stake: ${float(result['stake'] or 0):.2f}")
print(f"Pending to win: ${float(result['to_win'] or 0):.2f}")
print(f"Errors: {errors}")
print("=" * 60)

db.close()

