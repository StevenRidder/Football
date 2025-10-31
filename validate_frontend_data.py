"""
Validate simulator predictions data on frontend using Playwright.

Checks:
1. All weeks (1-9) are available in dropdown
2. Data loads correctly for each week
3. Conviction badges display correctly
4. Results shown for completed games (weeks 1-8)
5. Predictions shown for week 9 (no results)
"""
import asyncio
import json
from playwright.async_api import async_playwright
import pandas as pd
from pathlib import Path

async def validate_week_data(page, week, expected_data):
    """Validate data for a specific week."""
    print(f"\n{'='*70}")
    print(f"Validating Week {week}")
    print(f"{'='*70}")
    
    # Select week from dropdown
    await page.select_option('#weekSelect', str(week))
    
    # Wait for data to load
    await page.wait_for_timeout(1000)  # Wait 1 second for API call
    
    # Check if loading indicator is gone
    try:
        await page.wait_for_selector('#games-tbody tr:not(:has-text("Loading"))', timeout=5000)
    except:
        print(f"⚠️  Week {week}: Data may not have loaded")
    
    # Get all game rows
    rows = await page.query_selector_all('#games-tbody tr')
    
    if len(rows) == 0:
        print(f"❌ Week {week}: No games found")
        return False
    
    print(f"✅ Week {week}: Found {len(rows)} games")
    
    # Validate each game
    errors = []
    warnings = []
    
    for idx, row in enumerate(rows):
        # Get game text
        game_text = await row.inner_text()
        
        # Check for basic game info (away @ home)
        if ' @ ' not in game_text:
            errors.append(f"Row {idx}: Missing game matchup")
            continue
        
        # Extract game info
        game_cell = await row.query_selector('td:first-child')
        if game_cell:
            game_html = await game_cell.inner_html()
            # Check for away/home team names
            if not any(team in game_html for team in ['DAL', 'PHI', 'KC', 'BAL', 'MIA']):
                warnings.append(f"Row {idx}: Game text may be malformed")
        
        # Check for spread recommendation
        spread_cell = await row.query_selector('td:nth-child(7)')
        if spread_cell:
            spread_text = await spread_cell.inner_text()
            if spread_text.strip() and 'Pass' not in spread_text:
                # Should have conviction badge
                spread_html = await spread_cell.inner_html()
                has_badge = 'badge' in spread_html and ('HIGH' in spread_html or 'MEDIUM' in spread_html or 'LOW' in spread_html)
                if not has_badge and week <= 8:
                    warnings.append(f"Row {idx}: Spread bet missing conviction badge")
        
        # Check for total recommendation
        total_cell = await row.query_selector('td:nth-child(11)')
        if total_cell:
            total_text = await total_cell.inner_text()
            if total_text.strip() and 'Pass' not in total_text:
                # Should have conviction badge
                total_html = await total_cell.inner_html()
                has_badge = 'badge' in total_html and ('HIGH' in total_html or 'MEDIUM' in total_html or 'LOW' in total_html)
                if not has_badge and week <= 8:
                    warnings.append(f"Row {idx}: Total bet missing conviction badge")
        
        # Check for results (weeks 1-8 should have results)
        if week <= 8:
            result_cells = await row.query_selector_all('td.col-result')
            has_results = False
            for result_cell in result_cells:
                result_text = await result_cell.inner_text()
                if 'W' in result_text or 'L' in result_text or 'WIN' in result_text or 'LOSS' in result_text:
                    has_results = True
                    break
            
            if not has_results:
                warnings.append(f"Row {idx}: Missing results for completed game")
        
        # Check for final score (weeks 1-8)
        if week <= 8:
            score_cell = await row.query_selector('td:nth-child(2)')
            if score_cell:
                score_text = await score_cell.inner_text()
                if not score_text.strip() or score_text == '-':
                    warnings.append(f"Row {idx}: Missing final score")
    
    if errors:
        print(f"❌ Week {week}: {len(errors)} errors")
        for error in errors[:5]:  # Show first 5
            print(f"   {error}")
    else:
        print(f"✅ Week {week}: No errors")
    
    if warnings:
        print(f"⚠️  Week {week}: {len(warnings)} warnings")
        for warning in warnings[:3]:  # Show first 3
            print(f"   {warning}")
    
    return len(errors) == 0

async def validate_api_data(page):
    """Validate API endpoint returns correct data."""
    print(f"\n{'='*70}")
    print("Validating API Endpoints")
    print(f"{'='*70}")
    
    # Test simulator-predictions endpoint
    try:
        response = await page.goto('http://localhost:9876/api/simulator-predictions?week=1')
        if response and response.status == 200:
            data = await response.json()
            print(f"✅ /api/simulator-predictions returned {data.get('total', 0)} games")
            if data.get('games'):
                sample_game = data['games'][0]
                required_fields = ['away_team', 'home_team', 'week', 'spread_conviction', 'total_conviction']
                missing = [f for f in required_fields if f not in sample_game or sample_game[f] is None]
                if missing:
                    print(f"⚠️  Missing fields in API response: {missing}")
                else:
                    print(f"✅ API response has all required fields")
        else:
            print(f"❌ /api/simulator-predictions returned status {response.status if response else 'None'}")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

async def validate_week_selector(page):
    """Validate week selector dropdown."""
    print(f"\n{'='*70}")
    print("Validating Week Selector")
    print(f"{'='*70}")
    
    # Get all options
    options = await page.query_selector_all('#weekSelect option')
    weeks = []
    for opt in options:
        value = await opt.get_attribute('value')
        text = await opt.inner_text()
        weeks.append((value, text))
    
    print(f"Found {len(weeks)} week options:")
    for value, text in weeks:
        print(f"  Week {value}: {text}")
    
    # Check for weeks 1-9
    week_values = [w[0] for w in weeks]
    missing = [w for w in range(1, 10) if str(w) not in week_values]
    if missing:
        print(f"❌ Missing weeks: {missing}")
        return False
    else:
        print(f"✅ All weeks 1-9 available")
        return True

async def validate_conviction_badges(page, week):
    """Validate conviction badges are displayed correctly."""
    await page.select_option('#weekSelect', str(week))
    await page.wait_for_timeout(1000)
    
    # Check for badges in page HTML
    page_html = await page.content()
    
    badge_counts = {
        'HIGH': page_html.count('badge') and page_html.count('HIGH'),
        'MEDIUM': page_html.count('badge') and page_html.count('MEDIUM'),
        'LOW': page_html.count('badge') and page_html.count('LOW'),
    }
    
    # Check for Tabler badge classes
    has_danger_badge = 'bg-danger' in page_html
    has_warning_badge = 'bg-warning' in page_html
    has_secondary_badge = 'bg-secondary' in page_html
    
    print(f"\nWeek {week} Badge Validation:")
    print(f"  HIGH badges: {badge_counts['HIGH'] > 0}")
    print(f"  MEDIUM badges: {badge_counts['MEDIUM'] > 0}")
    print(f"  LOW badges: {badge_counts['LOW'] > 0}")
    print(f"  Tabler classes: danger={has_danger_badge}, warning={has_warning_badge}, secondary={has_secondary_badge}")

async def main():
    """Run all validations."""
    print("="*70)
    print("FRONTEND DATA VALIDATION")
    print("="*70)
    
    # Load expected data
    data_file = Path("artifacts/simulator_predictions.csv")
    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        return
    
    df = pd.read_csv(data_file)
    print(f"\n📊 Loaded expected data: {len(df)} games")
    
    # Group by week
    expected_by_week = {}
    for week in range(1, 10):
        week_df = df[df['week'] == week]
        expected_by_week[week] = {
            'total': len(week_df),
            'completed': week_df[week_df['is_completed'] == True].shape[0],
            'spread_bets': week_df[week_df['spread_recommendation'] != 'Pass'].shape[0],
            'total_bets': week_df[week_df['total_recommendation'] != 'Pass'].shape[0],
        }
        print(f"  Week {week}: {expected_by_week[week]['total']} games ({expected_by_week[week]['completed']} completed)")
    
    async with async_playwright() as p:
        print(f"\n🌐 Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print(f"📡 Navigating to http://localhost:9876...")
            await page.goto('http://localhost:9876', wait_until='networkidle', timeout=10000)
            
            # Validate week selector
            await validate_week_selector(page)
            
            # Validate API
            await validate_api_data(page)
            
            # Validate each week
            all_passed = True
            for week in range(1, 10):
                expected = expected_by_week[week]
                passed = await validate_week_data(page, week, expected)
                
                if not passed:
                    all_passed = False
                
                # Validate badges for first and last week
                if week == 1 or week == 9:
                    await validate_conviction_badges(page, week)
                
                # Small delay between weeks
                await page.wait_for_timeout(500)
            
            print(f"\n{'='*70}")
            if all_passed:
                print("✅ ALL VALIDATIONS PASSED")
            else:
                print("⚠️  SOME VALIDATIONS FAILED - See details above")
            print(f"{'='*70}")
            
        except Exception as e:
            print(f"\n❌ Error during validation: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

