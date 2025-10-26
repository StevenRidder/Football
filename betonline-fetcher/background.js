// Background script to handle CORS-free requests

let authToken = null;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fetchBets') {
    fetchAllBets(request.startPosition, request.pageSize)
      .then(data => sendResponse({ success: true, data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open for async response
  }
});

async function fetchAllBets(startPosition, pageSize) {
  const url = 'https://api.betonline.ag/report/api/report/get-bet-history';
  
  // Get current timestamps
  const now = new Date();
  const actualTime = now.getTime();
  const isoTime = now.toISOString();
  const utcTime = now.toUTCString();
  const gmtOffset = -now.getTimezoneOffset() / 60;
  const utcOffset = Math.abs(now.getTimezoneOffset());
  
  // Calculate date range
  const endDate = now.toISOString();
  const startDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString(); // 1 year ago
  
  const headers = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'actual-time': actualTime.toString(),
    'iso-time': isoTime,
    'utc-time': utcTime,
    'gmt-offset': gmtOffset.toString(),
    'utc-offset': utcOffset.toString(),
    'contests': 'na',
    'gsetting': 'bolnasite',
    'Origin': 'https://www.betonline.ag',
    'Referer': 'https://www.betonline.ag/'
  };
  
  const response = await fetch(url, {
    method: 'POST',
    headers: headers,
    credentials: 'include',
    body: JSON.stringify({
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
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return await response.json();
}

