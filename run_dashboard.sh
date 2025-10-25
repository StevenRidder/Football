#!/bin/bash
# Run the Tabler-based Flask dashboard

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Install Flask if needed
pip install flask -q

# Export ODDS_API_KEY for predictions
export ODDS_API_KEY="649f1767c6550bc2612b8da6685d1774"

# Run Flask app
echo "🚀 Starting NFL Edge Tabler Dashboard..."
echo "📊 Dashboard will be available at: http://localhost:9876"
echo "🔑 ODDS_API_KEY configured for Vegas predictions"
echo ""
python3 app_flask.py

