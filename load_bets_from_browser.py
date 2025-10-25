#!/usr/bin/env python3
"""
Load all bet data extracted from the browser into the system.
"""
import json
import re

# Read the browser evaluation log
with open('/Users/steveridder/.cursor/browser-logs/browser_evaluate-2025-10-25T21-43-41-393Z.log', 'r') as f:
    content = f.read()

# Extract the JSON result
json_start = content.find('{')
# Find the end of the first complete JSON object
brace_count = 0
json_end = json_start
for i in range(json_start, len(content)):
    if content[i] == '{':
        brace_count += 1
    elif content[i] == '}':
        brace_count -= 1
        if brace_count == 0:
            json_end = i + 1
            break

data = json.loads(content[json_start:json_end])
all_text = data.get('all', '')

# Split by the separator
bet_entries = all_text.split('---')

print(f"Found {len(bet_entries)} bet entries")

# Parse each bet entry looking for structured data
parsed_bets = []
for entry in bet_entries:
    entry = entry.strip()
    if not entry or len(entry) < 50:
        continue
    
    # Look for "Ticket Number:" pattern
    ticket_match = re.search(r'Ticket Number:\s*(\d{9}-\d+)', entry)
    if not ticket_match:
        continue
    
    ticket = ticket_match.group(1)
    
    # Extract date
    date_match = re.search(r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})', entry)
    date = date_match.group(1) if date_match else ''
    
    # Extract type
    type_match = re.search(r'Type:\s*([^\n]+)', entry)
    bet_type = type_match.group(1).strip() if type_match else ''
    
    # Extract status
    status_match = re.search(r'Status\s*([A-Za-z]+)', entry)
    status = status_match.group(1) if status_match else 'Pending'
    
    # Extract amount
    amount_match = re.search(r'Amount\s*\$?([\d,]+\.?\d*)', entry)
    amount = f"${amount_match.group(1)}" if amount_match else ''
    
    # Extract to win
    to_win_match = re.search(r'To win\s*\$?([\d,]+\.?\d*)', entry)
    to_win = f"${to_win_match.group(1)}" if to_win_match else ''
    
    # Extract description - look for "Description:" section
    desc_match = re.search(r'Description:\s*([^\n]+(?:\n(?!Type:|Status|Amount|To win)[^\n]+)*)', entry, re.MULTILINE)
    if desc_match:
        description = desc_match.group(1).strip()
        # Clean up description
        description = re.sub(r'\s+', ' ', description)
        # Remove "Desktop - " prefix
        description = description.replace('Desktop - ', '')
    else:
        # Fallback: try to extract from the beginning
        lines = entry.split('\n')
        description = ''
        for line in lines:
            if 'FOOTBALL' in line or 'Parlay' in line:
                description = line.strip()
                break
    
    # Limit description length
    if len(description) > 300:
        description = description[:300] + '...'
    
    parsed_bets.append({
        'ticket': ticket,
        'date': date,
        'description': description,
        'type': bet_type,
        'status': status,
        'amount': amount,
        'to_win': to_win
    })

# Remove duplicates based on ticket number
seen_tickets = set()
unique_bets = []
for bet in parsed_bets:
    if bet['ticket'] not in seen_tickets:
        seen_tickets.add(bet['ticket'])
        unique_bets.append(bet)

print(f"Parsed {len(unique_bets)} unique bets")

# Calculate summary
total_pending = sum(1 for b in unique_bets if b['status'] == 'Pending')
total_won = sum(1 for b in unique_bets if b['status'] == 'Won')
total_lost = sum(1 for b in unique_bets if b['status'] == 'Lost')

# Calculate total amounts
def parse_amount(amt_str):
    if not amt_str or amt_str == '-':
        return 0.0
    return float(amt_str.replace('$', '').replace(',', ''))

total_risked = sum(parse_amount(b['amount']) for b in unique_bets if b['status'] == 'Pending')
total_to_win = sum(parse_amount(b['to_win']) for b in unique_bets if b['status'] == 'Pending')

# Save to JSON
output = {
    'bets': unique_bets,
    'summary': {
        'total_bets': len(unique_bets),
        'pending': total_pending,
        'won': total_won,
        'lost': total_lost,
        'total_risked': f"${total_risked:.2f}",
        'total_to_win': f"${total_to_win:.2f}"
    }
}

with open('artifacts/betonline_bets.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Successfully loaded {len(unique_bets)} bets!")
print(f"📊 Summary:")
print(f"   Pending: {total_pending}")
print(f"   Won: {total_won}")
print(f"   Lost: {total_lost}")
print(f"   Total Risked: ${total_risked:.2f}")
print(f"   Total To Win: ${total_to_win:.2f}")
print(f"\n💾 Saved to artifacts/betonline_bets.json")

# Show first 5 bets
print("\n📋 First 5 bets:")
for bet in unique_bets[:5]:
    print(f"  {bet['ticket']} | {bet['date']} | {bet['type']} | {bet['status']} | {bet['amount']} -> {bet['to_win']}")

