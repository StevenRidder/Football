document.getElementById('fetchBtn').addEventListener('click', fetchAllBets);

async function fetchAllBets() {
  const btn = document.getElementById('fetchBtn');
  const status = document.getElementById('status');
  
  btn.disabled = true;
  status.innerHTML = '<div class="progress">🔄 Injecting script into page...</div>';
  
  try {
    // Get active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Inject the script into the page context
    const response = await chrome.tabs.sendMessage(tab.id, { action: 'injectScript' });
    
    if (!response.success) {
      throw new Error(response.error || 'Failed to inject script');
    }
    
    status.innerHTML = '<div class="progress">✓ Script injected! Fetching all bets...</div><div>Check the page console for progress...</div>';
    
    // Listen for completion
    const listener = (message) => {
      if (message.action === 'fetchComplete') {
        status.innerHTML = `
          <div class="progress">✅ COMPLETE!</div>
          <div>Total bets: ${message.bets}</div>
          <div>📥 File downloaded!</div>
        `;
        btn.disabled = false;
        chrome.runtime.onMessage.removeListener(listener);
      }
      
      if (message.action === 'fetchError') {
        status.innerHTML = `<div style="color: red;">❌ Error: ${message.error}</div>`;
        btn.disabled = false;
        chrome.runtime.onMessage.removeListener(listener);
      }
    };
    
    chrome.runtime.onMessage.addListener(listener);
    
    // Timeout after 60 seconds
    setTimeout(() => {
      status.innerHTML += '<div>⏱️ Taking longer than expected... Check console for progress</div>';
    }, 10000);
    
  } catch (error) {
    status.innerHTML = `<div style="color: red;">❌ Error: ${error.message}</div>`;
    btn.disabled = false;
  }
}
