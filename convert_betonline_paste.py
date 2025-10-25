#!/usr/bin/env python3
"""
Convert raw BetOnline paste data to the format needed for the web interface.
Just paste your raw BetOnline data and this will format it correctly.
"""

import re
import sys

def parse_raw_betonline(text):
    """Parse raw BetOnline text and convert to pipe-delimited format"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Extract fields
    ticket_id = None
    date = None
    bet_type = None
    status = None
    amount = None
    to_win = None
    legs = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for ticket number (usually first line or after "Ticket Number:")
        if re.match(r'^\d{9}-\d+$', line):
            ticket_id = line
        elif line.startswith('Ticket Number:') and i + 1 < len(lines):
            ticket_id = lines[i + 1]
            i += 1
        
        # Look for date (MM/DD/YYYY format)
        elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', line):
            date = line
        elif line.startswith('Accepted Date:') and i + 1 < len(lines):
            date_line = lines[i + 1]
            # Convert "10/25/25" to "10/25/2025"
            date_match = re.match(r'(\d{1,2}/\d{1,2})/(\d{2})', date_line)
            if date_match:
                date = f"{date_match.group(1)}/20{date_match.group(2)}"
            i += 1
        
        # Look for type
        elif line in ['Same Game Parlay', 'Parlay', 'Spread', 'Total', 'Moneyline', 'Live'] and not bet_type:
            bet_type = line
        elif line.startswith('Type:'):
            # Extract type from "Type: Same Game Parlay" format
            bet_type = line.replace('Type:', '').strip()
            if not bet_type and i + 1 < len(lines):
                bet_type = lines[i + 1]
                i += 1
        
        # Look for status
        elif line in ['Pending', 'Won', 'Lost', 'Push']:
            status = line
        elif line.startswith('Status:') and i + 1 < len(lines):
            status = lines[i + 1]
            i += 1
        
        # Look for amount
        elif line.startswith('$') and amount is None:
            amount = float(line.replace('$', '').replace(',', ''))
        elif line.startswith('Amount:') and i + 1 < len(lines):
            amount = float(lines[i + 1].replace('$', '').replace(',', ''))
            i += 1
        
        # Look for to_win
        elif line.startswith('$') and amount is not None and to_win is None:
            to_win = float(line.replace('$', '').replace(',', ''))
        elif line.startswith('To win:') and i + 1 < len(lines):
            to_win = float(lines[i + 1].replace('$', '').replace(',', ''))
            i += 1
        
        # Look for description/legs
        elif line.startswith('Description:'):
            # Everything after "Description:" until the end or next section is legs
            i += 1
            while i < len(lines):
                leg_line = lines[i].strip()
                # Skip empty lines, section headers, and game titles
                if (leg_line and not leg_line.endswith(':') and 
                    leg_line not in ['Pending', 'Won', 'Lost'] and
                    not leg_line.startswith('FOOTBALL') and
                    leg_line not in legs):  # Avoid duplicates
                    # Clean up the leg
                    leg_line = leg_line.replace(' (Game)', '').strip()
                    if leg_line:
                        legs.append(leg_line)
                i += 1
            break
        
        # Also catch legs in the initial format (with |)
        elif '|' in line and ('FOOTBALL' in line or 'Total points' in line):
            # Split by | and clean up
            parts = [p.strip().replace(' (Game)', '') for p in line.split('|')]
            for p in parts:
                if p and not p.startswith('FOOTBALL') and p not in legs:
                    legs.append(p)
        
        i += 1
    
    return {
        'ticket_id': ticket_id,
        'date': date,
        'bet_type': bet_type,
        'status': status,
        'amount': amount,
        'to_win': to_win,
        'legs': legs
    }

def format_for_web(bet):
    """Format parsed bet data for web interface"""
    if not all([bet['ticket_id'], bet['date'], bet['bet_type'], bet['status'], 
                bet['amount'] is not None, bet['to_win'] is not None]):
        return None
    
    # Build the formatted line
    parts = [
        bet['ticket_id'],
        bet['date']
    ]
    
    # Add legs (or description if no legs)
    if bet['legs']:
        parts.extend(bet['legs'])
    else:
        parts.append('No description')
    
    # Add final fields
    parts.extend([
        bet['bet_type'],
        bet['status'],
        f"{bet['amount']:.2f}",
        f"{bet['to_win']:.2f}"
    ])
    
    return '|'.join(parts)

def main():
    print("=" * 80)
    print("BETONLINE BET CONVERTER")
    print("=" * 80)
    print()
    print("Paste your raw BetOnline bet data below.")
    print("Press Ctrl+D (Mac/Linux) or Ctrl+Z then Enter (Windows) when done:")
    print()
    
    # Read from stdin
    raw_text = sys.stdin.read()
    
    # Parse the bet
    bet = parse_raw_betonline(raw_text)
    
    print("\n" + "=" * 80)
    print("PARSED DATA:")
    print("=" * 80)
    print(f"Ticket: {bet['ticket_id']}")
    print(f"Date: {bet['date']}")
    print(f"Type: {bet['bet_type']}")
    print(f"Status: {bet['status']}")
    print(f"Amount: ${bet['amount']:.2f}")
    print(f"To Win: ${bet['to_win']:.2f}")
    print(f"Legs: {len(bet['legs'])}")
    for i, leg in enumerate(bet['legs'], 1):
        print(f"  {i}. {leg}")
    
    # Format for web
    formatted = format_for_web(bet)
    
    if formatted:
        print("\n" + "=" * 80)
        print("FORMATTED FOR WEB INTERFACE - COPY THIS LINE:")
        print("=" * 80)
        print()
        print(formatted)
        print()
        print("=" * 80)
        print()
        print("Instructions:")
        print("1. Copy the line above (between the === marks)")
        print("2. Go to http://localhost:9876/bets")
        print("3. Paste into the text area")
        print("4. Click 'Load Bets'")
        print()
    else:
        print("\n❌ ERROR: Could not parse all required fields")
        print("Make sure your paste includes: Ticket #, Date, Type, Status, Amount, To Win")

if __name__ == "__main__":
    main()

