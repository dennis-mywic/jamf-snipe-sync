#!/bin/bash
#
# Run this script DIRECTLY ON THE VM (172.22.2.169)
# Sets up automated Jamf + Intune sync at 2:00 AM MST
#

set -e

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║          Setup Automated MDM Sync on VM - 2:00 AM MST Schedule            ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Set timezone to MST
echo "🕐 Setting timezone to MST (America/Denver)..."
sudo timedatectl set-timezone America/Denver
echo "✅ Timezone set to: $(timedatectl | grep 'Time zone' | awk '{print $3}')"
echo ""

# Setup Jamf Sync
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  1. SETTING UP JAMF SYNC"
echo "═══════════════════════════════════════════════════════════════════════════"

JAMF_DIR="/home/dennis/jamf-snipe-sync"

# Clone or pull repo
if [ -d "$JAMF_DIR" ]; then
    echo "📥 Updating Jamf sync repository..."
    cd $JAMF_DIR
    git pull origin main
else
    echo "📥 Cloning Jamf sync repository..."
    cd /home/dennis
    git clone https://github.com/dennis-mywic/jamf-snipe-sync.git
    cd jamf-snipe-sync
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt --user

# Make scripts executable
chmod +x *.py *.sh

# Copy systemd files
echo "⚙️  Installing systemd service..."
sudo cp systemd/jamf-snipe-ultimate-sync.service /etc/systemd/system/
sudo cp systemd/jamf-snipe-ultimate-sync.timer /etc/systemd/system/

# Enable timer
sudo systemctl daemon-reload
sudo systemctl enable jamf-snipe-ultimate-sync.timer
sudo systemctl start jamf-snipe-ultimate-sync.timer

echo "✅ Jamf sync installed - scheduled for 2:00 AM MST"
echo ""

# Setup Intune Sync
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  2. SETTING UP INTUNE SYNC"
echo "═══════════════════════════════════════════════════════════════════════════"

INTUNE_DIR="/home/dennis/intune-snipe-sync"

# Clone or pull repo
if [ -d "$INTUNE_DIR" ]; then
    echo "📥 Updating Intune sync repository..."
    cd $INTUNE_DIR
    git pull origin main
else
    echo "📥 Cloning Intune sync repository..."
    cd /home/dennis
    git clone https://github.com/dennis-mywic/intune-snipe-sync.git
    cd intune-snipe-sync
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt --user

# Make scripts executable
chmod +x *.py

# Copy .env from jamf-snipe-sync if not exists
if [ ! -f ".env" ] && [ -f "$JAMF_DIR/.env" ]; then
    echo "🔐 Copying credentials from Jamf sync..."
    cp $JAMF_DIR/.env .
fi

# Copy systemd files
echo "⚙️  Installing systemd service..."
sudo cp systemd/intune-snipe-sync.service /etc/systemd/system/
sudo cp systemd/intune-snipe-sync.timer /etc/systemd/system/

# Enable timer
sudo systemctl daemon-reload
sudo systemctl enable intune-snipe-sync.timer
sudo systemctl start intune-snipe-sync.timer

echo "✅ Intune sync installed - scheduled for 2:10 AM MST"
echo ""

# Setup log files
echo "📝 Creating log files..."
sudo touch /var/log/jamf-snipe-sync.log /var/log/intune-snipe-sync.log
sudo chown dennis:dennis /var/log/jamf-snipe-sync.log /var/log/intune-snipe-sync.log

# Show status
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                        ✅ SETUP COMPLETE!                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⏰ Scheduled Syncs:"
echo "═══════════════════════════════════════════════════════════════════════════"
sudo systemctl list-timers jamf-snipe-ultimate-sync.timer intune-snipe-sync.timer --no-pager
echo ""

echo "📊 Timer Status:"
echo "═══════════════════════════════════════════════════════════════════════════"
sudo systemctl status jamf-snipe-ultimate-sync.timer --no-pager | head -5
sudo systemctl status intune-snipe-sync.timer --no-pager | head -5
echo ""

echo "✅ Both syncs are now automated!"
echo ""
echo "Useful commands:"
echo "  # View logs"
echo "  sudo tail -f /var/log/jamf-snipe-sync.log"
echo "  sudo tail -f /var/log/intune-snipe-sync.log"
echo ""
echo "  # Manual test run"
echo "  sudo systemctl start jamf-snipe-ultimate-sync.service"
echo "  sudo systemctl start intune-snipe-sync.service"
echo ""
echo "  # Check status"
echo "  sudo systemctl status jamf-snipe-ultimate-sync.timer"
echo "  sudo systemctl status intune-snipe-sync.timer"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

