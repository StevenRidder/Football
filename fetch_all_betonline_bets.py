#!/usr/bin/env python3
"""
Fetch ALL bets from BetOnline API (past and present)
Uses pagination to get complete history
"""
import json
import datetime
from nfl_edge.bets.betonline_client import parse_curl_to_headers, _post_json

def fetch_all_bets_paginated(headers, days_back=365, page_size=1000):
    """
    Fetch ALL bets from BetOnline with pagination
    
    Args:
        headers: Authentication headers from cURL
        days_back: How many days back to fetch (default 365 for full year)
        page_size: Items per page (max 1000)
    """
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days_back)
    
    all_bets = []
    start_position = 0
    
    print(f"📊 Fetching bets from {start_date.date()} to {end_date.date()}")
    print(f"   Using page size: {page_size}")
    print()
    
    while True:
        request_body = {
            "Id": None,
            "EndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",  # Include milliseconds
            "StartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "Status": None,  # All statuses
            "Product": None,  # All products
            "WagerType": None,  # All wager types
            "FreePlayFlag": None,
            "StartPosition": start_position,
            "TotalPerPage": page_size,
            "IsDailyFigureReport": False
        }
        
        try:
            print(f"📥 Fetching page starting at position {start_position}...")
            result = _post_json("get-bet-history", headers=headers, data=request_body)
            
            if isinstance(result, dict):
                # Check if it has a data array
                if "Data" in result:
                    page_bets = result["Data"]
                elif "data" in result:
                    page_bets = result["data"]
                else:
                    # Might be error response
                    print(f"⚠️  Unexpected response format: {list(result.keys())}")
                    break
            elif isinstance(result, list):
                page_bets = result
            else:
                print(f"⚠️  Unknown response type: {type(result)}")
                break
            
            if not page_bets:
                print(f"✅ No more bets found. Total fetched: {len(all_bets)}")
                break
            
            all_bets.extend(page_bets)
            print(f"   Got {len(page_bets)} bets (total: {len(all_bets)})")
            
            # If we got less than page_size, we're done
            if len(page_bets) < page_size:
                print(f"✅ Reached end of results. Total: {len(all_bets)}")
                break
            
            start_position += page_size
            
        except Exception as e:
            print(f"❌ Error at position {start_position}: {e}")
            break
    
    return all_bets

def main():
    print("🏈 BetOnline Complete Bet History Fetcher")
    print("=" * 50)
    print()
    print("Paste your cURL command from BetOnline DevTools:")
    print("(Right-click on 'get-bet-history' request → Copy → Copy as cURL)")
    print()
    
    # Read multi-line cURL
    lines = []
    while True:
        try:
            line = input()
            if not line.strip():
                break
            lines.append(line)
        except EOFError:
            break
    
    curl_cmd = ' '.join(lines)
    
    if not curl_cmd.strip():
        print("❌ No cURL command provided")
        return
    
    try:
        print("\n🔐 Parsing cURL headers...")
        headers_dict = parse_curl_to_headers(curl_cmd)
        
        # Remove the __url__ and __method__ keys
        headers = {k: v for k, v in headers_dict.items() if not k.startswith('__')}
        
        print("✅ Headers extracted")
        print()
        
        # Fetch all bets
        all_bets = fetch_all_bets_paginated(headers, days_back=365, page_size=1000)
        
        print()
        print(f"📊 SUMMARY:")
        print(f"   Total bets fetched: {len(all_bets)}")
        
        # Calculate totals
        pending_bets = [b for b in all_bets if b.get('Status') == 'Pending' or b.get('status') == 'Pending']
        pending_total = sum(float(b.get('Risk', 0) or b.get('Amount', 0) or 0) for b in pending_bets)
        
        print(f"   Pending bets: {len(pending_bets)}")
        print(f"   Pending amount: ${pending_total:.2f}")
        
        # Save to file
        output_file = 'artifacts/betonline_all_bets.json'
        with open(output_file, 'w') as f:
            json.dump({
                'total_bets': len(all_bets),
                'pending_count': len(pending_bets),
                'pending_total': pending_total,
                'bets': all_bets
            }, f, indent=2)
        
        print()
        print(f"✅ Saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

