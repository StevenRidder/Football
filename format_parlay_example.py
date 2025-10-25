#!/usr/bin/env python3
"""
Example of how to format a parlay bet with multiple legs.
Based on the user's actual bet data.
"""

# Example: 5-team parlay from ticket 905768987-76
parlay_bet = {
    'ticket': '905768987-76',
    'date': '10/23/2025',
    'legs': [
        'Dallas Cowboys +3½ -118',
        'Miami Dolphins +7½ -112',
        'Green Bay/Pittsburgh over 46 -110',
        'Cincinnati Bengals -6½ -108',
        'Carolina Panthers +7½ -116'
    ],
    'type': 'Parlay',
    'status': 'Pending',
    'amount': 1.00,
    'to_win': 22.93
}

# Format for pasting into the web interface
formatted = f"{parlay_bet['ticket']}|{parlay_bet['date']}|"
formatted += '|'.join(parlay_bet['legs'])
formatted += f"|{parlay_bet['type']}|{parlay_bet['status']}|{parlay_bet['amount']:.2f}|{parlay_bet['to_win']:.2f}"

print("=" * 80)
print("FORMATTED PARLAY BET - COPY THIS LINE:")
print("=" * 80)
print()
print(formatted)
print()
print("=" * 80)
print(f"This parlay has {len(parlay_bet['legs'])} legs")
print("=" * 80)
print()
print("When you click on this bet in the web interface, you'll see:")
for i, leg in enumerate(parlay_bet['legs'], 1):
    print(f"  {i}. {leg}")
print()
print("Instructions:")
print("1. Copy the line above (between the === marks)")
print("2. Go to http://localhost:9876/bets")
print("3. Paste into the text area")
print("4. Click 'Load Bets'")
print("5. Click on the parlay row to see all legs in the modal")
print()

