#!/bin/bash
# Check status of the NFL betting application server

echo "=========================================="
echo "NFL Betting Application Status"
echo "=========================================="

# Check if running
if lsof -ti:9876 > /dev/null 2>&1; then
    PIDS=$(lsof -ti:9876)
    echo "✅ Server is RUNNING"
    echo ""
    echo "Process IDs: $PIDS"
    echo "Port: 9876"
    echo "URL: http://localhost:9876/"
    echo ""
    echo "Recent logs:"
    tail -10 /Users/steveridder/Git/Football/flask.log
else
    echo "❌ Server is NOT RUNNING"
    echo ""
    echo "Start it with: ./start_server.sh"
fi

