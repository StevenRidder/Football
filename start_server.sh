#!/bin/bash
# Start the NFL betting application server

cd /Users/steveridder/Git/Football

echo "=========================================="
echo "Starting NFL Betting Application"
echo "=========================================="

# Check if already running
if lsof -ti:9876 > /dev/null 2>&1; then
    echo "⚠️  Server already running on port 9876"
    echo "Run ./stop_server.sh first to stop it"
    exit 1
fi

# Start Flask in background (without auto-reload to prevent hangs)
echo "Starting Flask server..."
nohup python3 -m flask --app app_flask run --port 9876 --no-reload > flask.log 2>&1 &
FLASK_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Check if it's running
if lsof -ti:9876 > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo ""
    echo "Access the application at:"
    echo "  http://localhost:9876/"
    echo ""
    echo "Logs: tail -f flask.log"
    echo "Stop: ./stop_server.sh"
else
    echo "❌ Server failed to start"
    echo "Check flask.log for errors:"
    tail -20 flask.log
    exit 1
fi

