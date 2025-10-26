// INTERCEPT VERSION: Captures data from the page's own requests
// Use this if CORS blocks direct fetch calls

console.log('🚀 BetOnline Bet Interceptor');
console.log('=============================\n');

window.allCapturedBets = [];
window.capturedResponses = [];

// Intercept XMLHttpRequest
const originalXHROpen = XMLHttpRequest.prototype.open;
const originalXHRSend = XMLHttpRequest.prototype.send;

XMLHttpRequest.prototype.open = function(method, url, ...args) {
  this._url = url;
  this._method = method;
  return originalXHROpen.apply(this, [method, url, ...args]);
};

XMLHttpRequest.prototype.send = function(...args) {
  if (this._url && this._url.includes('get-bet-history')) {
    this.addEventListener('load', function() {
      try {
        const data = JSON.parse(this.responseText);
        if (data.Data && data.Data.length > 0) {
          window.capturedResponses.push(data);
          window.allCapturedBets.push(...data.Data);
          console.log(`✓ Intercepted ${data.Data.length} bets (Total: ${window.allCapturedBets.length}, TotalRows: ${data.TotalRows})`);
        }
      } catch (e) {
        console.error('Failed to parse response:', e);
      }
    });
  }
  return originalXHRSend.apply(this, args);
};

// Intercept fetch
const originalFetch = window.fetch;
window.fetch = async function(...args) {
  const response = await originalFetch(...args);
  
  if (args[0] && (args[0].includes('get-bet-history') || (args[0].url && args[0].url.includes('get-bet-history')))) {
    const clone = response.clone();
    try {
      const data = await clone.json();
      if (data.Data && data.Data.length > 0) {
        window.capturedResponses.push(data);
        window.allCapturedBets.push(...data.Data);
        console.log(`✓ Intercepted ${data.Data.length} bets (Total: ${window.allCapturedBets.length}, TotalRows: ${data.TotalRows})`);
      }
    } catch (e) {
      console.error('Failed to parse fetch response:', e);
    }
  }
  
  return response;
};

console.log('✅ Interceptor installed!\n');
console.log('Now do this:');
console.log('1. Scroll down to load more bets');
console.log('2. Change date filters to load different periods');
console.log('3. Watch the console for "✓ Intercepted" messages');
console.log('4. When you have all bets, run: downloadAllBets()\n');

window.downloadAllBets = function() {
  // Deduplicate
  const unique = [];
  const seen = new Set();
  
  for (const bet of window.allCapturedBets) {
    const key = `${bet.TicketNumber}-${bet.PlacedDate}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(bet);
    }
  }
  
  const asNum = x => Number(x || 0);
  const pending = unique.filter(r => r.WagerStatus === 'Pending');
  const stake = pending.reduce((s, r) => s + asNum(r.Risk), 0);
  const toWin = pending.reduce((s, r) => s + asNum(r.ToWin), 0);
  
  console.log('\n' + '='.repeat(60));
  console.log('✅ DOWNLOAD READY!');
  console.log('='.repeat(60));
  console.log(`Total unique bets: ${unique.length}`);
  console.log(`Pending bets: ${pending.length}`);
  console.log(`Total stake: $${stake.toFixed(2)}`);
  console.log(`Total to win: $${toWin.toFixed(2)}`);
  console.log('='.repeat(60));
  
  const json = JSON.stringify(unique, null, 2);
  const blob = new Blob([json], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'all_404_bets_complete.json';
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('📥 Downloaded: all_404_bets_complete.json');
};

window.showStats = function() {
  const unique = [];
  const seen = new Set();
  
  for (const bet of window.allCapturedBets) {
    const key = `${bet.TicketNumber}-${bet.PlacedDate}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(bet);
    }
  }
  
  const asNum = x => Number(x || 0);
  const pending = unique.filter(r => r.WagerStatus === 'Pending');
  const stake = pending.reduce((s, r) => s + asNum(r.Risk), 0);
  const toWin = pending.reduce((s, r) => s + asNum(r.ToWin), 0);
  
  console.log('\n📊 Current Stats:');
  console.log(`  Unique bets: ${unique.length}`);
  console.log(`  Pending: ${pending.length}`);
  console.log(`  Stake: $${stake.toFixed(2)}`);
  console.log(`  To win: $${toWin.toFixed(2)}\n`);
};

