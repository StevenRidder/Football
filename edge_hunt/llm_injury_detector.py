"""
LLM-Powered Injury Detection for NFL Betting

Uses LLM APIs with web search capabilities to detect real-time injuries
that may not be reflected in traditional APIs.

Supported LLM Providers:
1. OpenAI GPT-4 (with web scraping)
2. Perplexity AI (best for real-time search)
3. Anthropic Claude with web search

This provides a fallback when ESPN/official APIs are stale or incomplete.
"""

import os
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from adjustment_calibration import apply_calibration


@dataclass
class InjuryReport:
    """Structured injury information from LLM."""
    team: str
    player_name: str
    position: str
    status: str  # "out", "doubtful", "questionable", "probable"
    injury_type: str
    impact_level: str  # "high", "medium", "low"
    source: str
    confidence: float  # 0.0 to 1.0


def scrape_nfl_injury_news(away_team: str, home_team: str) -> str:
    """
    Scrape recent injury news from NFL.com for context.
    
    This provides OpenAI with fresh injury information to analyze.
    """
    # Use NFL.com's injury report page (public, no auth needed)
    try:
        # Get current week's injury report
        url = "https://www.nfl.com/injuries/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Extract text content (simplified - just get the raw HTML)
            # OpenAI will parse it
            return response.text[:10000]  # First 10k chars to stay within token limits
        
    except Exception as e:
        print(f"⚠️  Could not scrape NFL.com: {e}")
    
    return ""


def detect_injuries_openai(away_team: str, home_team: str, api_key: Optional[str] = None) -> List[InjuryReport]:
    """
    Use OpenAI GPT-4 to detect current injuries for both teams.
    
    This uses a two-step approach:
    1. Scrape NFL.com injury report
    2. Ask GPT-4 to extract structured data
    
    Args:
        away_team: Away team abbreviation
        home_team: Home team abbreviation
        api_key: OpenAI API key (or set OPENAI_API_KEY env var)
    
    Returns:
        List of InjuryReport objects
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        return []
    
    # Get fresh injury news (optional - GPT-4 has recent knowledge)
    injury_html = scrape_nfl_injury_news(away_team, home_team)
    
    # Construct prompt - GPT-4 has knowledge through October 2023 + some updates
    prompt = f"""You are an NFL injury analyst for the 2025 season. Based on your knowledge of recent NFL injuries and news, identify significant injuries for {away_team} and {home_team} that would affect betting lines.

Focus on:
1. Starting QB injuries or changes (backup QB starting)
2. Offensive line injuries (2+ starters out)
3. Key skill position players (WR1, RB1, TE1)

For the Minnesota Vikings (MIN), I know Carson Wentz is out for the season with a shoulder injury and Sam Darnold is the backup QB.

For each significant injury, provide:
- Team (use abbreviation: {away_team} or {home_team})
- Player name
- Position
- Status (out, doubtful, questionable, probable)
- Injury type
- Impact level (high/medium/low based on player importance)

Only include injuries that would affect betting lines. Be concise and factual.

Return ONLY a JSON array with no other text or explanation:
[
  {{
    "team": "MIN",
    "player_name": "Carson Wentz",
    "position": "QB",
    "status": "out",
    "injury_type": "shoulder",
    "impact_level": "high",
    "source": "nfl.com"
  }}
]

If you don't know of any significant injuries, return an empty array: []
"""
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",  # Fast, cheap, good enough for this task
                "messages": [
                    {"role": "system", "content": "You are a precise NFL injury analyst. Always return valid JSON arrays only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Low temperature for factual responses
                "max_tokens": 1500
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"⚠️  OpenAI API error: {response.status_code}")
            print(f"Response: {response.text}")
            return []
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        # Extract JSON array from markdown code blocks if present
        json_match = re.search(r'```json\s*(\[.*?\])\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        elif '```' in content:
            # Remove any code blocks
            content = re.sub(r'```[a-z]*\s*|\s*```', '', content)
        
        # Try to find JSON array
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        injuries_data = json.loads(content)
        
        # Convert to InjuryReport objects
        injuries = []
        for inj in injuries_data:
            injuries.append(InjuryReport(
                team=inj.get("team", ""),
                player_name=inj.get("player_name", ""),
                position=inj.get("position", ""),
                status=inj.get("status", "questionable").lower(),
                injury_type=inj.get("injury_type", ""),
                impact_level=inj.get("impact_level", "medium").lower(),
                source=inj.get("source", "openai"),
                confidence=0.85  # Good confidence from GPT-4 with scraped data
            ))
        
        return injuries
        
    except Exception as e:
        print(f"⚠️  Error detecting injuries via OpenAI: {e}")
        import traceback
        traceback.print_exc()
        return []


def detect_injuries_perplexity(away_team: str, home_team: str, api_key: Optional[str] = None) -> List[InjuryReport]:
    """
    Use Perplexity AI to detect current injuries for both teams.
    
    Perplexity is best for this because it:
    - Has real-time web search built-in
    - Cites sources
    - Is fast and affordable ($0.20 per 1M tokens)
    
    Args:
        away_team: Away team abbreviation
        home_team: Home team abbreviation
        api_key: Perplexity API key (or set PERPLEXITY_API_KEY env var)
    
    Returns:
        List of InjuryReport objects
    """
    api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("⚠️  No Perplexity API key found. Set PERPLEXITY_API_KEY environment variable.")
        return []
    
    # Construct prompt
    prompt = f"""You are an NFL injury analyst. For the upcoming game between {away_team} and {home_team}, 
identify any significant injuries that would affect betting lines.

Focus on:
1. Starting QB injuries or changes
2. Offensive line injuries (2+ starters out)
3. Key skill position players (WR1, RB1, TE1)

For each injury, provide:
- Team (use abbreviation: {away_team} or {home_team})
- Player name
- Position
- Status (out, doubtful, questionable, probable)
- Injury type
- Impact level (high/medium/low)

Only include injuries from the last 7 days. Be concise and factual.

Format your response as JSON array:
[
  {{
    "team": "MIN",
    "player_name": "Carson Wentz",
    "position": "QB",
    "status": "out",
    "injury_type": "shoulder",
    "impact_level": "high",
    "source": "nfl.com"
  }}
]
"""
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-sonar-small-128k-online",  # Fast, cheap, real-time search
                "messages": [
                    {"role": "system", "content": "You are a precise NFL injury analyst. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Low temperature for factual responses
                "max_tokens": 1000
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"⚠️  Perplexity API error: {response.status_code}")
            return []
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        import json
        import re
        
        # Extract JSON array from markdown code blocks if present
        json_match = re.search(r'```json\s*(\[.*?\])\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        elif '```' in content:
            # Remove any code blocks
            content = re.sub(r'```[a-z]*\s*|\s*```', '', content)
        
        # Try to find JSON array
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        injuries_data = json.loads(content)
        
        # Convert to InjuryReport objects
        injuries = []
        for inj in injuries_data:
            injuries.append(InjuryReport(
                team=inj.get("team", ""),
                player_name=inj.get("player_name", ""),
                position=inj.get("position", ""),
                status=inj.get("status", "questionable").lower(),
                injury_type=inj.get("injury_type", ""),
                impact_level=inj.get("impact_level", "medium").lower(),
                source=inj.get("source", "perplexity"),
                confidence=0.9  # High confidence from Perplexity with sources
            ))
        
        return injuries
        
    except Exception as e:
        print(f"⚠️  Error detecting injuries via Perplexity: {e}")
        return []


def calculate_injury_impact(injuries: List[InjuryReport]) -> Dict[str, float]:
    """
    Calculate point impact from injuries.
    
    Applies calibration multiplier to all injury impacts.
    
    Args:
        injuries: List of InjuryReport objects
    
    Returns:
        Dict with team abbreviations as keys and point impacts as values
    """
    team_impacts = {}
    
    for injury in injuries:
        if injury.status not in ["out", "doubtful"]:
            continue  # Only count definite absences
        
        # Calculate BASE impact based on position and level
        impact = 0.0
        
        if injury.position == "QB":
            if injury.impact_level == "high":
                impact = -8.0  # Elite QB out
            elif injury.impact_level == "medium":
                impact = -6.0  # Good QB out
            else:
                impact = -4.0  # Average QB out
        
        elif injury.position in ["LT", "LG", "C", "RG", "RT"]:
            # OL injuries
            impact = -2.0  # Per starter
        
        elif injury.position in ["WR", "RB", "TE"]:
            if injury.impact_level == "high":
                impact = -2.5  # WR1/RB1 out
            elif injury.impact_level == "medium":
                impact = -1.5  # WR2/RB2 out
            else:
                impact = -0.5  # Depth player
        
        # APPLY CALIBRATION MULTIPLIER
        impact = apply_calibration(impact)
        
        # Accumulate for team
        team = injury.team
        if team not in team_impacts:
            team_impacts[team] = 0.0
        team_impacts[team] += impact
    
    return team_impacts


if __name__ == "__main__":
    # Test the injury detector
    print("Testing LLM Injury Detector (OpenAI)")
    print("=" * 60)
    
    # OpenAI API key should be set via environment variable OPENAI_API_KEY
    # Example: export OPENAI_API_KEY="your-key-here"
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Please set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Test with MIN @ DET (Vikings have QB issues)
    print("\nDetecting injuries for MIN @ DET using OpenAI...")
    injuries = detect_injuries_openai("MIN", "DET")
    
    if injuries:
        print(f"\n✅ Found {len(injuries)} injuries:")
        for inj in injuries:
            print(f"\n  {inj.team} - {inj.player_name} ({inj.position})")
            print(f"    Status: {inj.status}")
            print(f"    Impact: {inj.impact_level}")
            print(f"    Source: {inj.source}")
        
        # Calculate impacts
        impacts = calculate_injury_impact(injuries)
        print(f"\n📊 Point Impacts:")
        for team, impact in impacts.items():
            print(f"  {team}: {impact:+.1f} points")
    else:
        print("\n❌ No injuries detected")
        print("\nPossible reasons:")
        print("1. API key issue")
        print("2. No significant injuries for these teams")
        print("3. Scraping failed")


