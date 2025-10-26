// This script runs in the page context (not isolated like content scripts)
// It can make API calls using the page's own auth

(async function() {
  console.log('🚀 BetOnline Complete Fetcher - Injected Script Running');
  
  const allBets = [];
  
  async function fetchBetsPage(startPosition, pageSize = 100) {
    const url = 'https://api.betonline.ag/report/api/report/get-bet-history';
    
    const now = new Date();
    const endDate = now.toISOString();
    const startDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString();
    
    console.log(`📡 Fetching bets ${startPosition}-${startPosition + pageSize}...`);
    
    // Use XMLHttpRequest instead of fetch to avoid CORS preflight
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url, true);
      
      // Set headers exactly as the page does
      xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('actual-time', now.getTime().toString());
      xhr.setRequestHeader('iso-time', now.toISOString());
      xhr.setRequestHeader('utc-time', now.toUTCString());
      xhr.setRequestHeader('gmt-offset', (-now.getTimezoneOffset() / 60).toString());
      xhr.setRequestHeader('utc-offset', Math.abs(now.getTimezoneOffset()).toString());
      xhr.setRequestHeader('contests', 'na');
      xhr.setRequestHeader('gsetting', 'bolnasite');
      
      // This is critical - send cookies
      xhr.withCredentials = true;
      
      xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            console.log(`  ✓ Got ${data.Data?.length || 0} bets (TotalRows: ${data.TotalRows})`);
            resolve(data);
          } catch (e) {
            reject(new Error('Failed to parse response: ' + e.message));
          }
        } else {
          reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
        }
      };
      
      xhr.onerror = function() {
        reject(new Error('Network error'));
      };
      
      const body = JSON.stringify({
        Id: null,
        StartDate: startDate,
        EndDate: endDate,
        Status: null,
        Product: null,
        WagerType: null,
        FreePlayFlag: null,
        StartPosition: startPosition,
        TotalPerPage: pageSize,
        IsDailyFigureReport: false
      });
      
      xhr.send(body);
    });
  }
  
  // Fetch all pages
  try {
    const firstPage = await fetchBetsPage(0, 100);
    const totalRows = firstPage.TotalRows;
    
    console.log(`\n📊 Total bets available: ${totalRows}\n`);
    
    allBets.push(...(firstPage.Data || []));
    
    // Fetch remaining pages
    const numPages = Math.ceil(totalRows / 100);
    for (let i = 1; i < numPages; i++) {
      await new Promise(resolve => setTimeout(resolve, 500)); // Small delay
      const page = await fetchBetsPage(i * 100, 100);
      allBets.push(...(page.Data || []));
    }
    
    // Deduplicate
    const unique = [];
    const seen = new Set();
    
    for (const bet of allBets) {
      const key = `${bet.TicketNumber}`;
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(bet);
      }
    }
    
    // Calculate stats
    const asNum = x => Number(x || 0);
    const pending = unique.filter(r => r.WagerStatus === 'Pending');
    const stake = pending.reduce((s, r) => s + asNum(r.Risk), 0);
    const toWin = pending.reduce((s, r) => s + asNum(r.ToWin), 0);
    
    console.log('\n' + '='.repeat(60));
    console.log('✅ FETCH COMPLETE!');
    console.log('='.repeat(60));
    console.log(`Total unique bets: ${unique.length}`);
    console.log(`Pending bets: ${pending.length}`);
    console.log(`Total stake: $${stake.toFixed(2)}`);
    console.log(`Total to win: $${toWin.toFixed(2)}`);
    console.log('='.repeat(60));
    
    // Download
    const json = JSON.stringify(unique, null, 2);
    const blob = new Blob([json], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'all_404_bets_complete.json';
    a.click();
    URL.revokeObjectURL(url);
    
    console.log('📥 Downloaded: all_404_bets_complete.json');
    
    // Send message back to extension
    window.postMessage({ type: 'BETONLINE_FETCH_COMPLETE', bets: unique.length }, '*');
    
  } catch (error) {
    console.error('❌ Error:', error);
    window.postMessage({ type: 'BETONLINE_FETCH_ERROR', error: error.message }, '*');
  }
})();
