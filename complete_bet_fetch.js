// COMPLETE FETCH: Makes requests for ALL 400 bets
// Paste this in the console on sports.betonline.ag

(async function() {
  console.log('🚀 Fetching ALL 400 bets...\n');
  
  const allBets = [];
  const url = 'https://sports.betonline.ag/services/wagering/get-bet-history';
  
  // Fetch ALL positions in chunks of 100
  for (let start = 0; start < 400; start += 100) {
    console.log(`📡 Fetching bets ${start}-${start + 100}...`);
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          StartPosition: start,
          PageSize: 100,
          FromDate: '2020-01-01T00:00:00.000Z',
          ToDate: '2025-12-31T23:59:59.999Z',
          Product: 'Sportsbook',
          WagerStatus: 'All'
        })
      });
      
      if (!response.ok) {
        console.error(`  ❌ HTTP ${response.status}`);
        continue;
      }
      
      const data = await response.json();
      const bets = data.Data || [];
      
      console.log(`  ✓ Got ${bets.length} bets (TotalRows: ${data.TotalRows})`);
      
      allBets.push(...bets);
      
      // Small delay to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 500));
      
    } catch (error) {
      console.error(`  ❌ Error: ${error.message}`);
    }
  }
  
  // Calculate stats
  const asNum = x => Number(x || 0);
  const pending = allBets.filter(r => r.WagerStatus === 'Pending');
  const stake = pending.reduce((s, r) => s + asNum(r.Risk), 0);
  const toWin = pending.reduce((s, r) => s + asNum(r.ToWin), 0);
  
  console.log('\n' + '='.repeat(60));
  console.log('✅ FETCH COMPLETE!');
  console.log('='.repeat(60));
  console.log(`Fetched bets: ${allBets.length}`);
  console.log(`Pending: ${pending.length}`);
  console.log(`Stake: $${stake.toFixed(2)}`);
  console.log(`To Win: $${toWin.toFixed(2)}`);
  console.log('='.repeat(60));
  
  // Download
  const json = JSON.stringify(allBets, null, 2);
  const blob = new Blob([json], {type: 'application/json'});
  const url2 = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url2;
  a.download = 'all_400_bets_complete.json';
  a.click();
  URL.revokeObjectURL(url2);
  
  console.log('📥 Downloaded: all_400_bets_complete.json');
  console.log('\nNow run: python3 import_all_404_bets.py');
})();

