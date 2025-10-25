#!/bin/bash
# Stop the Flask dashboard

echo "🛑 Stopping NFL Edge Dashboard..."

# Find and kill Flask process
pkill -f "python3 app_flask.py"

# Find and kill Streamlit if running
pkill -f "streamlit run app.py"

echo "✅ Dashboard stopped"
