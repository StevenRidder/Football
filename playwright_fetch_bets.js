const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const contexts = browser.contexts();
  const context = contexts[0];
  const pages = await context.pages();
  const page = pages[pages.length - 1];
  
  console.log('🚀 Fetching ALL bets since 10/22/25...');
  
  // Execute the fetch script in the page context
  const result = await page.evaluate(async () => {
    const BASE = 'https://api.betonline.ag/report/api/report/get-bet-history';
    const START_DATE = '2025-10-22T00:00:00.000Z';
    const END_DATE = '2025-12-31T23:59:59.999Z';
    const PAGE_SIZE = 100;
    
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    
    const all = [];
    const seen = new Set();
    let offset = 0;
    
    // Get auth from a recent request or localStorage
    let auth = null;
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      const value = localStorage.getItem(key);
      if (value && value.includes('eyJ') && value.length > 500) {
        auth = `Bearer ${value}`;
        break;
      }
    }
    
    if (!auth) {
      // Try to get from a test request
      try {
        const testResp = await fetch(BASE, {
          method: 'POST',
          headers: {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json'
          },
          body: JSON.stringify({
            Id: null,
            StartDate: START_DATE,
            EndDate: END_DATE,
            Status: 'Pending',
            Product: null,
            WagerType: null,
            FreePlayFlag: null,
            StartPosition: 0,
            TotalPerPage: 10,
            IsDailyFigureReport: false
          })
        });
        
        // If this works, we have cookies
        if (testResp.ok) {
          auth = 'cookies';
        }
      } catch (e) {}
    }
    
    while (true) {
      const body = {
        Id: null,
        StartDate: START_DATE,
        EndDate: END_DATE,
        Status: 'Pending',
        Product: null,
        WagerType: null,
        FreePlayFlag: null,
        StartPosition: offset,
        TotalPerPage: PAGE_SIZE,
        IsDailyFigureReport: false
      };
      
      const headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json'
      };
      
      if (auth && auth !== 'cookies') {
        headers['authorization'] = auth;
      }
      
      try {
        const resp = await fetch(BASE, {
          method: 'POST',
          headers,
          body: JSON.stringify(body)
        });
        
        if (!resp.ok) {
          return { error: `HTTP ${resp.status}`, offset, total: all.length };
        }
        
        const data = await resp.json();
        const page = Array.isArray(data.Data) ? data.Data : [];
        
        for (const bet of page) {
          const key = `${bet.TicketNumber}|${bet.PlacedDate}`;
          if (!seen.has(key)) {
            seen.add(key);
            all.push(bet);
          }
        }
        
        if (page.length < PAGE_SIZE) break;
        offset += PAGE_SIZE;
        await sleep(1500);
        
      } catch (err) {
        return { error: err.message, offset, total: all.length };
      }
    }
    
    const pending = all.filter(r => r.WagerStatus === 'Pending');
    const stake = pending.reduce((s, r) => s + Number(r.Risk || 0), 0);
    const toWin = pending.reduce((s, r) => s + Number(r.ToWin || 0), 0);
    
    return {
      success: true,
      total: all.length,
      pending: pending.length,
      stake,
      toWin,
      bets: all
    };
  });
  
  if (result.error) {
    console.error('❌ Error:', result.error);
    console.log(`Fetched ${result.total} bets before error at offset ${result.offset}`);
  } else {
    console.log('='.repeat(60));
    console.log('✅ SUCCESS!');
    console.log('='.repeat(60));
    console.log(`Total bets: ${result.total}`);
    console.log(`Pending: ${result.pending}`);
    console.log(`Stake: $${result.stake.toFixed(2)}`);
    console.log(`To Win: $${result.toWin.toFixed(2)}`);
    console.log('='.repeat(60));
    
    fs.writeFileSync('week8_bets.json', JSON.stringify(result.bets, null, 2));
    console.log('\n📁 Saved to: week8_bets.json');
  }
  
  await browser.close();
})();
