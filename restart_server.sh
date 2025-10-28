#!/bin/bash
# Restart the NFL betting application server

cd /Users/steveridder/Git/Football

echo "=========================================="
echo "Restarting NFL Betting Application"
echo "=========================================="

# Stop first
./stop_server.sh

# Wait a moment
sleep 2

# Start
./start_server.sh

