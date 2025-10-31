#!/usr/bin/env python3
"""
Convert PFF JSON data to CSV format expected by pff_loader.py
"""

import json
import pandas as pd
from pathlib import Path

# Directories
json_dir = Path(__file__).parent.parent / "data" / "pff_raw"
output_dir = Path(__file__).parent.parent / "data" / "pff_raw"
output_dir.mkdir(parents=True, exist_ok=True)

print("📊 Converting PFF JSON to CSV Format")
print("=" * 60)

# Map JSON files to seasons
json_files = {
    2024: "team_overview_2024_full.json",
    # Add more as we parse them
}

for season, filename in json_files.items():
    filepath = json_dir / filename
    
    if not filepath.exists():
        print(f"⏭️  Skipping {season}: {filename} not found")
        continue
    
    # Load JSON
    with open(filepath) as f:
        data = json.load(f)
    
    teams = data['team_overview']
    
    # Convert to DataFrame with expected columns
    rows = []
    for team in teams:
        rows.append({
            'team': team['name'],
            'abbreviation': team['abbreviation'],
            'pass_block_grade': team['grades_pass_block'],
            'pass_rush_grade': team['grades_pass_rush_defense'],
            'run_block_grade': team['grades_run_block'],
            'run_defense_grade': team['grades_run_defense'],
            'coverage_grade': team['grades_coverage_defense'],
            'pass_grade': team['grades_pass'],
            # Additional useful fields
            'overall_grade': team['grades_overall'],
            'offense_grade': team['grades_offense'],
            'defense_grade': team['grades_defense'],
            'wins': team['wins'],
            'losses': team['losses'],
            'points_scored': team['points_scored'],
            'points_allowed': team['points_allowed'],
        })
    
    df = pd.DataFrame(rows)
    
    # Save to CSV
    output_file = output_dir / f"team_grades_{season}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"✅ {season}: Converted {len(df)} teams")
    print(f"   Output: {output_file}")
    print(f"   Sample: {df.iloc[0]['abbreviation']} - Pass Block: {df.iloc[0]['pass_block_grade']}, Pass Rush: {df.iloc[0]['pass_rush_grade']}")

print("\n" + "=" * 60)
print("✅ Conversion complete!")
print(f"📁 CSV files saved to: {output_dir}")

