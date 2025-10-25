# BetOnline Bet Extractor Bookmarklet

Since BetOnline blocks API access, use this bookmarklet to extract your bets directly from their website.

## How to Install:

1. **Create a new bookmark** in your browser
2. **Name it:** "Extract BetOnline Bets"
3. **Paste this as the URL:**

```javascript
javascript:(function(){let bets=[];document.querySelectorAll('table tbody tr').forEach(row=>{let cells=row.querySelectorAll('td');if(cells.length>=7){let bet={ticket:cells[0]?.innerText?.trim()||'',date:cells[1]?.innerText?.trim()||'',description:cells[2]?.innerText?.trim()||'',type:cells[3]?.innerText?.trim()||'',status:cells[4]?.innerText?.trim()||'',amount:cells[5]?.innerText?.trim()||'',toWin:cells[6]?.innerText?.trim()||''};bets.push(`${bet.ticket}|${bet.date}|${bet.description}|${bet.type}|${bet.status}|${bet.amount}|${bet.toWin}`);}});let output=bets.join('\n');navigator.clipboard.writeText(output).then(()=>alert('✅ Copied '+bets.length+' bets to clipboard!\n\nNow paste into your Football app.')).catch(()=>{prompt('Copy this data:',output);});})();
```

## How to Use:

1. **Go to BetOnline** → My Account → Bet History
2. **Click the bookmarklet** you just created
3. It will **automatically copy** all visible bets to your clipboard
4. **Go to** http://localhost:9876/bets
5. **Paste** into the text box
6. **Click "Load Bets"**

## For Parlay Details:

The bookmarklet extracts what's visible on the page. To get parlay details:

1. **Click on each parlay** to expand it
2. **Run the bookmarklet again** - it will extract the expanded details
3. Or manually edit the description to add legs separated by `|`

## Alternative: Console Script

If the bookmarklet doesn't work, paste this in the browser console (F12 → Console):

```javascript
let bets = [];
document.querySelectorAll('table tbody tr').forEach(row => {
    let cells = row.querySelectorAll('td');
    if (cells.length >= 7) {
        let bet = {
            ticket: cells[0]?.innerText?.trim() || '',
            date: cells[1]?.innerText?.trim() || '',
            description: cells[2]?.innerText?.trim() || '',
            type: cells[3]?.innerText?.trim() || '',
            status: cells[4]?.innerText?.trim() || '',
            amount: cells[5]?.innerText?.trim() || '',
            toWin: cells[6]?.innerText?.trim() || ''
        };
        bets.push(`${bet.ticket}|${bet.date}|${bet.description}|${bet.type}|${bet.status}|${bet.amount}|${bet.toWin}`);
    }
});
let output = bets.join('\n');
console.log(output);
copy(output); // Copies to clipboard
alert('✅ Copied ' + bets.length + ' bets to clipboard!');
```

