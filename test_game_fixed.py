#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('http://localhost:9876/game/BAL/MIA', wait_until='networkidle')
    page.wait_for_selector('table', timeout=10000)
    
    print("\n" + "="*70)
    print("GAME PAGE DATA CHECK - AFTER FIX")
    print("="*70 + "\n")
    
    for stat in ['Passing EPA', 'Rushing EPA', 'Passing Yards', 'Rushing Yards']:
        row = page.locator(f'tr:has-text("{stat}")').first
        if row.count() > 0:
            text = row.inner_text()
            nums = re.findall(r'[-]?\d+\.?\d*', text)
            non_zero = [n for n in nums if float(n) != 0.0]
            status = '✅ HAS DATA' if non_zero else '❌ ALL ZEROS'
            print(f'{stat:25s}: {status} {nums}')
    
    print("\n" + "="*70)
    import time
    time.sleep(8)
    browser.close()

