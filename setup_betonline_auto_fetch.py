#!/usr/bin/env python3
"""
ONE-TIME SETUP: Get your BetOnline session cookies for automatic bet fetching.

This script will:
1. Guide you to copy ONE cURL command from DevTools
2. Extract and save your session cookies
3. Automatically fetch ALL your bets going forward

You only need to do this ONCE (or when your session expires).
"""

import json
from pathlib import Path
from nfl_edge.bets.betonline_client import parse_curl_to_headers, fetch_all_bets, normalize_to_ledger, save_ledger

def setup():
    print("=" * 80)
    print("BETONLINE AUTO-FETCH SETUP")
    print("=" * 80)
    print()
    print("This is a ONE-TIME setup. After this, fetching bets will be automatic!")
    print()
    print("📋 STEP 1: Get your cURL command")
    print("-" * 80)
    print("1. Open BetOnline in your browser and log in")
    print("2. Go to My Account → Bet History")
    print("3. Open DevTools (F12 or Right-click → Inspect)")
    print("4. Go to the Network tab")
    print("5. Refresh the page")
    print("6. Look for ANY request to betonline.ag")
    print("7. Right-click on it → Copy → Copy as cURL (bash)")
    print()
    print("📋 STEP 2: Paste your cURL command below")
    print("-" * 80)
    print("Paste the entire cURL command (can be multiple lines)")
    print("When done, press Enter on an empty line:")
    print()
    
    # Read multi-line input
    lines = []
    while True:
        try:
            line = input()
            if not line.strip() and lines:  # Empty line after some input
                break
            lines.append(line)
        except EOFError:
            break
    
    curl_cmd = ' '.join(lines).strip()
    
    if not curl_cmd.startswith('curl '):
        print("\n❌ ERROR: That doesn't look like a cURL command.")
        print("Make sure you copied 'Copy as cURL (bash)' not just the URL.")
        return False
    
    print("\n⏳ Parsing cURL command...")
    
    try:
        # Parse the cURL command
        headers = parse_curl_to_headers(curl_cmd)
        
        # Remove helper keys
        headers = {k: v for k, v in headers.items() if not k.startswith("__")}
        
        print("✅ Successfully extracted session cookies!")
        
        # Save headers for future use
        config_dir = Path("artifacts")
        config_dir.mkdir(exist_ok=True)
        
        with open(config_dir / "betonline_session.json", 'w') as f:
            json.dump(headers, f, indent=2)
        
        print(f"✅ Saved session to {config_dir / 'betonline_session.json'}")
        
        # Test by fetching bets
        print("\n⏳ Testing by fetching your bets...")
        
        raw_data = fetch_all_bets(headers)
        ledger_df = normalize_to_ledger(raw_data)
        
        if ledger_df.empty:
            print("\n⚠️ WARNING: No bets found. This could mean:")
            print("  1. You have no bets on BetOnline")
            print("  2. The session cookies are not working")
            print("  3. BetOnline's API endpoints have changed")
            print("\nTry running this setup again with a fresh cURL command.")
            return False
        
        # Save the bets
        save_ledger(ledger_df, str(config_dir / "bets.parquet"))
        
        print(f"\n✅ SUCCESS! Fetched {len(ledger_df)} bets!")
        print(f"✅ Saved to {config_dir / 'bets.parquet'}")
        
        # Show summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total bets: {len(ledger_df)}")
        print(f"Pending: {len(ledger_df[ledger_df['settlement'] == 'Pending'])}")
        print(f"Graded: {len(ledger_df[ledger_df['settlement'] == 'Graded'])}")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("1. Run: python3 auto_fetch_bets.py")
        print("   This will fetch all your latest bets automatically!")
        print()
        print("2. Or go to: http://localhost:9876/bets")
        print("   Click 'Auto-Fetch from BetOnline' button")
        print()
        print("Your session will stay active for ~24 hours.")
        print("If it expires, just run this setup script again.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure you're logged into BetOnline")
        print("2. Make sure you copied the ENTIRE cURL command")
        print("3. Try a different request from the Network tab")
        return False

if __name__ == "__main__":
    success = setup()
    if not success:
        print("\n❌ Setup failed. Please try again.")
        exit(1)
    else:
        print("\n✅ Setup complete! You're all set.")
        exit(0)

