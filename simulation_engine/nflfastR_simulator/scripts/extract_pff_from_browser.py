#!/usr/bin/env python3
"""
Extract PFF data from browser snapshots.
This script processes the JSON responses captured from the browser.
"""

import json
from pathlib import Path

# Data to save (paste from browser snapshots)
datasets = {
    "team_overview_2024_full.json": """paste 2024 data here""",
    "team_overview_2023_full.json": """paste 2023 data here""",
    # Add more as needed
}

output_dir = Path(__file__).parent.parent / "data" / "pff_raw"
output_dir.mkdir(parents=True, exist_ok=True)

print("📊 Extracting PFF data from browser responses...")
print("=" * 60)

for filename, json_str in datasets.items():
    if "paste" in json_str:
        print(f"⏭️  Skipping {filename} (no data)")
        continue
    
    try:
        data = json.loads(json_str)
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Saved: {filename}")
        if 'team_overview' in data:
            print(f"   Teams: {len(data['team_overview'])}")
            if data['team_overview']:
                sample = data['team_overview'][0]
                print(f"   Sample team: {sample['name']}")
                print(f"   Pass Block Grade: {sample.get('grades_pass_block', 'N/A')}")
                print(f"   Pass Rush Grade: {sample.get('grades_pass_rush_defense', 'N/A')}")
    
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")

print("\n" + "=" * 60)
print("✅ Extraction complete!")
