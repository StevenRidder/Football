#!/bin/bash
# Restart Flask App
# Usage: ./restart_flask.sh

cd "$(dirname "$0")"

echo "🔍 Checking for running Flask processes..."
PIDS=$(pgrep -f "python3 app_flask.py")

if [ -n "$PIDS" ]; then
    echo "🛑 Stopping Flask (PIDs: $PIDS)..."
    pkill -9 -f "app_flask.py"
    sleep 2
    echo "✅ Flask stopped"
else
    echo "ℹ️  No Flask processes found"
fi

echo "🚀 Starting Flask..."
python3 app_flask.py > flask.log 2>&1 &
FLASK_PID=$!

sleep 3

# Check if Flask started successfully
if lsof -i :9876 > /dev/null 2>&1; then
    echo "✅ Flask is running on http://localhost:9876 (PID: $FLASK_PID)"
    echo "📋 Logs: tail -f flask.log"
else
    echo "❌ Flask failed to start. Check flask.log for errors"
    exit 1
fi

