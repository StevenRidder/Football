// This script uses the page's own fetch with proper auth
// Run this AFTER the page has loaded

console.log('🚀 Fetching ALL bets using page authentication...');

async function fetchAllBets() {
  // Get the auth headers from the page's last request
  // We'll use the page's own fetch which has the right cookies/auth
  
  const BASE = 'https://api.betonline.ag/report/api/report/get-bet-history';
  const START_DATE = '2025-01-01T00:00:00.000Z';
  const END_DATE = '2025-12-31T23:59:59.999Z';
  const STATUS = 'Pending';
  
  const size = 100;
  let offset = 0;
  const allBets = [];
  
  // Get auth from a real page request first
  console.log('Getting authentication from page...');
  
  // Make a test request to get the pattern
  const testBody = {
    Id: null,
    StartDate: START_DATE,
    EndDate: END_DATE,
    Status: STATUS,
    Product: null,
    WagerType: null,
    FreePlayFlag: null,
    StartPosition: 0,
    TotalPerPage: 10,
    IsDailyFigureReport: false
  };
  
  // Get the authorization header from the page's Angular HTTP client
  // The page uses Angular which stores the token
  let authToken = null;
  
  // Try to extract from localStorage or sessionStorage
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    const value = localStorage.getItem(key);
    if (value && value.includes('eyJ')) {
      console.log(`Found potential token in localStorage: ${key}`);
      authToken = value;
      break;
    }
  }
  
  if (!authToken) {
    console.error('❌ Could not find auth token in localStorage');
    console.log('Trying to extract from network requests...');
    
    // Alternative: intercept the next request
    console.log('Please scroll the page to trigger a bet-history request...');
    return;
  }
  
  console.log('✓ Found auth token, starting pagination...');
  
  while (true) {
    const body = {
      Id: null,
      StartDate: START_DATE,
      EndDate: END_DATE,
      Status: STATUS,
      Product: null,
      WagerType: null,
      FreePlayFlag: null,
      StartPosition: offset,
      TotalPerPage: size,
      IsDailyFigureReport: false
    };
    
    console.log(`Fetching offset ${offset}...`);
    
    try {
      const resp = await fetch(BASE, {
        method: 'POST',
        headers: {
          'accept': 'application/json, text/plain, */*',
          'content-type': 'application/json',
          'authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(body)
      });
      
      if (!resp.ok) {
        console.error(`HTTP ${resp.status} at offset ${offset}`);
        break;
      }
      
      const data = await resp.json();
      allBets.push(...data.Data);
      console.log(`✓ Got ${data.Data.length} bets (TotalRows=${data.TotalRows})`);
      
      if (data.Data.length < size) {
        console.log('✓ Reached last page');
        break;
      }
      
      offset += size;
      await new Promise(r => setTimeout(r, 500));
      
    } catch (err) {
      console.error(`Error at offset ${offset}:`, err);
      break;
    }
  }
  
  // Calculate totals
  const asNum = x => Number(x || 0);
  const pending = allBets.filter(r => r.WagerStatus === 'Pending');
  const stake = pending.reduce((s, r) => s + asNum(r.Risk), 0);
  const toWin = pending.reduce((s, r) => s + asNum(r.ToWin), 0);
  
  console.log('');
  console.log('='.repeat(60));
  console.log('✅ COMPLETE!');
  console.log('='.repeat(60));
  console.log(`Total bets fetched: ${allBets.length}`);
  console.log(`Pending bets: ${pending.length}`);
  console.log(`Total stake (Risk): $${stake.toFixed(2)}`);
  console.log(`Total to win: $${toWin.toFixed(2)}`);
  console.log('='.repeat(60));
  
  // Download
  const json = JSON.stringify(allBets, null, 2);
  const blob = new Blob([json], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), {href:url, download:'all_404_bets.json'});
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('📥 Downloaded all_404_bets.json');
}

fetchAllBets();
