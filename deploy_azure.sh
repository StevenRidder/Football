#!/bin/bash
# Azure VM Deployment Script for Football Betting Tracker
# Run this ON THE AZURE VM after cloning the repo

set -e

echo "🚀 Starting deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv postgresql-client nginx

# Create app directory
APP_DIR="/home/azureuser/Football"
cd $APP_DIR

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install Flask psycopg psycopg-binary psycopg2-binary requests numpy pandas scikit-learn

# Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/football-tracker.service > /dev/null <<EOF
[Unit]
Description=Football Betting Tracker
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python3 $APP_DIR/app_flask.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx as reverse proxy
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/football-tracker > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:9876;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed later)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/football-tracker /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Start the service
echo "🎯 Starting Football Tracker service..."
sudo systemctl daemon-reload
sudo systemctl enable football-tracker
sudo systemctl start football-tracker

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service status:"
sudo systemctl status football-tracker --no-pager
echo ""
echo "🌍 Your app is now running!"
echo "   Access it at: http://YOUR_VM_IP"
echo ""
echo "📝 Useful commands:"
echo "   View logs:    sudo journalctl -u football-tracker -f"
echo "   Restart app:  sudo systemctl restart football-tracker"
echo "   Stop app:     sudo systemctl stop football-tracker"

