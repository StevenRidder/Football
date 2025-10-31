#!/usr/bin/env python3
"""
Verify that frontend displays match backend calculations.
Check multiple weeks and validate via Playwright.
"""

import pandas as pd
import json
from playwright.sync_api import sync_playwright
import time


def load_backend_data():
    """Load the backend graded results"""
    import glob
    
    graded_files = glob.glob('artifacts/graded_results/graded_bets_*.csv')
    if not graded_files:
        raise FileNotFoundError("No graded results found. Run grade_predictions_simple.py first")
    
    latest_file = sorted(graded_files)[-1]
    print(f"✅ Loading backend data from {latest_file}")
    
    df = pd.read_csv(latest_file)
    return df


def check_backend_data(df, weeks=[1, 3, 5, 7, 8]):
    """Check backend data for specific weeks"""
    print("\n" + "=" * 70)
    print("📊 BACKEND DATA CHECK")
    print("=" * 70)
    
    backend_results = {}
    
    for week in weeks:
        week_data = df[df['week'] == week]
        spread_bets = week_data[week_data['spread_win'].notna()]
        
        if len(spread_bets) > 0:
            wins = spread_bets['spread_win'].sum()
            losses = len(spread_bets) - wins
            wr = wins / len(spread_bets) * 100
            
            backend_results[week] = {
                'bets': len(spread_bets),
                'wins': int(wins),
                'losses': int(losses),
                'win_rate': round(wr, 1),
                'games': []
            }
            
            # Get sample games
            for _, game in spread_bets.head(3).iterrows():
                backend_results[week]['games'].append({
                    'matchup': f"{game['away_team']} @ {game['home_team']}",
                    'actual': f"{int(game['actual_away_score'])}-{int(game['actual_home_score'])}",
                    'bet': game['spread_bet_side'],
                    'result': 'WIN' if game['spread_win'] == 1 else 'LOSS'
                })
            
            print(f"\nWeek {week}:")
            print(f"  Bets: {len(spread_bets)}")
            print(f"  Record: {int(wins)}-{int(losses)} ({wr:.1f}%)")
            print(f"  Sample games:")
            for g in backend_results[week]['games']:
                print(f"    {g['matchup']}: {g['actual']} → {g['bet']} = {g['result']}")
    
    return backend_results


def check_frontend_data(weeks=[1, 3, 5, 7, 8]):
    """Check frontend data via Playwright"""
    print("\n" + "=" * 70)
    print("🌐 FRONTEND DATA CHECK (via Playwright)")
    print("=" * 70)
    
    frontend_results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to Flask app
        try:
            page.goto('http://localhost:9876/', timeout=10000)
            time.sleep(2)
        except Exception as e:
            print(f"\n❌ ERROR: Could not connect to Flask app at http://localhost:9876/")
            print(f"   Make sure Flask is running: python3 app_flask.py")
            browser.close()
            return None
        
        for week in weeks:
            print(f"\n📅 Checking Week {week}...")
            
            # Get data from API
            try:
                response = page.request.get(f'http://localhost:9876/api/games/graded?week={week}')
                data = response.json()
                
                if 'games' not in data:
                    print(f"  ❌ No games data returned")
                    continue
                
                games = data['games']
                
                # Count spread bets and results
                spread_bets = [g for g in games if g.get('spread_bet') not in ['Pass', None, '']]
                wins = sum(1 for g in spread_bets if g.get('spread_result') == 'WIN')
                losses = sum(1 for g in spread_bets if g.get('spread_result') == 'LOSS')
                pending = sum(1 for g in spread_bets if g.get('spread_result') not in ['WIN', 'LOSS', 'PUSH'])
                
                total = wins + losses
                wr = (wins / total * 100) if total > 0 else 0
                
                frontend_results[week] = {
                    'bets': len(spread_bets),
                    'wins': wins,
                    'losses': losses,
                    'pending': pending,
                    'win_rate': round(wr, 1),
                    'games': []
                }
                
                # Get sample games
                for g in spread_bets[:3]:
                    if g.get('spread_result') in ['WIN', 'LOSS']:
                        frontend_results[week]['games'].append({
                            'matchup': f"{g['away_team']} @ {g['home_team']}",
                            'actual': f"{g.get('away_score', 'N/A')}-{g.get('home_score', 'N/A')}",
                            'bet': g.get('spread_bet', 'N/A'),
                            'result': g.get('spread_result', 'N/A')
                        })
                
                print(f"  Bets: {len(spread_bets)} (Pending: {pending})")
                print(f"  Record: {wins}-{losses} ({wr:.1f}%)")
                print(f"  Sample games:")
                for g in frontend_results[week]['games']:
                    print(f"    {g['matchup']}: {g['actual']} → {g['bet']} = {g['result']}")
                
            except Exception as e:
                print(f"  ❌ Error fetching week {week}: {e}")
        
        # Take screenshot of Week 1
        try:
            page.goto('http://localhost:9876/', timeout=10000)
            time.sleep(2)
            page.screenshot(path='frontend_week1_verification.png')
            print(f"\n📸 Screenshot saved: frontend_week1_verification.png")
        except Exception as e:
            print(f"\n⚠️ Could not take screenshot: {e}")
        
        browser.close()
    
    return frontend_results


def compare_backend_frontend(backend, frontend):
    """Compare backend calculations with frontend display"""
    print("\n" + "=" * 70)
    print("🔍 BACKEND vs FRONTEND COMPARISON")
    print("=" * 70)
    
    if frontend is None:
        print("\n❌ Frontend check failed - cannot compare")
        return False
    
    all_match = True
    
    for week in backend.keys():
        if week not in frontend:
            print(f"\n❌ Week {week}: Missing from frontend")
            all_match = False
            continue
        
        b = backend[week]
        f = frontend[week]
        
        print(f"\nWeek {week}:")
        
        # Check bets count
        if b['bets'] == f['bets']:
            print(f"  ✅ Bets: {b['bets']} (match)")
        else:
            print(f"  ❌ Bets: Backend={b['bets']}, Frontend={f['bets']} (MISMATCH)")
            all_match = False
        
        # Check wins/losses (accounting for pending)
        if f['pending'] > 0:
            print(f"  ⚠️ Record: Backend={b['wins']}-{b['losses']}, Frontend={f['wins']}-{f['losses']} ({f['pending']} pending)")
        elif b['wins'] == f['wins'] and b['losses'] == f['losses']:
            print(f"  ✅ Record: {b['wins']}-{b['losses']} (match)")
        else:
            print(f"  ❌ Record: Backend={b['wins']}-{b['losses']}, Frontend={f['wins']}-{f['losses']} (MISMATCH)")
            all_match = False
        
        # Check win rate
        if abs(b['win_rate'] - f['win_rate']) < 1.0:  # Allow 1% tolerance
            print(f"  ✅ Win Rate: {b['win_rate']}% (match)")
        else:
            print(f"  ❌ Win Rate: Backend={b['win_rate']}%, Frontend={f['win_rate']}% (MISMATCH)")
            all_match = False
    
    print("\n" + "=" * 70)
    if all_match:
        print("✅ ALL CHECKS PASSED - Backend and Frontend match!")
    else:
        print("❌ MISMATCHES FOUND - Backend and Frontend don't match")
    print("=" * 70)
    
    return all_match


def main():
    print("=" * 70)
    print("🔬 FRONTEND-BACKEND VERIFICATION")
    print("=" * 70)
    
    # Load backend data
    backend_df = load_backend_data()
    
    # Check specific weeks
    weeks_to_check = [1, 3, 5, 7, 8]
    
    # Check backend
    backend_results = check_backend_data(backend_df, weeks_to_check)
    
    # Check frontend
    frontend_results = check_frontend_data(weeks_to_check)
    
    # Compare
    match = compare_backend_frontend(backend_results, frontend_results)
    
    # Final summary
    print("\n" + "=" * 70)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 70)
    
    if match:
        print("\n✅ SUCCESS: Frontend correctly displays backend calculations")
        print("✅ All weeks checked show matching data")
        print("✅ Ready for production use")
    else:
        print("\n❌ FAILURE: Frontend does not match backend")
        print("⚠️ Flask may be using old prediction files")
        print("⚠️ Check that Flask is loading the correct CSV")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()

