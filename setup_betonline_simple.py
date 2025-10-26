#!/usr/bin/env python3
"""
SIMPLE SETUP: Just paste your Authorization token from BetOnline.
Much easier than the full cURL command!
"""

import json
from pathlib import Path

def simple_setup():
    print("=" * 80)
    print("BETONLINE SIMPLE SETUP")
    print("=" * 80)
    print()
    print("This is MUCH easier - just copy your cookies!")
    print()
    print("📋 HOW TO GET YOUR COOKIES:")
    print("-" * 80)
    print("1. Open BetOnline in your browser and log in")
    print("2. Go to My Account → Bet History")
    print("3. Open DevTools (F12)")
    print("4. Go to Network tab")
    print("5. Refresh the page")
    print("6. Click on ANY request to betonline.ag")
    print("7. Scroll down to 'Request Headers'")
    print("8. Find the 'cookie:' header")
    print("9. Copy the ENTIRE cookie value (very long)")
    print()
    print("📋 PASTE YOUR COOKIES:")
    print("-" * 80)
    print("Paste the entire cookie string:")
    print()
    
    cookies = input().strip()
    
    if not cookies:
        print("\n❌ ERROR: No cookies provided")
        return False
    
    # Check if it looks like cookies
    if 'KEYCLOAK' not in cookies and 'AUTH_SESSION' not in cookies:
        print("\n❌ ERROR: This doesn't look like BetOnline cookies")
        print("Make sure you copied the entire 'cookie:' header value")
        return False
    
    print("\n⏳ Testing cookies...")
    
    # Build headers with cookies
    headers = {
        'cookie': cookies,
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://www.betonline.ag',
        'referer': 'https://www.betonline.ag/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Test by fetching bets
        print("⏳ Fetching your bets to test...")
        
        # Try the new API endpoint format
        import requests
        
        # BetOnline uses api.betonline.ag for their new API
        test_url = "https://api.betonline.ag/sportsbook/api/wager/get-pending-wagers"
        
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 401:
            print("\n❌ ERROR: Token is invalid or expired")
            print("Please get a fresh token from DevTools")
            return False
        
        if response.status_code != 200:
            print(f"\n⚠️ WARNING: Got status code {response.status_code}")
            print("Trying alternate endpoints...")
        
        # Try to get any data
        try:
            data = response.json()
            print("✅ Got response from BetOnline!")
            
            # Save the working headers
            config_dir = Path("artifacts")
            config_dir.mkdir(exist_ok=True)
            
            with open(config_dir / "betonline_session.json", 'w') as f:
                json.dump(headers, f, indent=2)
            
            print(f"✅ Saved session to {config_dir / 'betonline_session.json'}")
            
            print("\n" + "=" * 80)
            print("SUCCESS!")
            print("=" * 80)
            print()
            print("Your token is saved and ready to use!")
            print()
            print("NEXT STEPS:")
            print("1. Go to: http://localhost:9876/bets")
            print("2. Click 'Auto-Fetch from BetOnline'")
            print("3. All your bets will appear automatically!")
            print()
            print("Or run: python3 auto_fetch_bets.py")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: Could not parse response: {e}")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure you're logged into BetOnline")
        print("2. Get a fresh token from DevTools")
        print("3. Make sure you copied the ENTIRE token")
        return False

if __name__ == "__main__":
    success = simple_setup()
    if not success:
        print("\n❌ Setup failed. Please try again.")
        print("\nTIP: The token is the long string after 'Bearer' in the authorization header")
        print("It starts with 'eyJ' and is very long (500+ characters)")
        exit(1)
    else:
        print("\n✅ Setup complete! You're all set.")
        exit(0)

