# BetOnline Data Extractor Bookmarklet

## Instructions

1. **Refresh the BetOnline bet history page** (to recover from the crash)
2. **Create a new bookmark** in Chrome
3. **Name it**: "Extract Bets"
4. **Paste this as the URL**:

```javascript
javascript:(function(){const d=document;const w=window;const s=d.createElement('script');s.src='data:text/javascript,'+encodeURIComponent(`(async()=>{const AUTH=prompt("Paste Bearer token (from Network tab):");if(!AUTH)return alert("No token!");const BASE="https://api.betonline.ag/report/api/report/get-bet-history";const PAGE_SIZE=100;const YEAR_START="2025-01-01T00:00:00.000Z";const YEAR_END="2025-12-31T23:59:59.999Z";const sleep=ms=>new Promise(r=>setTimeout(r,ms));async function postHistory(body){const r=await fetch(BASE,{method:"POST",headers:{"accept":"application/json, text/plain, */*","content-type":"application/json","authorization":AUTH},body:JSON.stringify(body)});if(r.status===429){await sleep(60000);return postHistory(body);}if(r.status===401||r.status===403)throw new Error("Auth failed");if(!r.ok)throw new Error("HTTP "+r.status);return r.json();}console.log("Probing...");const probe=await postHistory({Id:null,StartDate:YEAR_START,EndDate:YEAR_END,Status:null,Product:null,WagerType:null,FreePlayFlag:null,StartPosition:0,TotalPerPage:1,IsDailyFigureReport:false});console.log("TotalRows=",probe.TotalRows);if((probe.TotalRows??0)===0){alert("No data!");return;}console.log("Fetching...");const rows=[];for(let off=0;off<1000;off+=PAGE_SIZE){const page=await postHistory({Id:null,StartDate:YEAR_START,EndDate:YEAR_END,Status:null,Product:null,WagerType:null,FreePlayFlag:null,StartPosition:off,TotalPerPage:PAGE_SIZE,IsDailyFigureReport:false});const got=page.Data?.length||0;console.log(off,"→",got);rows.push(...(page.Data||[]));if(got<PAGE_SIZE)break;await sleep(1500);}const P=rows.filter(r=>r.WagerStatus==="Pending");const sum=(arr,f)=>arr.reduce((s,r)=>s+Number(f(r)||0),0);console.log("SUCCESS! Total:",rows.length,"Pending:",P.length,"Stake:$"+sum(P,r=>r.Risk).toFixed(2));const url=URL.createObjectURL(new Blob([JSON.stringify(rows,null,2)],{type:"application/json"}));Object.assign(document.createElement("a"),{href:url,download:"all_bets.json"}).click();URL.revokeObjectURL(url);alert("Downloaded all_bets.json!");})();`);d.body.appendChild(s);})();
```

5. **Click the bookmarklet**
6. **Paste the Bearer token** when prompted
7. **Wait for the download**

## Alternative: Manual Console Method

If the bookmarklet doesn't work, **refresh the page**, open Console, and paste this:

```javascript
(async () => {
    const AUTH = prompt("Paste Bearer token:");
    if (!AUTH) return alert("No token!");
    
    const BASE = 'https://api.betonline.ag/report/api/report/get-bet-history';
    const PAGE_SIZE = 100;
    const YEAR_START = '2025-01-01T00:00:00.000Z';
    const YEAR_END = '2025-12-31T23:59:59.999Z';
    
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    
    async function postHistory(body) {
        const r = await fetch(BASE, {
            method: 'POST',
            headers: {
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'authorization': AUTH
            },
            body: JSON.stringify(body)
        });
        if (r.status === 429) { await sleep(60000); return postHistory(body); }
        if (r.status === 401 || r.status === 403) throw new Error('Auth failed');
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    }
    
    console.log('🔍 Probing...');
    const probe = await postHistory({
        Id: null, StartDate: YEAR_START, EndDate: YEAR_END, Status: null,
        Product: null, WagerType: null, FreePlayFlag: null,
        StartPosition: 0, TotalPerPage: 1, IsDailyFigureReport: false
    });
    
    console.log('✅ TotalRows=', probe.TotalRows);
    
    if ((probe.TotalRows ?? 0) === 0) {
        alert('No data!');
        return;
    }
    
    console.log('📥 Fetching...');
    const rows = [];
    for (let off = 0; off < 1000; off += PAGE_SIZE) {
        const page = await postHistory({
            Id: null, StartDate: YEAR_START, EndDate: YEAR_END, Status: null,
            Product: null, WagerType: null, FreePlayFlag: null,
            StartPosition: off, TotalPerPage: PAGE_SIZE, IsDailyFigureReport: false
        });
        const got = page.Data?.length || 0;
        console.log(`  ${off} → ${got}`);
        rows.push(...(page.Data || []));
        if (got < PAGE_SIZE) break;
        await sleep(1500);
    }
    
    const P = rows.filter(r => r.WagerStatus === 'Pending');
    const sum = (arr, f) => arr.reduce((s, r) => s + Number(f(r) || 0), 0);
    
    console.log('='.repeat(60));
    console.log('✅ SUCCESS!');
    console.log('Total:', rows.length, '| Pending:', P.length);
    console.log('Stake: $' + sum(P, r => r.Risk).toFixed(2));
    console.log('='.repeat(60));
    
    const url = URL.createObjectURL(new Blob([JSON.stringify(rows, null, 2)], {type:'application/json'}));
    Object.assign(document.createElement('a'), {href:url, download:'all_bets.json'}).click();
    URL.revokeObjectURL(url);
    
    alert('Downloaded all_bets.json!');
    window.ALL_BETS = rows;
})();
```

## What to do with the downloaded file

Once you have `all_bets.json`, upload it here and I'll import it into the database!

