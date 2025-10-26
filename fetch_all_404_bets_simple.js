(async function() {
  console.log('🚀 BetOnline Complete Data Extractor');
  console.log('=====================================\n');

  const betCapture = {
    allBets: [],
    pages: [],
    
    async fetchPage(startPosition, pageSize = 100) {
      const url = 'https://sports.betonline.ag/services/wagering/get-bet-history';
      
      const payload = {
        StartPosition: startPosition,
        PageSize: pageSize,
        FromDate: '2024-01-01T00:00:00.000Z',
        ToDate: '2025-12-31T23:59:59.999Z',
        Product: 'Sportsbook',
        WagerStatus: 'All'
      };
      
      console.log(`📡 Fetching bets ${startPosition}-${startPosition + pageSize}...`);
      
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        console.log(`  ✓ Got ${data.Data?.length || 0} bets (TotalRows: ${data.TotalRows})`);
        
        return data;
      } catch (error) {
        console.error(`  ❌ Error fetching page ${startPosition}:`, error.message);
        throw error;
      }
    },
    
    async fetchAllPages() {
      console.log('🔄 Starting complete data fetch...\n');
      
      this.allBets = [];
      this.pages = [];
      
      const firstPage = await this.fetchPage(0, 100);
      const totalRows = firstPage.TotalRows;
      
      console.log(`\n📊 Total bets to fetch: ${totalRows}\n`);
      
      this.pages.push(firstPage);
      
      const pageSize = 100;
      const numPages = Math.ceil(totalRows / pageSize);
      
      for (let i = 1; i < numPages; i++) {
        const startPos = i * pageSize;
        await new Promise(resolve => setTimeout(resolve, 500));
        const page = await this.fetchPage(startPos, pageSize);
        this.pages.push(page);
      }
      
      const allBetsMap = new Map();
      
      for (const page of this.pages) {
        for (const bet of page.Data || []) {
          const key = `${bet.TicketNumber}-${bet.PlacedDate}`;
          if (!allBetsMap.has(key)) {
            allBetsMap.set(key, bet);
          }
        }
      }
      
      this.allBets = Array.from(allBetsMap.values());
      
      const asNum = x => Number(x || 0);
      const pending = this.allBets.filter(r => r.WagerStatus === 'Pending');
      const stake = pending.reduce((s, r) => s + asNum(r.Risk), 0);
      const toWin = pending.reduce((s, r) => s + asNum(r.ToWin), 0);
      
      console.log('\n' + '='.repeat(60));
      console.log('✅ FETCH COMPLETE!');
      console.log('='.repeat(60));
      console.log(`Total unique bets: ${this.allBets.length}`);
      console.log(`Pending bets: ${pending.length}`);
      console.log(`Total stake (Risk): $${stake.toFixed(2)}`);
      console.log(`Total to win: $${toWin.toFixed(2)}`);
      console.log('='.repeat(60));
      
      return this.allBets;
    },
    
    downloadJSON() {
      if (this.allBets.length === 0) {
        console.error('❌ No bets to download! Run fetchAllPages() first.');
        return;
      }
      
      const json = JSON.stringify(this.allBets, null, 2);
      const blob = new Blob([json], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'all_404_bets_complete.json';
      a.click();
      URL.revokeObjectURL(url);
      
      console.log('📥 Downloaded: all_404_bets_complete.json');
    }
  };

  // Auto-run everything
  await betCapture.fetchAllPages();
  betCapture.downloadJSON();
  
  console.log('\n✅ ALL DONE! Check your Downloads folder for all_404_bets_complete.json');
})();
