// Content script to extract auth token from the page

// Function to get auth token from localStorage, sessionStorage, or window
function getAuthToken() {
  console.log('[BetOnline Fetcher] Searching for auth token...');
  
  // Try localStorage - search ALL keys
  console.log('[BetOnline Fetcher] Checking localStorage...');
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    const value = localStorage.getItem(key);
    
    // Special handling for kc-callback (Keycloak)
    if (key.startsWith('kc-callback')) {
      console.log(`[BetOnline Fetcher] Found Keycloak callback: ${key}`);
      try {
        const parsed = JSON.parse(value);
        console.log(`[BetOnline Fetcher] Keycloak data:`, parsed);
        
        // Check all nested properties
        const searchObject = (obj, path = '') => {
          for (const [k, v] of Object.entries(obj)) {
            const currentPath = path ? `${path}.${k}` : k;
            if (typeof v === 'string' && v.startsWith('eyJ') && v.length > 100) {
              console.log(`[BetOnline Fetcher] Found token at ${currentPath}`);
              return v;
            }
            if (typeof v === 'object' && v !== null) {
              const result = searchObject(v, currentPath);
              if (result) return result;
            }
          }
          return null;
        };
        
        const token = searchObject(parsed);
        if (token) return token;
      } catch (e) {
        console.log(`[BetOnline Fetcher] Error parsing Keycloak data:`, e);
      }
    }
    
    if (value) {
      // Check if value contains JWT token
      if (value.includes('eyJ')) {
        try {
          const parsed = JSON.parse(value);
          // Check common token field names
          const tokenFields = ['access_token', 'accessToken', 'token', 'idToken', 'id_token', 'jwt', 'bearer'];
          for (const field of tokenFields) {
            if (parsed[field] && parsed[field].startsWith('eyJ')) {
              console.log(`[BetOnline Fetcher] Found token in localStorage.${key}.${field}`);
              return parsed[field];
            }
          }
        } catch {
          // Not JSON, check if it's a raw token
          if (value.startsWith('eyJ') && value.length > 100) {
            console.log(`[BetOnline Fetcher] Found raw token in localStorage.${key}`);
            return value;
          }
        }
      }
    }
  }
  
  // Try sessionStorage - search ALL keys
  console.log('[BetOnline Fetcher] Checking sessionStorage...');
  for (let i = 0; i < sessionStorage.length; i++) {
    const key = sessionStorage.key(i);
    const value = sessionStorage.getItem(key);
    console.log(`[BetOnline Fetcher] sessionStorage[${key}] = ${value?.substring(0, 50)}...`);
    
    if (value) {
      if (value.includes('eyJ')) {
        try {
          const parsed = JSON.parse(value);
          const tokenFields = ['access_token', 'accessToken', 'token', 'idToken', 'id_token', 'jwt', 'bearer'];
          for (const field of tokenFields) {
            if (parsed[field] && parsed[field].startsWith('eyJ')) {
              console.log(`[BetOnline Fetcher] Found token in sessionStorage.${key}.${field}`);
              return parsed[field];
            }
          }
        } catch {
          if (value.startsWith('eyJ') && value.length > 100) {
            console.log(`[BetOnline Fetcher] Found raw token in sessionStorage.${key}`);
            return value;
          }
        }
      }
    }
  }
  
  // Try window object properties
  console.log('[BetOnline Fetcher] Checking window object...');
  const windowProps = ['authToken', 'accessToken', 'token', 'idToken', 'jwt', 'bearer', 'auth'];
  for (const prop of windowProps) {
    if (window[prop]) {
      console.log(`[BetOnline Fetcher] Found window.${prop}`);
      if (typeof window[prop] === 'string' && window[prop].startsWith('eyJ')) {
        return window[prop];
      }
      if (typeof window[prop] === 'object' && window[prop].access_token) {
        return window[prop].access_token;
      }
    }
  }
  
  console.log('[BetOnline Fetcher] No token found');
  return null;
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getAuthToken') {
    const token = getAuthToken();
    sendResponse({ token });
  }
  
  if (request.action === 'injectScript') {
    // Inject the script into the page context
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('injected.js');
    script.onload = function() {
      this.remove();
      sendResponse({ success: true });
    };
    script.onerror = function() {
      sendResponse({ success: false, error: 'Failed to inject script' });
    };
    (document.head || document.documentElement).appendChild(script);
    return true; // Keep channel open for async response
  }
  
  return true;
});

// Listen for messages from injected script
window.addEventListener('message', (event) => {
  if (event.source !== window) return;
  
  if (event.data.type === 'BETONLINE_FETCH_COMPLETE') {
    chrome.runtime.sendMessage({
      action: 'fetchComplete',
      bets: event.data.bets
    });
  }
  
  if (event.data.type === 'BETONLINE_FETCH_ERROR') {
    chrome.runtime.sendMessage({
      action: 'fetchError',
      error: event.data.error
    });
  }
});

