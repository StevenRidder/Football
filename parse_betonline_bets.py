#!/usr/bin/env python3
"""
Parse BetOnline bet data and save to JSON for display
"""
import json
from datetime import datetime
from pathlib import Path

# Load from file
with open('artifacts/betonline_bets_raw.txt', 'r') as f:
    bets_data = f.read()

def parse_amount(amount_str):
    """Parse amount string like '$6.33' or '$37,377.61' to float"""
    if amount_str == '-':
        return 0.0
    return float(amount_str.replace('$', '').replace(',', ''))

def parse_bets(data_str):
    """Parse bet data into structured format"""
    bets = []
    lines = [line.strip() for line in data_str.strip().split('\n') if line.strip()]
    
    for line in lines:
        parts = line.split('|')
        if len(parts) >= 6:
            ticket = parts[0].strip()
            date = parts[1].strip()
            description = parts[2].strip()
            bet_type = parts[3].strip()
            status = parts[4].strip()
            amount = float(parts[5].strip())
            to_win = float(parts[6].strip()) if len(parts) > 6 else 0.0
            
            # Calculate profit based on status
            if status == 'Won':
                profit = to_win
            elif status == 'Lost':
                profit = -amount
            else:  # Pending
                profit = 0.0
            
            bets.append({
                'ticket_id': ticket,
                'date': date,
                'description': description,
                'type': bet_type,
                'status': status,
                'amount': amount,
                'to_win': to_win,
                'profit': profit
            })
    
    return bets

def main():
    bets = parse_bets(bets_data)
    
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
    
    # Save to JSON
    output = {
        'timestamp': datetime.now().isoformat(),
        'summary': summary,
        'bets': bets
    }
    
    Path('artifacts').mkdir(exist_ok=True)
    with open('artifacts/betonline_bets.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Parsed {len(bets)} bets")
    print(f"   Total Amount: ${total_amount:.2f}")
    print(f"   Total Profit: ${total_profit:.2f}")
    print(f"   Pending: {len(pending_bets)} bets (${pending_amount:.2f})")
    print(f"   Potential Win: ${potential_win:.2f}")
    print("\n✅ Saved to artifacts/betonline_bets.json")

if __name__ == "__main__":
    main()

