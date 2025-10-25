#!/bin/bash
# Run the Tabler-based Flask dashboard

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Install Flask if needed
pip install flask -q

# Run Flask app
echo "🚀 Starting NFL Edge Tabler Dashboard..."
echo "📊 Dashboard will be available at: http://localhost:9876"
echo ""
python3 app_flask.py

