#!/usr/bin/env python3
"""
Save PFF data from browser network responses.
Run this to save the JSON response from the current browser page.
"""
import sys
import json
from pathlib import Path

# Get the JSON from stdin
data = sys.stdin.read()

# Parse to validate
try:
    parsed = json.loads(data)
    
    # Get filename from command line arg
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "pff_data.json"
    
    # Save to pff_raw directory
    output_dir = Path(__file__).parent.parent / "data" / "pff_raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / filename
    with open(filepath, 'w') as f:
        json.dump(parsed, f, indent=2)
    
    print(f"✅ Saved: {filepath}")
    print(f"   Keys: {list(parsed.keys())}")
    if 'team_overview' in parsed:
        print(f"   Teams: {len(parsed['team_overview'])}")
        if parsed['team_overview']:
            print(f"   Fields: {list(parsed['team_overview'][0].keys())[:10]}")
    
except json.JSONDecodeError as e:
    print(f"❌ Invalid JSON: {e}")
    sys.exit(1)

