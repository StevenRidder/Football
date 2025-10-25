# ✅ Parlay Details Display - Complete Guide

## What's Been Fixed

Your bet tracking system now **properly displays all parlay legs** when you click on a parlay bet!

## How It Works

### 📋 Data Format

To see all parlay legs, format your bet data like this:

```
TicketID|Date|Leg1|Leg2|Leg3|...|Type|Status|Amount|ToWin
```

**Example 5-team parlay:**
```
905768987-76|10/23/2025|Dallas Cowboys +3½ -118|Miami Dolphins +7½ -112|Green Bay/Pittsburgh over 46 -110|Cincinnati Bengals -6½ -108|Carolina Panthers +7½ -116|Parlay|Pending|1.00|22.93
```

### 🎯 What You'll See

When you click on a parlay bet, the modal displays:

1. **Numbered List** - Each leg gets a blue numbered badge (1, 2, 3, etc.)
2. **Leg Details** - Full description of each bet
3. **Odds Badges** - Odds displayed in green badges (e.g., -118, -110)
4. **Summary** - "5 legs in this Parlay" at the bottom

### 🎨 Visual Design

- **List Group**: Clean Tabler list with separators
- **Blue Badges**: Numbered 1-5 for each leg
- **Green Odds Badges**: Shows the odds for each leg
- **Bold Text**: Team names and bet details stand out
- **Responsive**: Works on all screen sizes

## Example Display

For the 5-team parlay above, you'll see:

```
┌─────────────────────────────────────────────┐
│ 🔵 1  Dallas Cowboys +3½ -118        [-118] │
├─────────────────────────────────────────────┤
│ 🔵 2  Miami Dolphins +7½ -112        [-112] │
├─────────────────────────────────────────────┤
│ 🔵 3  Green Bay/Pittsburgh over 46   [-110] │
├─────────────────────────────────────────────┤
│ 🔵 4  Cincinnati Bengals -6½ -108    [-108] │
├─────────────────────────────────────────────┤
│ 🔵 5  Carolina Panthers +7½ -116     [-116] │
└─────────────────────────────────────────────┘
         5 legs in this Parlay
```

## How to Format Your Bets

### Option 1: Manual Formatting

1. Go to BetOnline and click on your parlay
2. Copy each leg
3. Format as: `TicketID|Date|Leg1|Leg2|Leg3|Type|Status|Amount|ToWin`
4. Paste into the web interface

### Option 2: Use the Helper Script

```bash
python3 format_parlay_example.py
```

This shows you the exact format needed.

## Technical Details

### Backend Parser (`app_flask.py`)

- **Smart Parsing**: Recognizes that the last 4 fields are always Type, Status, Amount, ToWin
- **Everything in between** is treated as description/legs
- **Joins with ` | `**: Preserves the pipe separators for the frontend

### Frontend Display (`templates/bets.html`)

- **Detects ` | ` separator**: Knows when to parse legs
- **Splits and displays**: Each leg gets its own list item
- **Extracts odds**: Regex finds odds like "-118" or "+150"
- **Numbered badges**: Auto-numbers each leg

## Single Bets vs Parlays

### Single Bet
- No pipes in description
- Displays as simple text paragraph

### Parlay
- Pipes separate each leg
- Displays as numbered list
- Shows leg count at bottom

## Example Formats

### Same Game Parlay (4 legs):
```
905769902-1|10/23/2025|Total points - Over 40.5|Player TDs - Kayshon Boutte Score anytime|Player TDs - R. Stevenson Score anytime|Spread - Patriots -7.5|Same Game Parlay|Pending|25.00|250.00
```

### Regular Parlay (12 teams):
```
905966563-1|10/24/2025|Team1 +3|Team2 -7|Team3 over 45|Team4 -110|Team5 +6|Team6 -3|Team7 over 48|Team8 -14|Team9 +7.5|Team10 -6.5|Team11 over 46|Team12 -7|Parlay|Pending|15.00|37377.61
```

### Single Straight Bet:
```
905769168-1|10/23/2025|New England Patriots -7 -105|Spread|Pending|100.00|95.24
```

## Testing

1. Copy the example parlay line from `format_parlay_example.py`
2. Go to http://localhost:9876/bets
3. Paste into the text area
4. Click "Load Bets"
5. Click on the parlay row
6. **You'll see all 5 legs displayed beautifully!**

## Files Modified

- ✅ `app_flask.py`: Updated parser to handle multiple pipes
- ✅ `templates/bets.html`: Added `parseDescription()` function
- ✅ `format_parlay_example.py`: Helper script for formatting

**Your parlay bets now display perfectly with all legs visible!** 🎉

