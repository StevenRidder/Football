// FORCE LOAD ALL BETS - Paste this in console on BetOnline bet history page
// This will intercept responses AND automatically trigger more loads

console.log('🚀 Force Load All Bets - Starting...\n');

window.allCapturedBets = [];
let totalRowsExpected = 0;
let lastStartPosition = -1;
let autoLoadInterval = null;

// Intercept XMLHttpRequest
const originalXHROpen = XMLHttpRequest.prototype.open;
const originalXHRSend = XMLHttpRequest.prototype.send;

XMLHttpRequest.prototype.open = function(method, url, ...args) {
  this._url = url;
  this._method = method;
  return originalXHROpen.apply(this, [method, url, ...args]);
};

XMLHttpRequest.prototype.send = function(body) {
  if (this._url && this._url.includes('get-bet-history')) {
    // Parse the request to see what position we're at
    try {
      const requestData = JSON.parse(body);
      lastStartPosition = requestData.StartPosition;
      console.log(`📡 Request: StartPosition=${requestData.StartPosition}, TotalPerPage=${requestData.TotalPerPage}`);
    } catch (e) {}
    
    this.addEventListener('load', function() {
      try {
        const data = JSON.parse(this.responseText);
        if (data.Data && data.Data.length > 0) {
          // Add new bets (avoid duplicates)
          const existingIds = new Set(window.allCapturedBets.map(b => b.TicketNumber));
          const newBets = data.Data.filter(b => !existingIds.has(b.TicketNumber));
          window.allCapturedBets.push(...newBets);
          
          totalRowsExpected = data.TotalRows;
          
          console.log(`✓ Captured ${newBets.length} NEW bets (${data.Data.length} total in response)`);
          console.log(`  Total captured so far: ${window.allCapturedBets.length}/${totalRowsExpected}`);
          
          // If we haven't loaded everything yet, keep going
          if (window.allCapturedBets.length < totalRowsExpected) {
            const missing = totalRowsExpected - window.allCapturedBets.length;
            console.log(`⚠️  Still missing ${missing} bets!`);
            
            // Trigger scroll to load more
            setTimeout(() => {
              console.log('🔄 Auto-scrolling to load more...');
              window.scrollTo(0, document.body.scrollHeight);
            }, 1000);
          } else {
            console.log('\n✅ ALL BETS CAPTURED!');
            console.log('   Run: downloadAllBets() to save them');
            if (autoLoadInterval) {
              clearInterval(autoLoadInterval);
              autoLoadInterval = null;
            }
          }
        }
      } catch (e) {
        console.error('Failed to parse response:', e);
      }
    });
  }
  return originalXHRSend.apply(this, arguments);
};

// Auto-scroll function to keep triggering loads
function autoScroll() {
  if (window.allCapturedBets.length < totalRowsExpected || totalRowsExpected === 0) {
    // Scroll to bottom
    window.scrollTo(0, document.body.scrollHeight);
    
    // Also try scrolling the bet history container if it exists
    const container = document.querySelector('.bet-history-container, .infinite-scroll-container, [infinite-scroll]');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  } else if (totalRowsExpected > 0) {
    console.log('✅ Auto-scroll stopped - all bets captured!');
    clearInterval(autoLoadInterval);
    autoLoadInterval = null;
  }
}

// Start auto-scrolling every 2 seconds
autoLoadInterval = setInterval(autoScroll, 2000);

// Function to download all captured bets
window.downloadAllBets = function() {
  // Deduplicate
  const unique = [];
  const seen = new Set();
  
  for (const bet of window.allCapturedBets) {
    const key = `${bet.TicketNumber}`;
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

// Function to stop auto-scrolling
window.stopAutoScroll = function() {
  if (autoLoadInterval) {
    clearInterval(autoLoadInterval);
    autoLoadInterval = null;
    console.log('🛑 Auto-scroll stopped');
  }
};

// Function to check status
window.checkStatus = function() {
  console.log('\n📊 STATUS:');
  console.log(`   Captured: ${window.allCapturedBets.length}/${totalRowsExpected}`);
  console.log(`   Missing: ${totalRowsExpected - window.allCapturedBets.length}`);
  console.log(`   Auto-scroll: ${autoLoadInterval ? 'RUNNING' : 'STOPPED'}`);
};

console.log('✅ Interceptor installed!');
console.log('🔄 Auto-scrolling ENABLED - will scroll every 2 seconds');
console.log('\nCommands:');
console.log('  checkStatus()      - Check how many bets captured');
console.log('  stopAutoScroll()   - Stop auto-scrolling');
console.log('  downloadAllBets()  - Download captured bets');
console.log('\nThe page will auto-scroll to load all bets. Just wait!');
