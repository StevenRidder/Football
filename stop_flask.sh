#!/bin/bash
# Stop Flask App
# Usage: ./stop_flask.sh

echo "🔍 Checking for running Flask processes..."
PIDS=$(pgrep -f "python3 app_flask.py")

if [ -n "$PIDS" ]; then
    echo "🛑 Stopping Flask (PIDs: $PIDS)..."
    pkill -9 -f "app_flask.py"
    sleep 1
    
    # Verify it stopped
    if pgrep -f "app_flask.py" > /dev/null; then
        echo "⚠️  Some Flask processes may still be running"
    else
        echo "✅ Flask stopped successfully"
    fi
else
    echo "ℹ️  No Flask processes found"
fi

