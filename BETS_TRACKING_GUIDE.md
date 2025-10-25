# My Bets Tracking - User Guide

## ✅ What's Been Built

I've created a beautiful, fully-functional bet tracking system using Tabler UI framework with:

1. **Paste Interface**: Simple text area to paste your bet data
2. **Summary Cards**: Shows total profit/loss, wagered amount, pending bets, and potential win
3. **Filterable Table**: Beautiful Tabler table with:
   - Search bar (searches all fields)
   - Type filter (Spread, Parlay, Same Game Parlay, Live)
   - Status filter (Pending, Won, Lost)
   - Date range filters (From/To dates)
4. **Color-coded Status Badges**: 
   - Yellow for Pending
   - Green for Won
   - Red for Lost
5. **Profit/Loss Display**: Color-coded profit column (green for wins, red for losses)

## 🚀 How to Use

### Step 1: Format Your Bet Data

Your bet data should be in pipe-delimited format:
```
Ticket#|Date|Description|Type|Status|Amount|ToWin
```

Example:
```
906320708-1|10/25/2025|FOOTBALL - NFL - New England Patriots v Cleveland Browns|Same Game Parlay|Pending|6.33|41.15
905836544-1|10/24/2025|VIKINGS at CHARGERS - Total - OVER 41.5|Live|Won|20.00|16.67
```

### Step 2: Paste Into Web Interface

1. Go to http://localhost:9876/bets
2. Paste your formatted bet data into the text area
3. Click "Load Bets"
4. Your bets will be parsed, saved, and displayed in a beautiful table

### Step 3: Use the Filters

- **Search**: Type anything to search across all fields
- **Type Filter**: Select bet type (Spread, Parlay, etc.)
- **Status Filter**: Show only Pending, Won, or Lost bets
- **Date Range**: Filter by date range

### Step 4: View Your Stats

The summary cards at the top show:
- **Total Profit/Loss**: Your net profit (green) or loss (red)
- **Total Wagered**: Total amount you've bet
- **Pending Bets**: Number and amount of pending bets
- **Potential Win**: Total potential winnings from pending bets

## 📊 Your Current Bets (Already Loaded)

I've already loaded your 14 bets into the system:
- **Total Wagered**: $336.33
- **Current Profit/Loss**: -$63.33 (from settled bets)
- **Pending**: 9 bets ($236.33)
- **Potential Win**: $109,879.54

## 🎨 Features

### Tabler Framework
- Clean, modern design
- Responsive layout
- Professional color scheme
- Smooth filtering animations

### Data Persistence
- Bets are saved to `artifacts/betonline_bets.json`
- Survives page refreshes
- Can be cleared with "Clear All" button

### Smart Parsing
- Automatically calculates profit/loss based on status
- Handles various bet types
- Truncates long descriptions with hover tooltips

## 🔧 Technical Details

### API Endpoints
- `POST /api/bets/paste`: Parse and save pasted bet data
- `POST /api/bets/clear`: Clear all bets
- `GET /bets`: Display bets page

### Data Format
```json
{
  "timestamp": "2025-10-25T...",
  "summary": {
    "total_bets": 14,
    "total_amount": 336.33,
    "total_profit": -63.33,
    "pending_count": 9,
    "potential_win": 109879.54
  },
  "bets": [...]
}
```

## 📝 Adding More Bets

To add more bets later:
1. Copy your new bet data from BetOnline
2. Format it in the pipe-delimited format
3. Paste into the interface
4. Click "Load Bets" (it will replace the old data)

## 🎯 Next Steps (Optional Enhancements)

If you want to enhance this further, we could add:
- **Export to CSV**: Download your bet history
- **Charts**: Profit/loss over time, win rate by bet type
- **Model Comparison**: Compare your bets vs. model recommendations
- **CLV Tracking**: Track closing line value
- **Weekly Breakdown**: Group bets by week
- **Bet Grading**: Auto-update status from game results

Let me know if you want any of these features!

