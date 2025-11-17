# Deploying to Webdock - Step by Step Guide

## Your Server Details
- **Domain**: tigoshub.com
- **IP**: 92.113.151.63
- **SSH User**: admin
- **SSH Password**: NNJHfXUnVJTK
- **MySQL Database**: sheetsdigita
- **MySQL User**: sheetsdigita
- **MySQL Password**: Y2dBbLW7xrSn

---

## Quick Deployment (Automated)

### Step 1: Connect to Your Server via SSH

```bash
ssh admin@92.113.151.63
# Enter password: NNJHfXUnVJTK
```

### Step 2: Switch to Root

```bash
sudo -i
# Enter password: NNJHfXUnVJTK
```

### Step 3: Download and Run Setup Script

```bash
# Create deployment directory
mkdir -p /tmp/deploy
cd /tmp/deploy

# Download the setup script
wget https://raw.githubusercontent.com/tigodev1/TestingClaude/claude/clear-repository-0177eXnJsBBHznA5s3yUtAmk/deploy/setup_webdock.sh

# Make it executable
chmod +x setup_webdock.sh

# Run it
./setup_webdock.sh
```

The script will:
1. Install all dependencies (Python, pip, etc.)
2. Clone your application
3. Set up the virtual environment
4. Configure MySQL database
5. Set up Nginx as reverse proxy
6. Create systemd service for auto-start
7. Start everything

### Step 4: Access Your Application

Open your browser and go to:
- http://tigoshub.com
- OR http://92.113.151.63

---

## Manual Deployment (Alternative)

If you prefer manual setup:

### 1. SSH into your server
```bash
ssh admin@92.113.151.63
sudo -i
```

### 2. Install dependencies
```bash
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-dev libmysqlclient-dev gcc git nginx
```

### 3. Clone repository
```bash
mkdir -p /var/www/datastore-manager
cd /var/www/datastore-manager
git clone -b claude/clear-repository-0177eXnJsBBHznA5s3yUtAmk https://github.com/tigodev1/TestingClaude.git .
```

### 4. Setup Python environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-production.txt
```

### 5. Configure environment
```bash
# Create .env file
cat > .env << 'EOF'
FLASK_ENV=production
FLASK_APP=wsgi.py
DATABASE_URL=mysql+pymysql://sheetsdigita:Y2dBbLW7xrSn@localhost/sheetsdigita
SECRET_KEY=your-random-secret-key-here
ENCRYPTION_KEY=your-random-encryption-key-here
EOF
```

### 6. Initialize database
```bash
python3 -c "
from app_production import create_app
from src.models import db
app = create_app('production')
with app.app_context():
    db.create_all()
"
```

### 7. Set permissions
```bash
chown -R www-data:www-data /var/www/datastore-manager
mkdir -p /var/log/datastore-manager
chown www-data:www-data /var/log/datastore-manager
```

### 8. Configure Nginx
```bash
cp deploy/nginx.conf /etc/nginx/sites-available/datastore-manager
ln -sf /etc/nginx/sites-available/datastore-manager /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
```

### 9. Setup systemd service
```bash
cp deploy/datastore-manager.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable datastore-manager
systemctl start datastore-manager
```

### 10. Restart Nginx
```bash
systemctl restart nginx
```

---

## Post-Deployment Setup

### Enable HTTPS (SSL/TLS)

```bash
# Install Certbot
apt-get install -y certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d tigoshub.com -d www.tigoshub.com

# Follow the prompts
# Choose to redirect HTTP to HTTPS when asked
```

After this, your site will be accessible at https://tigoshub.com

### Configure Roblox API

1. Go to https://tigoshub.com
2. Click on "Settings" in the sidebar
3. Enter your Roblox Open Cloud API Key
4. Enter your Universe ID
5. Click "Save Configuration"
6. Click "Test Connection" to verify

---

## Service Management

### Check Status
```bash
systemctl status datastore-manager
```

### View Logs
```bash
# Application logs
journalctl -u datastore-manager -f

# Or directly
tail -f /var/log/datastore-manager/error.log
tail -f /var/log/datastore-manager/access.log

# Nginx logs
tail -f /var/log/nginx/datastore-manager.error.log
```

### Restart Service
```bash
systemctl restart datastore-manager
```

### Stop Service
```bash
systemctl stop datastore-manager
```

### Update Application
```bash
cd /var/www/datastore-manager
git pull origin claude/clear-repository-0177eXnJsBBHznA5s3yUtAmk
source venv/bin/activate
pip install -r requirements-production.txt
systemctl restart datastore-manager
```

---

## Troubleshooting

### Service won't start
```bash
# Check logs
journalctl -u datastore-manager -n 100 --no-pager

# Common issues:
# - Wrong permissions: chown -R www-data:www-data /var/www/datastore-manager
# - Missing dependencies: source venv/bin/activate && pip install -r requirements-production.txt
# - Database connection: mysql -u sheetsdigita -pY2dBbLW7xrSn -D sheetsdigita
```

### 502 Bad Gateway
```bash
# Check if app is running
systemctl status datastore-manager

# Check if port is in use
ss -tulpn | grep 8000

# Restart everything
systemctl restart datastore-manager
systemctl restart nginx
```

### Database errors
```bash
# Check MySQL is running
systemctl status mysql

# Test connection
mysql -u sheetsdigita -pY2dBbLW7xrSn -D sheetsdigita -e "SHOW TABLES;"

# Recreate tables
cd /var/www/datastore-manager
source venv/bin/activate
python3 -c "
from app_production import create_app
from src.models import db
app = create_app('production')
with app.app_context():
    db.drop_all()
    db.create_all()
"
```

### Permission denied
```bash
chown -R www-data:www-data /var/www/datastore-manager
chmod -R 755 /var/www/datastore-manager
chmod 600 /var/www/datastore-manager/.env
```

---

## Security Recommendations

1. **Change default passwords** after setup
2. **Enable firewall**:
   ```bash
   ufw allow 22
   ufw allow 80
   ufw allow 443
   ufw enable
   ```
3. **Set up fail2ban** for SSH protection
4. **Regular backups** of /var/www/datastore-manager/backups/
5. **Monitor logs** for suspicious activity

---

## Features Available

Once deployed, you'll have access to:

- **Dashboard** - Overview of operations and quick stats
- **DataStores** - Browse all datastores in your game
- **Explorer** - View, edit, and delete entries
- **Bulk Operations** - Export/import entire datastores
- **Analytics** - Charts showing operation patterns and errors
- **Backups** - Automatic backup history
- **History** - Complete audit log of all operations
- **Settings** - Configure API credentials

---

## Need Help?

- Check the logs first: `journalctl -u datastore-manager -f`
- Restart services: `systemctl restart datastore-manager nginx`
- Visit the GitHub repository for updates

Your application should now be live at **https://tigoshub.com**!
