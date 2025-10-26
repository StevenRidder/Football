#!/usr/bin/env python3
"""
Import bet data from manually copied Network tab responses.
Handles multiple JSON files or a single concatenated file.
"""

import json
import sys
from pathlib import Path
from betting_db import BettingDB

def load_json_files(directory_or_file):
    """Load JSON from a directory of files or a single file."""
    path = Path(directory_or_file)
    all_bets = []
    
    if path.is_file():
        print(f"📄 Loading from file: {path}")
        with open(path, 'r') as f:
            content = f.read().strip()
            
            # Try to parse as single JSON
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    all_bets.extend(data)
                elif isinstance(data, dict) and 'Data' in data:
                    all_bets.extend(data['Data'])
                else:
                    all_bets.append(data)
            except json.JSONDecodeError:
                # Try to split by }{ pattern (concatenated JSONs)
                print("  Trying to split concatenated JSON objects...")
                parts = content.replace('}{', '}|||{').split('|||')
                for i, part in enumerate(parts):
                    try:
                        data = json.loads(part)
                        if isinstance(data, dict) and 'Data' in data:
                            all_bets.extend(data['Data'])
                            print(f"    ✓ Parsed chunk {i+1}: {len(data['Data'])} bets")
                        elif isinstance(data, list):
                            all_bets.extend(data)
                            print(f"    ✓ Parsed chunk {i+1}: {len(data)} bets")
                    except json.JSONDecodeError as e:
                        print(f"    ✗ Failed to parse chunk {i+1}: {e}")
    
    elif path.is_dir():
        print(f"📁 Loading from directory: {path}")
        json_files = sorted(path.glob('*.json'))
        
        for json_file in json_files:
            print(f"  Reading: {json_file.name}")
            with open(json_file, 'r') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_bets.extend(data)
                    elif isinstance(data, dict) and 'Data' in data:
                        all_bets.extend(data['Data'])
                        print(f"    ✓ Found {len(data['Data'])} bets")
                    else:
                        all_bets.append(data)
                except json.JSONDecodeError as e:
                    print(f"    ✗ Error: {e}")
    
    else:
        print(f"❌ Path not found: {path}")
        sys.exit(1)
    
    return all_bets

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_network_responses.py <file_or_directory>")
        print("\nExamples:")
        print("  python import_network_responses.py network_responses.json")
        print("  python import_network_responses.py ~/Downloads/")
        print("  python import_network_responses.py all_404_bets_complete.json")
        sys.exit(1)
    
    source = sys.argv[1]
    
    print("=" * 60)
    print("IMPORTING BETS FROM NETWORK RESPONSES")
    print("=" * 60)
    
    # Load all bets
    all_bets = load_json_files(source)
    print(f"\n📊 Total bets loaded: {len(all_bets)}")
    
    if not all_bets:
        print("❌ No bets found!")
        sys.exit(1)
    
    # Deduplicate by TicketNumber
    unique_bets = {}
    for bet in all_bets:
        ticket_num = bet.get('TicketNumber')
        if ticket_num and ticket_num not in unique_bets:
            unique_bets[ticket_num] = bet
    
    print(f"📊 Unique bets: {len(unique_bets)}")
    
    # Import to database
    db = BettingDB()
    
    imported = 0
    skipped = 0
    errors = 0
    
    for bet in unique_bets.values():
        try:
            # Check if already exists
            existing = db.get_bet_by_ticket(bet.get('TicketNumber'))
            if existing:
                skipped += 1
                continue
            
            # Import
            db.import_bet(bet)
            imported += 1
            
        except Exception as e:
            print(f"❌ Error importing bet {bet.get('TicketNumber')}: {e}")
            errors += 1
    
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"✅ Imported: {imported}")
    print(f"⏭️  Skipped (already exists): {skipped}")
    print(f"❌ Errors: {errors}")
    print("=" * 60)
    
    # Show summary
    stats = db.get_bet_summary()
    print(f"\n📊 DATABASE SUMMARY:")
    print(f"   Total bets: {stats['total_bets']}")
    print(f"   Pending: {stats['pending_bets']}")
    print(f"   Total stake: ${stats['total_stake']:.2f}")
    print(f"   Potential win: ${stats['potential_win']:.2f}")

if __name__ == '__main__':
    main()

