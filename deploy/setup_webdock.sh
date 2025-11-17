#!/bin/bash
# Roblox DataStore Manager - Webdock Setup Script
# Run this as root on your Webdock server

set -e

echo "============================================================"
echo "  Roblox DataStore Manager - Webdock Setup"
echo "============================================================"
echo ""

# Variables
APP_DIR="/var/www/datastore-manager"
LOG_DIR="/var/log/datastore-manager"
REPO_URL="https://github.com/tigodev1/TestingClaude.git"
BRANCH="claude/clear-repository-0177eXnJsBBHznA5s3yUtAmk"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (sudo)"
    exit 1
fi

# Step 1: Install system dependencies
echo ""
echo "Step 1: Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-dev \
    libmysqlclient-dev gcc git nginx

print_status "System dependencies installed"

# Step 2: Create application directory
echo ""
echo "Step 2: Setting up application directory..."
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"

# Clone or update repository
if [ -d "$APP_DIR/.git" ]; then
    print_warning "Repository exists, pulling latest..."
    cd "$APP_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    print_status "Cloning repository..."
    git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

print_status "Application directory ready"

# Step 3: Setup Python environment
echo ""
echo "Step 3: Setting up Python environment..."
cd "$APP_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-production.txt

print_status "Python environment configured"

# Step 4: Setup database
echo ""
echo "Step 4: Setting up database..."
mysql -u admin -petNvTppbndsP << EOF
CREATE DATABASE IF NOT EXISTS sheetsdigita CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON sheetsdigita.* TO 'sheetsdigita'@'localhost';
FLUSH PRIVILEGES;
EOF

print_status "Database configured"

# Step 5: Configure environment variables
echo ""
echo "Step 5: Configuring environment..."

# Generate random keys
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > "$APP_DIR/.env" << EOF
FLASK_ENV=production
FLASK_APP=wsgi.py
DATABASE_URL=mysql+pymysql://sheetsdigita:Y2dBbLW7xrSn@localhost/sheetsdigita
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
SERVER_NAME=tigoshub.com
PREFERRED_URL_SCHEME=https
LOG_TO_STDOUT=False
EOF

print_status "Environment variables configured"

# Step 6: Initialize database tables
echo ""
echo "Step 6: Initializing database..."
cd "$APP_DIR"
source venv/bin/activate

python3 << EOF
from app_production import create_app
from src.models import db

app = create_app('production')
with app.app_context():
    db.create_all()
    print("Database tables created successfully")
EOF

print_status "Database initialized"

# Step 7: Set permissions
echo ""
echo "Step 7: Setting permissions..."
chown -R www-data:www-data "$APP_DIR"
chown -R www-data:www-data "$LOG_DIR"
chmod -R 755 "$APP_DIR"
chmod 600 "$APP_DIR/.env"

# Create necessary directories
mkdir -p "$APP_DIR/data"
mkdir -p "$APP_DIR/backups"
chown www-data:www-data "$APP_DIR/data"
chown www-data:www-data "$APP_DIR/backups"

print_status "Permissions set"

# Step 8: Configure Nginx
echo ""
echo "Step 8: Configuring Nginx..."
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/datastore-manager

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -sf /etc/nginx/sites-available/datastore-manager /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

print_status "Nginx configured"

# Step 9: Setup systemd service
echo ""
echo "Step 9: Setting up systemd service..."
cp "$APP_DIR/deploy/datastore-manager.service" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start service
systemctl enable datastore-manager
systemctl start datastore-manager

print_status "Service configured and started"

# Step 10: Restart Nginx
echo ""
echo "Step 10: Restarting Nginx..."
systemctl restart nginx

print_status "Nginx restarted"

# Final checks
echo ""
echo "============================================================"
echo "  SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "Your Roblox DataStore Manager is now running at:"
echo "  http://tigoshub.com"
echo "  http://92.113.151.63"
echo ""
echo "Service Management:"
echo "  Check status: systemctl status datastore-manager"
echo "  View logs: journalctl -u datastore-manager -f"
echo "  Restart: systemctl restart datastore-manager"
echo ""
echo "Log files:"
echo "  Application: $LOG_DIR/error.log"
echo "  Access: $LOG_DIR/access.log"
echo "  Nginx: /var/log/nginx/datastore-manager.*.log"
echo ""

# Check if service is running
if systemctl is-active --quiet datastore-manager; then
    print_status "Service is running"
else
    print_error "Service failed to start. Check: journalctl -u datastore-manager"
fi

echo ""
echo "NEXT STEPS:"
echo "1. Visit http://tigoshub.com to access the dashboard"
echo "2. Configure your Roblox API key in Settings"
echo "3. Set up SSL with: certbot --nginx -d tigoshub.com"
echo ""
echo "For SSL setup, run:"
echo "  apt-get install certbot python3-certbot-nginx"
echo "  certbot --nginx -d tigoshub.com -d www.tigoshub.com"
echo ""
