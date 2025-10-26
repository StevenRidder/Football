#!/bin/bash
# Setup daily cron job to update model performance
# Run this once to install the cron job

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CRON_CMD="0 2 * * * cd $SCRIPT_DIR && /usr/bin/python3 update_model_performance.py >> $SCRIPT_DIR/logs/model_updates.log 2>&1"

echo "Setting up daily cron job to update model performance..."
echo "Will run at 2 AM every day"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "update_model_performance.py"; then
    echo "⚠️  Cron job already exists. Removing old one..."
    crontab -l 2>/dev/null | grep -v "update_model_performance.py" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "To verify, run: crontab -l"
echo "To remove, run: crontab -l | grep -v 'update_model_performance.py' | crontab -"
echo ""
echo "Manual run: cd $SCRIPT_DIR && python3 update_model_performance.py"

