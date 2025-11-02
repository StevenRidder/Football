"""
ChatGPT-powered betting recommendations generator.
Analyzes model predictions and generates expert picks for the week.
"""
import os
import json
from typing import Dict, List, Any
from pathlib import Path
import pandas as pd


def create_analysis_prompt(predictions: List[Dict[str, Any]]) -> str:
    """
    Create an optimized prompt for ChatGPT to analyze betting opportunities.
    
    Args:
        predictions: List of game prediction dictionaries
        
    Returns:
        Formatted prompt string
    """
    prompt = """You are an expert NFL sports bettor analyzing model predictions vs. market lines. 
Your goal is to identify the BEST betting opportunities where the model has a significant edge.

KEY PRINCIPLES:
1. **Edge Size Matters**: Focus on games where sim line differs from market by 3+ points (ATS) or 7+ points (totals)
2. **Confidence Levels**: 
   - 100% = Model line differs by 10+ points
   - 70-90% = Model line differs by 5-9 points
   - 53-60% = Model line differs by 2-4 points
   - 50% = Pass (no edge)
3. **Risk Management**: Avoid games with "Pass" recommendations or low confidence
4. **Value Identification**: Look for mispriced lines where the market is wrong

ANALYZE THE FOLLOWING GAMES:

"""
    
    for i, game in enumerate(predictions, 1):
        away = game['away_team']
        home = game['home_team']
        
        # Extract scores
        market_away = game.get('market_away_score', 0)
        market_home = game.get('market_home_score', 0)
        sim_away = game.get('sim_away_score_calibrated', 0)
        sim_home = game.get('sim_home_score_calibrated', 0)
        
        # Extract lines
        market_spread = game.get('spread', 'N/A')
        sim_spread_line = game.get('sim_spread_line', 'N/A')
        spread_pick = game.get('spread_pick', 'Pass')
        spread_confidence = game.get('spread_confidence', 50)
        
        market_total = game.get('total', 'N/A')
        sim_total = game.get('sim_total', 'N/A')
        total_pick = game.get('total_pick', 'Pass')
        total_confidence = game.get('total_confidence', 50)
        
        prompt += f"""
{i}. {away} @ {home}
   Market Score: {market_away}-{market_home} (from spread/total)
   Sim Score: {sim_away}-{sim_home}
   
   SPREAD: Market {market_spread} | Sim {sim_spread_line} | Pick: {spread_pick} {spread_confidence}%
   TOTAL: Market {market_total} | Sim {sim_total} | Pick: {total_pick} {total_confidence}%
"""
    
    prompt += """

PROVIDE YOUR ANALYSIS IN THE FOLLOWING FORMAT:

## 1. Against-the-Spread (ATS) Bets
[Table format:]
Game | Market Line | Sim Line | Edge | Pick | Confidence
[List top 5-7 plays only - ignore games with no edge]

## 2. Totals (Over/Under)
[Table format:]
Game | Market Total | Sim Total | Edge | Pick | Confidence
[List top 5-7 plays only]

## 3. Moneyline Value
[Table format:]
Game | Market Projection | Sim Projection | Edge | Moneyline Pick
[List top 3-5 plays only where one team is heavily favored by model]

## 4. Final Recommendations
[Provide top 3 BEST bets overall with rationale]

RULES:
- Only include games with meaningful edges (3+ point difference)
- Rank by confidence and edge size
- Provide brief reasoning for top picks
- Format as clean tables (use | separators)
"""
    
    return prompt


def call_chatgpt_api(prompt: str, api_key: str = None) -> str:
    """
    Call OpenAI ChatGPT API with the analysis prompt.
    
    Args:
        prompt: The formatted prompt
        api_key: OpenAI API key (defaults to env variable)
        
    Returns:
        ChatGPT response text
    """
    try:
        import openai
    except ImportError:
        return "ERROR: OpenAI library not installed. Run: pip install openai"
    
    if api_key is None:
        api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        return "ERROR: No OpenAI API key found. Set OPENAI_API_KEY environment variable."
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # or "gpt-4" or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are an expert NFL betting analyst with deep knowledge of line value and edge identification."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        return f"ERROR calling ChatGPT API: {str(e)}"


def parse_chatgpt_response(response: str) -> Dict[str, Any]:
    """
    Parse the ChatGPT response into structured data.
    
    Args:
        response: Raw ChatGPT response text
        
    Returns:
        Dictionary with parsed sections
    """
    sections = {
        'ats_bets': [],
        'totals': [],
        'moneyline': [],
        'final_recommendations': [],
        'raw_response': response
    }
    
    # Simple parsing - just split by sections
    # In production, you'd want more robust parsing
    lines = response.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if '## 1. Against-the-Spread' in line or 'ATS' in line and '##' in line:
            current_section = 'ats_bets'
        elif '## 2. Totals' in line or 'Over/Under' in line and '##' in line:
            current_section = 'totals'
        elif '## 3. Moneyline' in line:
            current_section = 'moneyline'
        elif '## 4. Final' in line or 'Recommendations' in line and '##' in line:
            current_section = 'final_recommendations'
        elif line and '|' in line and current_section:
            # Parse table row
            sections[current_section].append(line)
        elif line and current_section == 'final_recommendations':
            sections[current_section].append(line)
    
    return sections


def generate_weekly_picks(predictions_csv: str = "artifacts/simulator_predictions.csv", 
                         current_week: int = None,
                         save_to_file: bool = True) -> Dict[str, Any]:
    """
    Main function to generate ChatGPT picks for the week.
    
    Args:
        predictions_csv: Path to predictions CSV file
        current_week: Week number to analyze (defaults to max week)
        save_to_file: Whether to save results to artifacts/
        
    Returns:
        Dictionary with picks and analysis
    """
    # Load predictions
    try:
        df = pd.read_csv(predictions_csv)
    except FileNotFoundError:
        return {"error": "Predictions file not found. Run predictions first."}
    
    # Filter to current week
    if current_week is None:
        current_week = df['week'].max()
    
    df_week = df[df['week'] == current_week].copy()
    
    if df_week.empty:
        return {"error": f"No predictions found for week {current_week}"}
    
    # Convert to list of dicts
    predictions = df_week.to_dict('records')
    
    # Create prompt
    prompt = create_analysis_prompt(predictions)
    
    # Call ChatGPT
    response = call_chatgpt_api(prompt)
    
    # Parse response
    parsed = parse_chatgpt_response(response)
    parsed['week'] = current_week
    parsed['generated_at'] = pd.Timestamp.now().isoformat()
    
    # Save to file
    if save_to_file:
        output_file = Path("artifacts") / f"chatgpt_picks_week{current_week}.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(parsed, f, indent=2)
        print(f"✅ Saved ChatGPT picks to {output_file}")
    
    return parsed


def load_weekly_picks(week: int = None) -> Dict[str, Any]:
    """Load saved ChatGPT picks from file."""
    if week is None:
        # Find most recent
        artifacts = Path("artifacts")
        pick_files = list(artifacts.glob("chatgpt_picks_week*.json"))
        if not pick_files:
            return {"error": "No saved picks found"}
        pick_files.sort()
        latest = pick_files[-1]
    else:
        latest = Path("artifacts") / f"chatgpt_picks_week{week}.json"
        if not latest.exists():
            return {"error": f"No picks found for week {week}"}
    
    with open(latest, 'r') as f:
        return json.load(f)


if __name__ == '__main__':
    # Test the module
    print("Generating ChatGPT picks...")
    result = generate_weekly_picks()
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"\n✅ Generated picks for Week {result['week']}")
        print(f"\n{result['raw_response']}")

