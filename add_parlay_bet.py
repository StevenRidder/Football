#!/usr/bin/env python3
"""
Quick script to add a parlay bet to the database
"""
import sys
sys.path.insert(0, '/Users/steveridder/Git/Football')

from nfl_edge.bets.db import BettingDB

# Parse the parlay bet
ticket_number = "905966563-1"
date = "2025-10-24"
bet_type = "Parlay"
status = "Pending"
amount = 15.00
to_win = 37377.61

# Individual legs
legs = [
    "CAR +7",
    "NYG +7.5",
    "MIA +7.5",
    "CIN -6.5",
    "NE -7",
    "CHI +6.5",
    "TB -3.5",
    "DEN -3.5",
    "HOU -2.5",
    "GB -3",
    "WAS +12.5",
    "TEN +14.5"
]

description = f"12-team parlay: {', '.join(legs)}"

# Add to database
db = BettingDB()
try:
    db.insert_bet({
        'ticket_id': ticket_number,
        'date': date,
        'description': description,
        'bet_type': bet_type,
        'status': status,
        'amount': amount,
        'to_win': to_win
    })
    print(f"✅ Added parlay bet {ticket_number}")
    print(f"   Amount: ${amount:.2f}")
    print(f"   To Win: ${to_win:.2f}")
    print(f"   Legs: {len(legs)}")
finally:
    db.close()

