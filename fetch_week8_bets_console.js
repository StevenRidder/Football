// Paste this in the DevTools Console on betonline.ag/my-account/bet-history
// It will fetch ALL bets since 10/22/25 with proper pacing to avoid Cloudflare

const START_DATE = '2025-10-22T00:00:00.000Z';
const END_DATE = '2025-12-31T23:59:59.999Z';
const STATUS_FILTER = 'Pending';
const PAGE_SIZE = 100;

const sleep = ms => new Promise(r => setTimeout(r, ms));
const jitter = () => Math.floor(1200 + Math.random() * 1000);

async function getAuthBearer() {
  let token = window.localStorage.getItem('__bol_auth_bearer__');
  if (!token) {
    token = prompt('Paste your Authorization Bearer token from Network tab:');
    if (token) window.localStorage.setItem('__bol_auth_bearer__', token);
  }
  return token;
}

async function postHistory(auth, body) {
  const url = 'https://api.betonline.ag/report/api/report/get-bet-history';
  
  for (let attempt = 1; attempt <= 4; attempt++) {
    const r = await fetch(url, {
      method: 'POST',
      headers: {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'authorization': auth,
        'origin': 'https://www.betonline.ag',
        'referer': 'https://www.betonline.ag/'
      },
      credentials: 'include',
      body: JSON.stringify(body)
    });
    
    if (r.status === 429) {
      const wait = 60000 * attempt;
      console.log(`⏳ Rate limited. Waiting ${wait/1000}s...`);
      await sleep(wait);
      continue;
    }
    
    if (r.status === 401 || r.status === 403) {
      throw new Error('❌ Auth failed. Reload page and get fresh token.');
    }
    
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }
  
  throw new Error('Too many rate limits');
}

console.log('🚀 Fetching ALL bets since 10/22/25...');

(async () => {
  const auth = await getAuthBearer();
  if (!auth) {
    console.error('❌ No auth token provided');
    return;
  }
  
  const all = [];
  const seen = new Set();
  let offset = 0;
  
  while (true) {
    const body = {
      Id: null,
      StartDate: START_DATE,
      EndDate: END_DATE,
      Status: STATUS_FILTER,
      Product: null,
      WagerType: null,
      FreePlayFlag: null,
      StartPosition: offset,
      TotalPerPage: PAGE_SIZE,
      IsDailyFigureReport: false
    };
    
    console.log(`📥 Fetching offset ${offset}...`);
    
    try {
      const j = await postHistory(auth, body);
      const page = Array.isArray(j.Data) ? j.Data : [];
      
      console.log(`   ✓ Got ${page.length} bets (TotalRows=${j.TotalRows})`);
      
      for (const r of page) {
        const key = `${r.TicketNumber}|${r.PlacedDate}`;
        if (!seen.has(key)) {
          seen.add(key);
          all.push(r);
        }
      }
      
      if (page.length < PAGE_SIZE) {
        console.log('   ✓ Reached last page');
        break;
      }
      
      offset += PAGE_SIZE;
      await sleep(jitter());
      
    } catch (err) {
      console.error('❌ Error:', err.message);
      break;
    }
  }
  
  // Calculate totals
  const P = all.filter(r => r.WagerStatus === 'Pending');
  const asNum = x => Number(x || 0);
  const stake = P.reduce((s, r) => s + asNum(r.Risk), 0);
  const toWin = P.reduce((s, r) => s + asNum(r.ToWin), 0);
  
  console.log('');
  console.log('='.repeat(60));
  console.log('✅ COMPLETE!');
  console.log('='.repeat(60));
  console.log(`Total bets fetched: ${all.length}`);
  console.log(`Pending bets: ${P.length}`);
  console.log(`Total stake (Risk): $${stake.toFixed(2)}`);
  console.log(`Total to win: $${toWin.toFixed(2)}`);
  console.log('='.repeat(60));
  
  // Download JSON
  const json = JSON.stringify(all, null, 2);
  const blob = new Blob([json], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), {
    href: url,
    download: 'week8_bets.json'
  });
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('📥 Downloaded week8_bets.json');
  console.log('');
  console.log('Next: Move to Football directory and run:');
  console.log('  python3 import_all_api_bets.py week8_bets.json');
  
})();
