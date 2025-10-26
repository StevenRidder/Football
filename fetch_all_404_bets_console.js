// Run this in the browser console on betonline.ag
// It will fetch ALL bets by paginating through the API

// 1) Get the Bearer token from the last request in Network tab
// Or paste it here:
const AUTH = 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJTQS1hVUczc05wcnZkSkVRSlZtTW1OVWxSLVNJOHBWZHNtSHV4enp6OUNRIn0.eyJleHAiOjE3NjE0NDI1OTksImlhdCI6MTc2MTQ0MjI5OSwiYXV0aF90aW1lIjoxNzYxNDIyODMyLCJqdGkiOiI5NmViOTlkMy01ZmY4LTQzZjUtOTMwNy04NjU4NDAyMjJiODEiLCJpc3MiOiJodHRwczovL2FwaS5iZXRvbmxpbmUuYWcvYXBpL2F1dGgvcmVhbG1zL2JldG9ubGluZSIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjMjQ4MzE5My0wOTBkLTQ5OGQtOWFjNC0yY2YyMDljNjRkMTkiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJiZXRvbmxpbmUtd2ViIiwibm9uY2UiOiJhZWI0ODU2ZC1hNDhlLTRmYzktODI0Yi1jYTEyZjhkMjVmYzUiLCJzZXNzaW9uX3N0YXRlIjoiMjMyMDI2N2ItNDk5NS00ODU0LWI2MzYtNjcwM2U0MmM3M2ViIiwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iLCJkZWZhdWx0LXJvbGVzLWJldG9ubGluZSJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHRlc3QtYWNjb3VudCBzZWN1cml0eS1mbGFncyBlbWFpbCBwcm9maWxlIiwic2lkIjoiMjMyMDI2N2ItNDk5NS00ODU0LWI2MzYtNjcwM2U0MmM3M2ViIiwiYmlydGhkYXRlIjoiMTk5MS0wNi0xOSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6IkxpemV0aCBSaWRkZXIiLCJ0cnVzdGVkRGV2aWNlRW5hYmxlZCI6dHJ1ZSwicHJlZmVycmVkX3VzZXJuYW1lIjoiYjU5MjQ1NzgiLCJ0ZXN0X2FjY291bnQiOmZhbHNlLCJnaXZlbl9uYW1lIjoiTGl6ZXRoIiwiZmFtaWx5X25hbWUiOiJSaWRkZXIiLCJ0ZmEiOmZhbHNlLCJlbWFpbCI6InNhcmlkZGVyQGdtYWlsLmNvbSJ9.V2iKAE1zNUh_4ejCszojp3RL7HC_NzSQs3Gcn11RzJOD-LLTf_VKMO5Mkc72tVeks0V1CG0Gre2ThKEEBOUvqAT5GCKEim6quy41SoCJE5ZcTVoDBDQoT37t4A59UANJ7zkSypGYbZTV1ss1iKTk0izn_qo5QGQmYo_MJPVoh7RT-st0nIjs0zCIl8oysHKhP4bwZThudxybN5LlSowTyQkyDqZdSK_a75vAGd-5Pl75brDK2njQd3tjvzu0KEIQpo-T6RfbQW6yWnsydM6jNgVHBwGMJ3sIGPffR2xElH3dFJuR5FjhiFftZLVDYf6M8-1NJB2XnO-N8lJrlw';

const BASE = 'https://api.betonline.ag/report/api/report/get-bet-history';

// Wide date window to catch all pending bets
const START_DATE = '2025-01-01T00:00:00.000Z';
const END_DATE   = '2025-12-31T23:59:59.999Z';

// Only pending bets
const STATUS = 'Pending';

async function fetchPage(offset = 0, size = 100) {
  const body = {
    Id: null,
    StartDate: START_DATE,
    EndDate: END_DATE,
    Status: STATUS,
    Product: null,
    WagerType: null,
    FreePlayFlag: null,
    StartPosition: offset,
    TotalPerPage: size,
    IsDailyFigureReport: false
  };
  
  const resp = await fetch(BASE, {
    method: 'POST',
    headers: {
      'accept': 'application/json, text/plain, */*',
      'content-type': 'application/json',
      'authorization': AUTH
    },
    body: JSON.stringify(body)
  });
  
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

async function pullAll() {
  const size = 100;
  let offset = 0;
  const rows = [];
  
  while (true) {
    console.log(`Fetching offset ${offset}...`);
    const page = await fetchPage(offset, size);
    rows.push(...page.Data);
    console.log(`✓ Got ${page.Data.length} bets at offset ${offset} (TotalRows=${page.TotalRows})`);
    
    if (page.Data.length < size) {
      console.log('✓ Reached last page');
      break;
    }
    offset += size;
    
    // Small delay to avoid rate limiting
    await new Promise(r => setTimeout(r, 500));
  }
  
  return rows;
}

console.log('🚀 Starting to fetch ALL bets...');
pullAll().then(rows => {
  const asNum = x => Number(x || 0);
  const pending = rows.filter(r => r.WagerStatus === 'Pending');
  const stake = pending.reduce((s, r) => s + asNum(r.Risk), 0);
  const toWin = pending.reduce((s, r) => s + asNum(r.ToWin), 0);
  
  console.log('');
  console.log('='.repeat(60));
  console.log('✅ COMPLETE!');
  console.log('='.repeat(60));
  console.log(`Total bets fetched: ${rows.length}`);
  console.log(`Pending bets: ${pending.length}`);
  console.log(`Total stake (Risk): $${stake.toFixed(2)}`);
  console.log(`Total to win: $${toWin.toFixed(2)}`);
  console.log('='.repeat(60));
  
  // Download as JSON
  const json = JSON.stringify(rows, null, 2);
  const blob = new Blob([json], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), {href:url, download:'all_404_bets.json'});
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('📥 Downloaded all_404_bets.json');
  console.log('');
  console.log('Copy this file to your Football directory and run import script');
  
}).catch(err => {
  console.error('❌ Error:', err);
  console.log('Token may have expired. Get a fresh one from Network tab.');
});
