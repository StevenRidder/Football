#!/bin/bash

AUTH='Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJTQS1hVUczc05wcnZkSkVRSlZtTW1OVWxSLVNJOHBWZHNtSHV4enp6OUNRIn0.eyJleHAiOjE3NjE0NDg3NDQsImlhdCI6MTc2MTQ0ODQ0NCwiYXV0aF90aW1lIjoxNzYxNDIyODMyLCJqdGkiOiJjODlkMTA1NS03Yzc2LTQ1ZTQtYTlmNS04NGU5OTk2OThhNjQiLCJpc3MiOiJodHRwczovL2FwaS5iZXRvbmxpbmUuYWcvYXBpL2F1dGgvcmVhbG1zL2JldG9ubGluZSIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjMjQ4MzE5My0wOTBkLTQ5OGQtOWFjNC0yY2YyMDljNjRkMTkiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJiZXRvbmxpbmUtd2ViIiwibm9uY2UiOiI0MjkyNDY4Yy00YmVhLTQ3MjAtOTE0Ny1hYzFjOWI2YmQwNzEiLCJzZXNzaW9uX3N0YXRlIjoiMjMyMDI2N2ItNDk5NS00ODU0LWI2MzYtNjcwM2U0MmM3M2ViIiwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iLCJkZWZhdWx0LXJvbGVzLWJldG9ubGluZSJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHRlc3QtYWNjb3VudCBzZWN1cml0eS1mbGFncyBlbWFpbCBwcm9maWxlIiwic2lkIjoiMjMyMDI2N2ItNDk5NS00ODU0LWI2MzYtNjcwM2U0MmM3M2ViIiwiYmlydGhkYXRlIjoiMTk5MS0wNi0xOSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6IkxpemV0aCBSaWRkZXIiLCJ0cnVzdGVkRGV2aWNlRW5hYmxlZCI6dHJ1ZSwicHJlZmVycmVkX3VzZXJuYW1lIjoiYjU5MjQ1NzgiLCJ0ZXN0X2FjY291bnQiOmZhbHNlLCJnaXZlbl9uYW1lIjoiTGl6ZXRoIiwiZmFtaWx5X25hbWUiOiJSaWRkZXIiLCJ0ZmEiOmZhbHNlLCJlbWFpbCI6InNhcmlkZGVyQGdtYWlsLmNvbSJ9.ZkCUq-VrS42LoMbC7UbqVfdYkcMiQ1GtPKjdBPOe8ywEj3ZgbAvV90G3UZ3-79di9giKrgqeGke6Zb0HEft1-WLG6I2hmowlsdjzlTAxaOKMUu8ehkyWlgAkOmWlHI4xXu7WydJSMM-bo2UJC4Jc6TkbVeLxCxUDTEFFp8aVjZsw3R1OAgDxylh0RWIeFsXhAOLXZAjLo7ar4-PrNTcKMICEw6YXLxnh56SBQeDULAMXFz216Wkjeyv8SUsS0xPuHbfF95p0WJeyNzaJYvVbILtzZiI13UbGZxgc_4HcGNww_TFF0Vo2S-uVFJMzKEFhkAnl0dGz5ily10o8edDJ8A'

BASE='https://api.betonline.ag/report/api/report/get-bet-history'
START_DATE='2025-10-22T00:00:00.000Z'
END_DATE='2025-12-31T23:59:59.999Z'

size=100
offset=0

echo "🚀 Fetching ALL bets since 10/22/25..."
echo ""

# Collect all responses
all_data="[]"

while true; do
  echo "📥 Fetching offset $offset..."
  
  response=$(curl -s "$BASE" \
    -H 'accept: application/json, text/plain, */*' \
    -H 'content-type: application/json' \
    -H "authorization: $AUTH" \
    -H 'origin: https://www.betonline.ag' \
    -H 'referer: https://www.betonline.ag/' \
    --data-raw "{\"Id\":null,\"EndDate\":\"$END_DATE\",\"StartDate\":\"$START_DATE\",\"Status\":\"Pending\",\"Product\":null,\"WagerType\":null,\"FreePlayFlag\":null,\"StartPosition\":$offset,\"TotalPerPage\":$size,\"IsDailyFigureReport\":false}")
  
  # Check for Cloudflare block
  if echo "$response" | grep -q "Cloudflare\|challenge"; then
    echo "❌ Cloudflare blocked the request"
    break
  fi
  
  # Check for errors
  if echo "$response" | grep -q "error\|Error"; then
    echo "❌ Error in response"
    break
  fi
  
  # Extract count and total
  count=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('Data', [])))" 2>/dev/null || echo "0")
  total=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('TotalRows', 0))" 2>/dev/null || echo "0")
  
  echo "   ✓ Got $count bets (TotalRows=$total)"
  
  # Save this page
  echo "$response" > "page_${offset}.json"
  
  if [ "$count" -lt "$size" ]; then
    echo "   ✓ Reached last page"
    break
  fi
  
  offset=$((offset + size))
  sleep 1.5
done

echo ""
echo "Combining all pages..."

# Combine all pages using Python
python3 << 'PYTHON'
import json
import glob

all_bets = []
seen = set()

for file in sorted(glob.glob('page_*.json')):
    try:
        with open(file, 'r') as f:
            data = json.load(f)
            for bet in data.get('Data', []):
                key = f"{bet['TicketNumber']}|{bet['PlacedDate']}"
                if key not in seen:
                    seen.add(key)
                    all_bets.append(bet)
    except:
        pass

# Calculate totals
pending = [b for b in all_bets if b.get('WagerStatus') == 'Pending']
stake = sum(float(b.get('Risk', 0)) for b in pending)
to_win = sum(float(b.get('ToWin', 0)) for b in pending)

print(f"\n{'='*60}")
print(f"✅ COMPLETE!")
print(f"{'='*60}")
print(f"Total bets fetched: {len(all_bets)}")
print(f"Pending bets: {len(pending)}")
print(f"Total stake (Risk): ${stake:.2f}")
print(f"Total to win: ${to_win:.2f}")
print(f"{'='*60}\n")

# Save
with open('week8_bets.json', 'w') as f:
    json.dump(all_bets, f, indent=2)

print("📁 Saved to: week8_bets.json")
PYTHON

# Cleanup
rm -f page_*.json

echo ""
echo "✅ Done! Now importing into database..."
