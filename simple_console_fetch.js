// PASTE THIS DIRECTLY IN THE BROWSER CONSOLE
// This uses the page's own authenticated fetch

(async function() {
  console.log('🚀 Starting bet fetch...');
  
  const allBets = [];
  const now = new Date();
  
  for (let start = 0; start < 500; start += 100) {
    console.log(`📡 Fetching bets ${start}-${start + 100}...`);
    
    try {
      const response = await fetch('https://api.betonline.ag/report/api/report/get-bet-history', {
        method: 'POST',
        headers: {
          'accept': 'application/json, text/plain, */*',
          'content-type': 'application/json',
          'actual-time': now.getTime().toString(),
          'iso-time': now.toISOString(),
          'utc-time': now.toUTCString(),
          'gmt-offset': (-now.getTimezoneOffset() / 60).toString(),
          'utc-offset': Math.abs(now.getTimezoneOffset()).toString(),
          'contests': 'na',
          'gsetting': 'bolnasite'
        },
        credentials: 'include',
        body: JSON.stringify({
          Id: null,
          StartDate: new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString(),
          EndDate: now.toISOString(),
          Status: null,
          Product: null,
          WagerType: null,
          FreePlayFlag: null,
          StartPosition: start,
          TotalPerPage: 100,
          IsDailyFigureReport: false
        })
      });
      
      const data = await response.json();
      console.log(`  ✓ Got ${data.Data?.length || 0} bets (TotalRows: ${data.TotalRows})`);
      
      allBets.push(...(data.Data || []));
      
      if (start + 100 >= data.TotalRows) {
        console.log('✅ Reached end of results');
        break;
      }
      
      // Small delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
    } catch (error) {
      console.error(`❌ Error at position ${start}:`, error);
      break;
    }
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
  
  console.log('\n' + '='.repeat(60));
  console.log('✅ FETCH COMPLETE!');
  console.log('='.repeat(60));
  console.log(`Total unique bets: ${unique.length}`);
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
  
  return unique;
})();

