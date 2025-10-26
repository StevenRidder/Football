#!/bin/bash

# BetOnline Bet Fetcher using curl
# This will prompt you for a fresh Bearer token and fetch ALL bets

echo "=================================================="
echo "BetOnline Bet Fetcher"
echo "=================================================="
echo ""
echo "INSTRUCTIONS:"
echo "1. Open BetOnline in your browser"
echo "2. Go to My Account -> Bet History"
echo "3. Open DevTools -> Network tab"
echo "4. Find a 'get-bet-history' request"
echo "5. Copy the Authorization header value"
echo ""
read -p "Paste Bearer token (starts with 'Bearer eyJ...'): " AUTH

if [[ ! $AUTH =~ ^Bearer ]]; then
    echo "❌ Invalid token! Must start with 'Bearer '"
    exit 1
fi

echo ""
echo "🚀 Fetching bets..."
echo ""

BASE_URL="https://api.betonline.ag/report/api/report/get-bet-history"
START_DATE="2025-01-01T00:00:00.000Z"
END_DATE="2025-12-31T23:59:59.999Z"
PAGE_SIZE=100

OUTPUT_FILE="/Users/steveridder/Git/Football/artifacts/betonline_all_bets_curl.json"
TEMP_FILE="/tmp/betonline_bets_temp.json"

# Clear output file
echo "[" > "$OUTPUT_FILE"

OFFSET=0
TOTAL_FETCHED=0
FIRST=true

while [ $OFFSET -lt 1000 ]; do
    echo "📥 Fetching offset $OFFSET..."
    
    RESPONSE=$(curl -s "$BASE_URL" \
        -H "accept: application/json, text/plain, */*" \
        -H "content-type: application/json" \
        -H "authorization: $AUTH" \
        --data-raw "{\"Id\":null,\"StartDate\":\"$START_DATE\",\"EndDate\":\"$END_DATE\",\"Status\":null,\"Product\":null,\"WagerType\":null,\"FreePlayFlag\":null,\"StartPosition\":$OFFSET,\"TotalPerPage\":$PAGE_SIZE,\"IsDailyFigureReport\":false}")
    
    # Check if response contains error
    if echo "$RESPONSE" | grep -q "401\|403\|error"; then
        echo "❌ Auth failed! Token expired or invalid."
        echo "$RESPONSE"
        exit 1
    fi
    
    # Extract Data array
    DATA=$(echo "$RESPONSE" | jq -r '.Data // []')
    COUNT=$(echo "$DATA" | jq 'length')
    
    if [ "$COUNT" -eq "null" ] || [ "$COUNT" -eq "0" ]; then
        echo "✅ No more data. Stopping."
        break
    fi
    
    echo "   Got $COUNT bets"
    
    # Append to output (with comma if not first)
    if [ "$FIRST" = true ]; then
        echo "$DATA" | jq -c '.[]' >> "$OUTPUT_FILE"
        FIRST=false
    else
        echo "$DATA" | jq -c '.[]' | sed 's/^/,/' >> "$OUTPUT_FILE"
    fi
    
    TOTAL_FETCHED=$((TOTAL_FETCHED + COUNT))
    
    if [ "$COUNT" -lt "$PAGE_SIZE" ]; then
        echo "✅ Reached end of data."
        break
    fi
    
    OFFSET=$((OFFSET + PAGE_SIZE))
    sleep 1.5
done

# Close JSON array
echo "]" >> "$OUTPUT_FILE"

# Fix JSON formatting
jq '.' "$OUTPUT_FILE" > "$TEMP_FILE" && mv "$TEMP_FILE" "$OUTPUT_FILE"

echo ""
echo "=================================================="
echo "✅ SUCCESS!"
echo "=================================================="
echo "Total bets fetched: $TOTAL_FETCHED"
echo "Saved to: $OUTPUT_FILE"
echo ""

# Calculate summary
PENDING_COUNT=$(jq '[.[] | select(.WagerStatus == "Pending")] | length' "$OUTPUT_FILE")
PENDING_STAKE=$(jq '[.[] | select(.WagerStatus == "Pending") | .Risk | tonumber] | add' "$OUTPUT_FILE")
PENDING_TO_WIN=$(jq '[.[] | select(.WagerStatus == "Pending") | .ToWin | tonumber] | add' "$OUTPUT_FILE")

echo "Pending bets: $PENDING_COUNT"
echo "Pending stake: \$$PENDING_STAKE"
echo "Pending to win: \$$PENDING_TO_WIN"
echo "=================================================="

