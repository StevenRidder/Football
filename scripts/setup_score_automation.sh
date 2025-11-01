#!/bin/bash
# Setup automatic score fetching during NFL season
# Run this script once to set up hourly score updates

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
PYTHON_BIN="python3"

echo "🏈 Setting up NFL Live Score Automation"
echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Create a temporary crontab file
TEMP_CRON=$(mktemp)

# Get existing crontab (if any)
crontab -l > "$TEMP_CRON" 2>/dev/null || true

# Remove any existing NFL score fetcher entries
grep -v "fetch_live_scores.py" "$TEMP_CRON" > "${TEMP_CRON}.tmp" || true
mv "${TEMP_CRON}.tmp" "$TEMP_CRON"

# Add new cron job - run every hour on NFL game days (Thursday, Sunday, Monday)
echo "# NFL Live Scores - Run every hour during game days" >> "$TEMP_CRON"
echo "0 * * * 4,0,1 cd $PROJECT_DIR && $PYTHON_BIN scripts/fetch_live_scores.py >> logs/score_fetcher.log 2>&1" >> "$TEMP_CRON"

# Also run every 15 minutes on Sunday afternoons (1pm-8pm ET) for live updates
echo "# NFL Live Scores - Every 15 minutes on Sunday afternoons" >> "$TEMP_CRON"
echo "*/15 13-20 * * 0 cd $PROJECT_DIR && $PYTHON_BIN scripts/fetch_live_scores.py >> logs/score_fetcher.log 2>&1" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"

# Clean up
rm "$TEMP_CRON"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

echo "✅ Cron jobs installed!"
echo ""
echo "📅 Schedule:"
echo "   - Every hour on Thu/Sun/Mon (game days)"
echo "   - Every 15 min on Sun 1-8pm ET (live games)"
echo ""
echo "📋 To view installed cron jobs: crontab -l"
echo "📊 To view logs: tail -f $PROJECT_DIR/logs/score_fetcher.log"
echo ""
echo "💡 To manually fetch scores now: python3 scripts/fetch_live_scores.py"

