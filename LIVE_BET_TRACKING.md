# Live Bet Tracking Feature

## Overview
Real-time bet status tracking that colors your bets **green** (winning), **red** (losing), or **yellow** (neutral) during live games.

## How It Works

### Data Source
- **ESPN API** (free, no authentication required)
- Updates every 30 seconds
- Supports: NFL, NCAAF, NBA, NCAAB, MLB, NHL

### Color Coding (Tabler Framework)
- 🟢 **Green** (`table-success`): Bet is currently winning
- 🔴 **Red** (`table-danger`): Bet is currently losing  
- 🟡 **Yellow** (`table-warning`): Bet is neutral/close
- ⚪ **White** (default): Game not live or no data

### Bet Types Supported
1. **Spread**: Compares current score differential to spread
2. **Moneyline**: Simple win/loss based on current score
3. **Over/Under**: Tracks if total is trending over/under

## Files Created

### Backend
- `live_bet_tracker.py` - Main tracking logic
  - Fetches live scores from ESPN
  - Matches bets to games
  - Determines win/loss status

### Frontend (Tabler-compliant)
- Updated `templates/bets.html`:
  - Auto-updates every 30 seconds
  - Uses official Tabler color classes
  - Adds pulsing "LIVE" badge
  - Hover shows live score

### API Endpoint
- `GET /api/live-bet-status`
  - Returns: `{ticket_number: {status, color, game}}`
  - Called automatically by frontend

## Usage

### Start the App
```bash
python3 app_flask.py
```

### View Live Bets
1. Go to: `http://localhost:9876/bets`
2. Bets will automatically color during live games
3. Hover over "LIVE" badge to see current score

## Tabler Framework Compliance

✅ **CSS**: Uses only Tabler custom properties:
- `--tblr-success-lt`, `--tblr-danger-lt`, `--tblr-warning-lt`
- `--tblr-table-bg`, `--tblr-table-hover-bg`

✅ **HTML**: Official Tabler/Bootstrap classes:
- `table-success`, `table-danger`, `table-warning`
- `badge`, `bg-success`, `bg-danger`, `bg-warning`
- `badge-pulse` (custom animation, Tabler-compatible)

✅ **JavaScript**: Bootstrap data attribute patterns:
- `document.addEventListener('DOMContentLoaded', ...)`
- `classList.add/remove` for official classes
- No custom CSS classes or variables

## Testing

### Test Live Tracker
```bash
python3 live_bet_tracker.py
```

### Manual Test
```python
from live_bet_tracker import LiveBetTracker

tracker = LiveBetTracker()
games = tracker.get_live_games('NFL')
print(f"Found {len(games)} live games")

statuses = tracker.update_all_bets()
for bet in statuses:
    if bet['live_status']:
        print(f"Ticket {bet['ticket_number']}: {bet['live_status']}")
```

## Customization

### Change Update Frequency
In `templates/bets.html`:
```javascript
// Update every 30 seconds (default)
liveStatusInterval = setInterval(updateLiveBetStatus, 30000);

// Change to 15 seconds
liveStatusInterval = setInterval(updateLiveBetStatus, 15000);
```

### Add More Sports
In `live_bet_tracker.py`:
```python
ESPN_SCOREBOARD_URLS = {
    'NFL': 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard',
    # Add more sports...
}
```

## Limitations

1. **Team Name Matching**: Simple string matching - may need refinement
2. **Bet Type Detection**: Extracts from description - may not catch all formats
3. **Rate Limiting**: ESPN API has no official rate limit, but we use 0.5s delays
4. **Live Games Only**: Only colors bets for games currently in progress

## Future Enhancements

- [ ] Better team name fuzzy matching
- [ ] Support for prop bets
- [ ] Live odds comparison
- [ ] Push notifications for bet status changes
- [ ] Historical win probability tracking

