#!/usr/bin/env python3
"""
Fetch ALL pages from BetOnline API to get the complete bet history.
"""
import requests
import json
from datetime import datetime, timedelta

# Parse headers from the cURL
headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJTQS1hVUczc05wcnZkSkVRSlZtTW1OVWxSLVNJOHBWZHNtSHV4enp6OUNRIn0.eyJleHAiOjE3NjE0NDQwNTAsImlhdCI6MTc2MTQ0Mzc1MCwiYXV0aF90aW1lIjoxNzYxNDIyODMyLCJqdGkiOiIzZTZiNjkyMC1mMjk3LTQyNmEtODVhYS00YmEzMGFkMGQyYzIiLCJpc3MiOiJodHRwczovL2FwaS5iZXRvbmxpbmUuYWcvYXBpL2F1dGgvcmVhbG1zL2JldG9ubGluZSIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjMjQ4MzE5My0wOTBkLTQ5OGQtOWFjNC0yY2YyMDljNjRkMTkiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJiZXRvbmxpbmUtd2ViIiwibm9uY2UiOiJhOTBlYmVjZS03ODUzLTQxMDctYjFjMC01OWFmNDhhOGY4MWQiLCJzZXNzaW9uX3N0YXRlIjoiMjMyMDI2N2ItNDk5NS00ODU0LWI2MzYtNjcwM2U0MmM3M2ViIiwiYmlydGhkYXRlIjoiMTk5MS0wNi0xOSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6IkxpemV0aCBSaWRkZXIiLCJ0cnVzdGVkRGV2aWNlRW5hYmxlZCI6dHJ1ZSwicHJlZmVycmVkX3VzZXJuYW1lIjoiYjU5MjQ1NzgiLCJ0ZXN0X2FjY291bnQiOmZhbHNlLCJnaXZlbl9uYW1lIjoiTGl6ZXRoIiwiZmFtaWx5X25hbWUiOiJSaWRkZXIiLCJ0ZmEiOmZhbHNlLCJlbWFpbCI6InNhcmlkZGVyQGdtYWlsLmNvbSJ9.SoCC1ni2p_bcf4c6M8BWp-UUF6W88B-9aqUWtCbaWnAoH73Brjz6pBWdFF_mMD1bscJPNhA742N_-15zCy4T6lezNS8reqcS0HMJTvHj3HDvMZ0xfvJiDcZ4xOFUEdbyYPBx5mOJSZr2KC8zCdoHw9rOsWwFAKVYGA7-qJzlWWEIYe7Q57jHsvBNyTbSYt4-2fVM4e2LDnxQW5-gDvG6vZE4lxobgJxoCkSbDaHwcTvQxVV3iDjc0fNpNmetL5S7OjcBF9DjxmnHeYe6obhwhXMMUOe4CCUA7irgJiTpMkziNIZqhvQJWwvIMhiD5KaDOk7Z_nd_r7Tqljtv58McDg',
    'cache-control': 'no-cache',
    'content-type': 'application/json',
    'contests': 'na',
    'gmt-offset': '-10',
    'gsetting': 'bolnasite',
    'origin': 'https://www.betonline.ag',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.betonline.ag/',
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'utc-offset': '600',
}

# Update time headers to current time
now = datetime.utcnow()
headers['actual-time'] = str(int(now.timestamp() * 1000))
headers['iso-time'] = now.isoformat() + 'Z'
headers['utc-time'] = now.strftime('%a, %d %b %Y %H:%M:%S GMT')

url = 'https://api.betonline.ag/report/api/report/get-bet-history'

# Fetch all pages
all_bets = []
start_position = 0
page_size = 25

print("Fetching all pages from BetOnline API...")
print("=" * 60)

while True:
    # Request body
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    body = {
        "Id": None,
        "EndDate": end_date.isoformat() + 'Z',
        "StartDate": start_date.strftime('%Y-%m-%dT00:00:00.000Z'),
        "Status": None,
        "Product": None,
        "WagerType": None,
        "FreePlayFlag": None,
        "StartPosition": start_position,
        "TotalPerPage": page_size,
        "IsDailyFigureReport": False
    }
    
    print(f"\nFetching page: StartPosition={start_position}, TotalPerPage={page_size}")
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we got any bets
            if 'Data' in data and data['Data']:
                bets = data['Data']
                print(f"  ✓ Got {len(bets)} bets")
                all_bets.extend(bets)
                
                # If we got fewer than page_size, we're done
                if len(bets) < page_size:
                    print(f"\n  → Last page (got {len(bets)} < {page_size})")
                    break
                
                # Move to next page
                start_position += page_size
            else:
                print("  → No more bets")
                break
        else:
            print(f"  ✗ Error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            break
            
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        break

print("\n" + "=" * 60)
print(f"TOTAL BETS FETCHED: {len(all_bets)}")
print("=" * 60)

# Calculate pending total
pending_total = 0
pending_count = 0
for bet in all_bets:
    if bet.get('Status') == 'Pending':
        amount = float(bet.get('RiskAmount', 0))
        pending_total += amount
        pending_count += 1

print(f"\nPending bets: {pending_count}")
print(f"Pending total: ${pending_total:.2f}")

# Save to file
output_file = '/Users/steveridder/Git/Football/artifacts/betonline_api_all_pages.json'
with open(output_file, 'w') as f:
    json.dump(all_bets, f, indent=2)

print(f"\n✓ Saved {len(all_bets)} bets to {output_file}")

