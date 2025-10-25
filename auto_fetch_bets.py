#!/usr/bin/env python3
"""
Automatically fetch all your BetOnline bets using saved session.

Run this anytime to get your latest bets!
"""

import json
from pathlib import Path
from datetime import datetime
from nfl_edge.bets.betonline_client import fetch_all_bets, normalize_to_ledger

def auto_fetch():
    print("=" * 80)
    print("BETONLINE AUTO-FETCH")
    print("=" * 80)
    print()
    
    # Load saved session
    session_file = Path("artifacts/betonline_session.json")
    
    if not session_file.exists():
        print("❌ ERROR: No saved session found!")
        print()
        print("You need to run the one-time setup first:")
        print("  python3 setup_betonline_auto_fetch.py")
        print()
        return False
    
    print("⏳ Loading saved session...")
    with open(session_file, 'r') as f:
        headers = json.load(f)
    
    print("✅ Session loaded")
    print()
    print("⏳ Fetching your bets from BetOnline...")
    
    try:
        # Fetch all bets
        raw_data = fetch_all_bets(headers)
        ledger_df = normalize_to_ledger(raw_data)
        
        if ledger_df.empty:
            print("\n⚠️ WARNING: No bets found.")
            print()
            print("This could mean:")
            print("  1. You have no bets on BetOnline")
            print("  2. Your session has expired (run setup again)")
            print("  3. BetOnline's API has changed")
            print()
            print("To fix: python3 setup_betonline_auto_fetch.py")
            return False
        
        # Convert to the format needed for the web interface
        bets = []
        for _, row in ledger_df.iterrows():
            # Build description from available fields
            desc_parts = []
            if row['market']:
                desc_parts.append(row['market'])
            if row['submarket']:
                desc_parts.append(row['submarket'])
            if row['line']:
                desc_parts.append(f"Line: {row['line']}")
            if row['odds_american']:
                desc_parts.append(f"Odds: {row['odds_american']}")
            
            description = ' | '.join(desc_parts) if desc_parts else 'No description'
            
            # Determine status
            if row['settlement'] == 'Pending':
                status = 'Pending'
            elif row['result'] == 'Win':
                status = 'Won'
            elif row['result'] == 'Loss':
                status = 'Lost'
            else:
                status = row['settlement']
            
            # Calculate profit
            if status == 'Won':
                profit = row['profit']
            elif status == 'Lost':
                profit = -row['stake']
            else:
                profit = 0.0
            
            bets.append({
                'ticket_id': str(row['ticket_id']),
                'date': row['placed_utc'][:10] if row['placed_utc'] else '',
                'description': description,
                'type': row['market'] or 'Unknown',
                'status': status,
                'amount': float(row['stake']),
                'to_win': float(row['profit']) if row['profit'] else 0.0,
                'profit': float(profit)
            })
        
        # Calculate summary
        total_amount = sum(b['amount'] for b in bets)
        total_profit = sum(b['profit'] for b in bets)
        pending_amount = sum(b['amount'] for b in bets if b['status'] == 'Pending')
        potential_win = sum(b['to_win'] for b in bets if b['status'] == 'Pending')
        
        won_bets = [b for b in bets if b['status'] == 'Won']
        lost_bets = [b for b in bets if b['status'] == 'Lost']
        pending_bets = [b for b in bets if b['status'] == 'Pending']
        
        summary = {
            'total_bets': len(bets),
            'total_amount': total_amount,
            'total_profit': total_profit,
            'pending_amount': pending_amount,
            'potential_win': potential_win,
            'won_count': len(won_bets),
            'lost_count': len(lost_bets),
            'pending_count': len(pending_bets),
            'win_rate': (len(won_bets) / (len(won_bets) + len(lost_bets)) * 100) if (len(won_bets) + len(lost_bets)) > 0 else 0
        }
        
        # Save to JSON for web interface
        output = {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'bets': bets
        }
        
        output_file = Path('artifacts/betonline_bets.json')
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✅ SUCCESS! Fetched {len(bets)} bets")
        print(f"✅ Saved to {output_file}")
        
        # Show summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Bets: {len(bets)}")
        print(f"Total Wagered: ${total_amount:.2f}")
        print(f"Total Profit/Loss: ${total_profit:.2f}")
        print(f"Pending: {len(pending_bets)} bets (${pending_amount:.2f})")
        print(f"Potential Win: ${potential_win:.2f}")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        
        print("\n" + "=" * 80)
        print("VIEW YOUR BETS")
        print("=" * 80)
        print("Go to: http://localhost:9876/bets")
        print("Your bets are now loaded and ready to view!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print()
        print("Your session may have expired. Run setup again:")
        print("  python3 setup_betonline_auto_fetch.py")
        return False

if __name__ == "__main__":
    success = auto_fetch()
    if not success:
        exit(1)
    else:
        exit(0)

