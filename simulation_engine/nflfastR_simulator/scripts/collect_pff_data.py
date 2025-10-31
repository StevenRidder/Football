#!/usr/bin/env python3
"""
Collect PFF data by navigating URLs and capturing network responses.
This script will save the actual API responses from the browser.
"""

import json
from pathlib import Path

# Data to collect
SEASONS = [2020, 2021, 2022, 2023, 2024]
WEEKS_2025 = list(range(1, 9))

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "pff_raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# URLs to navigate
urls_to_fetch = []

# Team overview for each season
for season in SEASONS:
    url = f"https://premium.pff.com/api/v1/teams/overview?league=nfl&season={season}&week=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,28,29,30,32"
    filename = f"team_overview_{season}_full.json"
    urls_to_fetch.append((url, filename))

# 2025 weeks 1-8
url_2025 = "https://premium.pff.com/api/v1/teams/overview?league=nfl&season=2025&week=1,2,3,4,5,6,7,8"
urls_to_fetch.append((url_2025, "team_overview_2025_weeks1-8.json"))

# Team stats for each season
for season in SEASONS:
    url = f"https://premium.pff.com/api/v1/teams?league=nfl&season={season}&week=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,28,29,30,32"
    filename = f"team_stats_{season}_full.json"
    urls_to_fetch.append((url, filename))

url_2025_stats = "https://premium.pff.com/api/v1/teams?league=nfl&season=2025&week=1,2,3,4,5,6,7,8"
urls_to_fetch.append((url_2025_stats, "team_stats_2025_weeks1-8.json"))

# Games for 2024 by week (since full season endpoint fails)
for week in range(1, 19):
    url = f"https://premium.pff.com/api/v1/games?league=nfl&season=2024&week={week}"
    filename = f"games_2024_week{week}.json"
    urls_to_fetch.append((url, filename))

# 2025 games
for week in WEEKS_2025:
    url = f"https://premium.pff.com/api/v1/games?league=nfl&season=2025&week={week}"
    filename = f"games_2025_week{week}.json"
    urls_to_fetch.append((url, filename))

# Print the URLs
print("📋 URLs to fetch via browser:")
print("=" * 80)
for i, (url, filename) in enumerate(urls_to_fetch, 1):
    print(f"{i}. {filename}")
    print(f"   {url}\n")

print(f"\nTotal: {len(urls_to_fetch)} URLs")
print(f"\nOutput directory: {OUTPUT_DIR}")

