#!/bin/bash
# Watch backtest progress

echo "🔍 BACKTEST PROGRESS MONITOR"
echo "=============================="
echo ""

# Check if process is running
if ps aux | grep "python3 backtest_proper.py" | grep -v grep > /dev/null; then
    echo "✅ Backtest is RUNNING"
    echo ""
else
    echo "⚠️  Backtest process not found"
    echo ""
fi

# Show last 30 lines of log
echo "📋 Last 30 lines of log:"
echo "------------------------"
tail -30 backtest_full.log 2>/dev/null || echo "No log file yet..."

echo ""
echo "------------------------"

# Check output file
if [ -f "artifacts/backtest_proper.csv" ]; then
    ROWS=$(wc -l < artifacts/backtest_proper.csv)
    GAMES=$((ROWS - 1))
    echo "📊 Games completed: $GAMES / 831"
    
    if [ $GAMES -gt 1 ]; then
        PERCENT=$((GAMES * 100 / 831))
        echo "📈 Progress: $PERCENT%"
    fi
else
    echo "📊 Output file not created yet..."
fi

echo ""
echo "Run this script again to check progress:"
echo "  bash watch_backtest.sh"

