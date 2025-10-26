#!/bin/bash

# Extract all 404 bets by paginating through the API
# Using the exact cURL you provided

AUTH='Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJTQS1hVUczc05wcnZkSkVRSlZtTW1OVWxSLVNJOHBWZHNtSHV4enp6OUNRIn0.eyJleHAiOjE3NjE0NDU5OTYsImlhdCI6MTc2MTQ0NTY5NiwiYXV0aF90aW1lIjoxNzYxNDIyODMyLCJqdGkiOiJkNGViZjNhMC02Y2FmLTRhOWMtOWY2NC01OTJmOTc1MjcyZjciLCJpc3MiOiJodHRwczovL2FwaS5iZXRvbmxpbmUuYWcvYXBpL2F1dGgvcmVhbG1zL2JldG9ubGluZSIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjMjQ4MzE5My0wOTBkLTQ5OGQtOWFjNC0yY2YyMDljNjRkMTkiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJiZXRvbmxpbmUtd2ViIiwibm9uY2UiOiI0ZjQxNzUwMi05MmViLTQxMGQtOGU0Mi1lZDllMGZmN2QzODgiLCJzZXNzaW9uX3N0YXRlIjoiMjMyMDI2N2ItNDk5NS00ODU0LWI2MzYtNjcwM2U0MmM3M2ViIiwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iLCJkZWZhdWx0LXJvbGVzLWJldG9ubGluZSJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHRlc3QtYWNjb3VudCBzZWN1cml0eS1mbGFncyBlbWFpbCBwcm9maWxlIiwic2lkIjoiMjMyMDI2N2ItNDk5NS00ODU0LWI2MzYtNjcwM2U0MmM3M2ViIiwiYmlydGhkYXRlIjoiMTk5MS0wNi0xOSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6IkxpemV0aCBSaWRkZXIiLCJ0cnVzdGVkRGV2aWNlRW5hYmxlZCI6dHJ1ZSwicHJlZmVycmVkX3VzZXJuYW1lIjoiYjU5MjQ1NzgiLCJ0ZXN0X2FjY291bnQiOmZhbHNlLCJnaXZlbl9uYW1lIjoiTGl6ZXRoIiwiZmFtaWx5X25hbWUiOiJSaWRkZXIiLCJ0ZmEiOmZhbHNlLCJlbWFpbCI6InNhcmlkZGVyQGdtYWlsLmNvbSJ9.JnmaZBrkLqUFfd79smyCSFT34AXNaKjNYAD-jmWDA8CteCNOMUSZ_vOwcPC_SNL9lQjmak-09E5X7YO_fwMayxNdcECCpRI4K_0Fe1E0XaO0OwXqHI530Oqac5CkqWwPLKoM8AOdODHFlxJCZlKFttJ0RRFHT23Y8y4IlVAqOM9RwIHLAUNjoc0ow2yeAKzPX7XscpravVJo_TwoxpEE5k4LzfOANzsBq6pMzOSTKFIP4gBLxPMiJ5nJ7mOMUeRxLlB2SdbZHog6NPDwGy8Wq5u-QfOgKlzymALV-k6qt2_2Hz9YZ_6D35M8Qni5eM2hkZnLtDAStiaOmcUuRP7bKw'

BASE='https://api.betonline.ag/report/api/report/get-bet-history'

# Wide date range to get ALL pending bets
START_DATE='2025-01-01T00:00:00.000Z'
END_DATE='2025-12-31T23:59:59.999Z'

size=100
offset=0
page=0

echo "🚀 Fetching ALL bets from BetOnline API..."
echo ""

# Create output file
OUTPUT="all_404_bets_combined.json"
echo "[" > "$OUTPUT"

first=true

while true; do
  echo "📥 Fetching page $page (offset $offset)..."
  
  # Make the request
  response=$(curl -s 'https://api.betonline.ag/report/api/report/get-bet-history' \
    -H 'accept: application/json, text/plain, */*' \
    -H 'content-type: application/json' \
    -H "authorization: $AUTH" \
    --data-raw "{\"Id\":null,\"EndDate\":\"$END_DATE\",\"StartDate\":\"$START_DATE\",\"Status\":\"Pending\",\"Product\":null,\"WagerType\":null,\"FreePlayFlag\":null,\"StartPosition\":$offset,\"TotalPerPage\":$size,\"IsDailyFigureReport\":false}")
  
  # Check for errors
  if echo "$response" | grep -q "error\|Error\|401\|403"; then
    echo "❌ Error in response:"
    echo "$response" | head -20
    break
  fi
  
  # Extract the Data array
  data=$(echo "$response" | jq -r '.Data')
  count=$(echo "$data" | jq 'length')
  total=$(echo "$response" | jq -r '.TotalRows')
  
  echo "   ✓ Got $count bets (TotalRows=$total)"
  
  # Append to output (with comma separator)
  if [ "$first" = true ]; then
    echo "$data" | jq -c '.[]' >> "$OUTPUT"
    first=false
  else
    echo "$data" | jq -c '.[]' | sed 's/^/,/' >> "$OUTPUT"
  fi
  
  # Check if we're done
  if [ "$count" -lt "$size" ]; then
    echo "   ✓ Reached last page"
    break
  fi
  
  offset=$((offset + size))
  page=$((page + 1))
  
  # Small delay to avoid rate limiting
  sleep 0.5
done

# Close JSON array
echo "]" >> "$OUTPUT"

# Fix the JSON (remove trailing comma if any)
jq '.' "$OUTPUT" > "all_404_bets.json"
rm "$OUTPUT"

echo ""
echo "============================================================"
echo "✅ COMPLETE!"
echo "============================================================"

# Calculate totals
total_bets=$(jq 'length' all_404_bets.json)
pending_bets=$(jq '[.[] | select(.WagerStatus == "Pending")] | length' all_404_bets.json)
total_stake=$(jq '[.[] | select(.WagerStatus == "Pending") | .Risk | tonumber] | add' all_404_bets.json)
total_towin=$(jq '[.[] | select(.WagerStatus == "Pending") | .ToWin | tonumber] | add' all_404_bets.json)

echo "Total bets fetched: $total_bets"
echo "Pending bets: $pending_bets"
echo "Total stake (Risk): \$$total_stake"
echo "Total to win: \$$total_towin"
echo "============================================================"
echo ""
echo "📁 Saved to: all_404_bets.json"
echo ""
echo "Next step: python3 import_all_api_bets.py all_404_bets.json"
