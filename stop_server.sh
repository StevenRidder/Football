#!/bin/bash
# Stop the NFL betting application server

echo "=========================================="
echo "Stopping NFL Betting Application"
echo "=========================================="

# Find and kill processes on port 9876
PIDS=$(lsof -ti:9876)

if [ -z "$PIDS" ]; then
    echo "ℹ️  No server running on port 9876"
    exit 0
fi

echo "Found server processes: $PIDS"
echo "Stopping..."

# Kill the processes
kill -9 $PIDS 2>/dev/null

# Wait a moment
sleep 1

# Verify stopped
if lsof -ti:9876 > /dev/null 2>&1; then
    echo "❌ Failed to stop server"
    exit 1
else
    echo "✅ Server stopped successfully"
fi

