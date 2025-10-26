// Capture RAW responses before they're parsed
// Paste this BEFORE scrolling

console.log('🚀 Raw Response Capturer - Starting...\n');

window.allRawResponses = [];

// Intercept at a lower level - before Angular processes it
const originalXHROpen = XMLHttpRequest.prototype.open;
const originalXHRSend = XMLHttpRequest.prototype.send;

XMLHttpRequest.prototype.open = function(method, url, ...args) {
  this._url = url;
  this._method = method;
  return originalXHROpen.apply(this, [method, url, ...args]);
};

XMLHttpRequest.prototype.send = function(body) {
  const xhr = this;
  
  if (this._url && this._url.includes('get-bet-history')) {
    console.log(`📡 Intercepted request to: ${this._url}`);
    
    // Store the original onload
    const originalOnLoad = xhr.onload;
    const originalOnReadyStateChange = xhr.onreadystatechange;
    
    // Override onreadystatechange to capture response
    xhr.onreadystatechange = function() {
      if (xhr.readyState === 4 && xhr.status === 200) {
        const responseText = xhr.responseText;
        console.log(`✓ Captured response (${responseText.length} chars)`);
        
        if (responseText && responseText.length > 10) {
          try {
            const data = JSON.parse(responseText);
            window.allRawResponses.push(data);
            console.log(`  → Parsed: ${data.Data?.length || 0} bets, TotalRows: ${data.TotalRows}`);
          } catch (e) {
            console.error('  → Failed to parse:', e.message);
            window.allRawResponses.push({ raw: responseText });
          }
        } else {
          console.warn('  → Response is empty or too short!');
        }
      }
      
      if (originalOnReadyStateChange) {
        return originalOnReadyStateChange.apply(this, arguments);
      }
    };
  }
  
  return originalXHRSend.apply(this, arguments);
};

// Function to download all captured responses
window.downloadRawResponses = function() {
  console.log(`\n📥 Downloading ${window.allRawResponses.length} responses...`);
  
  const json = JSON.stringify(window.allRawResponses, null, 2);
  const blob = new Blob([json], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'raw_responses.json';
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('✅ Downloaded: raw_responses.json');
};

// Function to extract all bets
window.extractAllBets = function() {
  const allBets = [];
  
  for (const response of window.allRawResponses) {
    if (response.Data && Array.isArray(response.Data)) {
      allBets.push(...response.Data);
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
  
  console.log(`\n📊 Extracted ${unique.length} unique bets from ${window.allRawResponses.length} responses`);
  
  // Download
  const json = JSON.stringify(unique, null, 2);
  const blob = new Blob([json], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'all_bets_extracted.json';
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('✅ Downloaded: all_bets_extracted.json');
  
  return unique;
};

console.log('✅ Raw capturer installed!');
console.log('\nNow:');
console.log('1. Scroll down to load bets');
console.log('2. When done, run: extractAllBets()');
console.log('3. Or run: downloadRawResponses() to see all responses');

