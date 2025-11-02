#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

bet = """Ticket Number:

908414722-1

Accepted Date:

11/01/25 08:29 GMT-10

Type: Parlay

Product:

Sportsbook

Amount:

$30.00

To win:

$1,460.37

Status:

Pending

Description:

Football - NFL - Chicago Bears vs Cincinnati Bengals - Parlay | 451 Chicago Bears -2½ -120 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Atlanta Falcons vs New England Patriots - Parlay | 456 New England Patriots -5 -110 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Indianapolis Colts vs Pittsburgh Steelers - Parlay | 457 Indianapolis Colts -3 -120 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Denver Broncos vs Houston Texans - Parlay | 463 Denver Broncos +2½ -110 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Jacksonville Jaguars vs Las Vegas Raiders - Parlay | 467 Jacksonville Jaguars -2½ -115 For Game | 11/02/2025 | 04:05:00 PM (EST) | PendingFootball - NFL - Carolina Panthers vs Green Bay Packers - Parlay | 460 Green Bay Packers -900 For Game | 11/02/2025 | 01:00:00 PM (EST) | PendingFootball - NFL - Minnesota Vikings vs Detroit Lions - Parlay | 462 Detroit Lions -9 -105 For Game | 11/02/2025 | 01:00:00 PM (EST) | Pending"""

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    page = b.new_page()
    
    print("PASTE TEST")
    page.goto('http://localhost:9876/bets', wait_until='networkidle')
    
    page.locator('#betDataInput').fill(bet)
    print("✅ Pasted")
    
    page.locator('button:has-text("Load Bets")').click()
    print("✅ Clicked Load")
    
    time.sleep(4)
    
    # Check if bet exists
    bet_row = page.locator('tr.bet-row:has(small:text("908414722-1"))')
    if bet_row.count() > 0:
        print("✅ BET IN TABLE")
        
        # Click it
        bet_row.click()
        time.sleep(2)
        
        # Check modal
        modal = page.locator('#betDetailsModal')
        if modal.is_visible():
            print("✅ MODAL OPEN")
            
            desc = modal.locator('#modalDescription').inner_html()
            if 'list-group-item' in desc:
                legs = modal.locator('.list-group-item').count()
                print(f"✅✅✅ {legs} LEGS SHOWING!")
            else:
                print(f"❌ NO LEGS: {desc[:100]}")
        else:
            print("❌ MODAL NOT VISIBLE")
    else:
        print("❌ BET NOT IN TABLE")
    
    time.sleep(5)
    b.close()

