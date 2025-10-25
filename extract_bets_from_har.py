#!/usr/bin/env python3
"""
Extract bet data from BetOnline HAR file
"""
import json
import sys
from pathlib import Path

def extract_bets_from_har(har_path):
    """Extract bet information from HAR file"""
    
    with open(har_path, 'r') as f:
        har = json.load(f)
    
    print("=" * 80)
    print("BETONLINE BET EXTRACTION")
    print("=" * 80)
    
    # Extract customer info
    customer_id = None
    pending_amount = None
    
    for entry in har['log']['entries']:
        url = entry['request']['url']
        
        # Get customer info from balance endpoint
        if 'update-balance' in url:
            if 'content' in entry['response'] and 'text' in entry['response']['content']:
                try:
                    data = json.loads(entry['response']['content']['text'])
                    profile = data.get('Profile', {})
                    customer_id = profile.get('CustomerID')
                    pending_amount = profile.get('PendingBets')
                    
                    print(f"\n✅ Customer ID: {customer_id}")
                    print(f"✅ Pending Bets: ${pending_amount}")
                    print(f"✅ Available Balance: ${profile.get('AvailableBalance', 0)}")
                except:
                    pass
    
    print("\n" + "=" * 80)
    print("IMPORTANT: BetOnline uses api2.betonline.ag")
    print("=" * 80)
    
    print("\nTo fetch your actual bet details, you need to:")
    print("1. Use the manual entry form at http://localhost:9876/bets")
    print("2. Or provide your session cookies to hit these endpoints:")
    print("   - https://api2.betonline.ag/sportsbook/pending-wagers")
    print("   - https://api2.betonline.ag/sportsbook/bet-history")
    print("   - https://api2.betonline.ag/sportsbook/graded-wagers")
    
    print(f"\n💡 You have ${pending_amount} in pending bets - add them manually for now")
    
    return {
        'customer_id': customer_id,
        'pending_amount': pending_amount
    }

if __name__ == "__main__":
    har_file = "/Users/steveridder/Dropbox/Mac/Downloads/www.betonline.ag.har"
    
    if not Path(har_file).exists():
        print(f"❌ HAR file not found: {har_file}")
        sys.exit(1)
    
    result = extract_bets_from_har(har_file)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Customer: {result['customer_id']}")
    print(f"Pending: ${result['pending_amount']}")
    print("\n✅ Use manual entry at http://localhost:9876/bets to track your bets")

