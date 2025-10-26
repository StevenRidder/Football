# Azure Deployment Guide - Football Betting Tracker

## Step 1: Create Azure VM with Static IP (via Azure Portal)

### 1.1 Create the VM
1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Create a resource"** → **"Virtual Machine"**
3. Configure:
   - **Subscription**: Your subscription
   - **Resource Group**: Create new → `football-tracker-rg`
   - **VM Name**: `football-tracker-vm`
   - **Region**: Choose closest to you (e.g., `East US`)
   - **Image**: `Ubuntu Server 22.04 LTS`
   - **Size**: `B1s` (1 vCPU, 1 GB RAM) - **~$7.59/month**
   - **Authentication**: SSH public key
   - **Username**: `azureuser`
   - **SSH Key**: Generate new or use existing

### 1.2 Configure Networking
1. In the **Networking** tab:
   - **Public IP**: Click "Create new"
   - **Name**: `football-tracker-ip`
   - **Assignment**: **STATIC** ⚠️ (Important!)
   - **SKU**: Standard
   - **Inbound ports**: Select `HTTP (80)`, `HTTPS (443)`, `SSH (22)`

2. Click **"Review + Create"** → **"Create"**

### 1.3 Get Your Static IP
After deployment completes:
1. Go to your VM → **Overview**
2. Copy the **Public IP address** (e.g., `20.123.45.67`)
3. This IP is now **permanent** and won't change!

---

## Step 2: Deploy the Application

### 2.1 SSH into your VM
```bash
ssh azureuser@YOUR_STATIC_IP
```

### 2.2 Clone your repository
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/Football.git
cd Football
```

**OR** if you don't have it in GitHub yet, upload via SCP:
```bash
# Run this from your Mac (in a new terminal)
cd /Users/steveridder/Git
tar -czf football.tar.gz Football --exclude='Football/.git' --exclude='Football/__pycache__' --exclude='Football/data/raw_responses'
scp football.tar.gz azureuser@YOUR_STATIC_IP:~
```

Then on the VM:
```bash
tar -xzf football.tar.gz
cd Football
```

### 2.3 Run the deployment script
```bash
chmod +x deploy_azure.sh
./deploy_azure.sh
```

This will:
- ✅ Install Python, Nginx, PostgreSQL client
- ✅ Create a Python virtual environment
- ✅ Install all dependencies
- ✅ Set up systemd service (auto-restart on crash/reboot)
- ✅ Configure Nginx as reverse proxy
- ✅ Start the app

---

## Step 3: Set up PostgreSQL Database

### Option A: Use Azure Database for PostgreSQL (Recommended)
1. In Azure Portal → **"Create a resource"** → **"Azure Database for PostgreSQL"**
2. Choose **"Flexible Server"**
3. Configure:
   - **Server name**: `football-tracker-db`
   - **Region**: Same as your VM
   - **Compute + Storage**: Burstable, B1ms (1 vCore, 2 GB RAM) - **~$12/month**
   - **Admin username**: `footballadmin`
   - **Password**: Create a strong password
4. In **Networking** tab:
   - Add your VM's **private IP** to firewall rules
   - OR enable "Allow public access from any Azure service"
5. Create the database

Then update your VM's database connection:
```bash
# On the VM
cd ~/Football
nano nfl_edge/bets/db.py
```

Update the connection string:
```python
DB_CONFIG = {
    'host': 'football-tracker-db.postgres.database.azure.com',
    'database': 'postgres',
    'user': 'footballadmin',
    'password': 'YOUR_PASSWORD',
    'port': 5432
}
```

### Option B: Use Local PostgreSQL on VM (Cheaper but less reliable)
```bash
# On the VM
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres psql -c "CREATE DATABASE football_bets;"
sudo -u postgres psql -c "CREATE USER footballuser WITH PASSWORD 'yourpassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE football_bets TO footballuser;"
```

Then update `nfl_edge/bets/db.py` to use `localhost`.

### 2.4 Import your existing bets
```bash
# On the VM
cd ~/Football
source venv/bin/activate
python3 import_existing_data.py  # If you have this script
```

---

## Step 4: Access Your App

🎉 **Your app is now live at:**
```
http://YOUR_STATIC_IP
```

Example: `http://20.123.45.67`

You can access it from:
- ✅ Your phone
- ✅ Any computer
- ✅ Anywhere in the world

---

## Step 5: (Optional) Add a Custom Domain

### 5.1 Buy a domain (e.g., from Namecheap, GoDaddy)
Example: `footballtracker.com` (~$10-15/year)

### 5.2 Add DNS A Record
In your domain registrar:
- **Type**: A
- **Host**: `@` (or `www`)
- **Value**: `YOUR_STATIC_IP`
- **TTL**: 3600

### 5.3 Update Nginx config on VM
```bash
sudo nano /etc/nginx/sites-available/football-tracker
```

Change:
```nginx
server_name _;
```

To:
```nginx
server_name footballtracker.com www.footballtracker.com;
```

Restart Nginx:
```bash
sudo systemctl restart nginx
```

### 5.4 (Optional) Add SSL/HTTPS with Let's Encrypt
```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d footballtracker.com -d www.footballtracker.com
```

---

## Useful Commands

### View app logs
```bash
sudo journalctl -u football-tracker -f
```

### Restart the app
```bash
sudo systemctl restart football-tracker
```

### Update the app (after making changes)
```bash
cd ~/Football
git pull  # Or re-upload via SCP
sudo systemctl restart football-tracker
```

### Check app status
```bash
sudo systemctl status football-tracker
```

### Check Nginx status
```bash
sudo systemctl status nginx
```

---

## Cost Breakdown

| Service | Tier | Monthly Cost |
|---------|------|--------------|
| VM (B1s) | 1 vCPU, 1 GB RAM | ~$7.59 |
| Static Public IP | Standard | ~$3.65 |
| Azure PostgreSQL (B1ms) | 1 vCore, 2 GB RAM | ~$12.41 |
| **Total** | | **~$23.65/month** |

### Cheaper Option (VM-only PostgreSQL):
| Service | Monthly Cost |
|---------|--------------|
| VM (B1s) + Static IP | ~$11.24 |

---

## Troubleshooting

### App won't start
```bash
# Check logs
sudo journalctl -u football-tracker -n 50

# Check if port 9876 is in use
sudo lsof -i :9876

# Manually test the app
cd ~/Football
source venv/bin/activate
python3 app_flask.py
```

### Can't access from browser
```bash
# Check Nginx
sudo nginx -t
sudo systemctl status nginx

# Check firewall (should be open from Azure portal)
sudo ufw status
```

### Database connection issues
```bash
# Test PostgreSQL connection
psql -h YOUR_DB_HOST -U footballadmin -d postgres
```

---

## Security Notes

⚠️ **Important**: This is a basic deployment. For production, you should:
1. Set up a firewall (only allow your IP for SSH)
2. Use environment variables for secrets (not hardcoded passwords)
3. Enable HTTPS with SSL certificate
4. Set up automatic backups for the database
5. Add authentication to your Flask app

For now, this will work great for personal use! 🎯

