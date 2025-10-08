#!/bin/bash
#
# Run this script DIRECTLY ON THE VM (172.22.2.169) as itsystems user
# Sets up automated Jamf + Intune sync at 2:00 AM MST in /opt/
#

set -e

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║       Setup Automated MDM Sync on VM - 2:00 AM MST Schedule (/opt)        ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  This script should be run as itsystems user on the VM"
echo ""

# Check if running as itsystems
if [ "$USER" != "itsystems" ]; then
    echo "⚠️  Warning: Not running as itsystems user (current: $USER)"
    echo "   Continuing anyway..."
fi

# Set timezone to MST
echo "🕐 Setting timezone to MST (America/Denver)..."
sudo timedatectl set-timezone America/Denver
echo "✅ Timezone set to: $(timedatectl | grep 'Time zone' | awk '{print $3}')"
echo ""

# Setup Jamf Sync
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  1. SETTING UP JAMF SYNC"
echo "═══════════════════════════════════════════════════════════════════════════"

JAMF_DIR="/opt/jamf-snipe-sync"

# Create /opt directory if needed
sudo mkdir -p /opt

# Clone or pull repo
if [ -d "$JAMF_DIR" ]; then
    echo "📥 Updating Jamf sync repository..."
    cd $JAMF_DIR
    sudo git pull origin main
else
    echo "📥 Cloning Jamf sync repository..."
    sudo git clone https://github.com/dennis-mywic/jamf-snipe-sync.git $JAMF_DIR
    cd $JAMF_DIR
fi

# Set ownership
sudo chown -R itsystems:itsystems $JAMF_DIR

# Install dependencies
echo "📦 Installing Python dependencies..."
cd $JAMF_DIR
pip3 install -r requirements.txt --user --break-system-packages 2>/dev/null || pip3 install -r requirements.txt --user

# Make scripts executable
chmod +x *.py *.sh 2>/dev/null || true

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

INTUNE_DIR="/opt/intune-snipe-sync"

# Clone or pull repo
if [ -d "$INTUNE_DIR" ]; then
    echo "📥 Updating Intune sync repository..."
    cd $INTUNE_DIR
    sudo git pull origin main
else
    echo "📥 Cloning Intune sync repository..."
    sudo git clone https://github.com/dennis-mywic/intune-snipe-sync.git $INTUNE_DIR
    cd $INTUNE_DIR
fi

# Set ownership
sudo chown -R itsystems:itsystems $INTUNE_DIR

# Install dependencies
echo "📦 Installing Python dependencies..."
cd $INTUNE_DIR
pip3 install -r requirements.txt --user --break-system-packages 2>/dev/null || pip3 install -r requirements.txt --user

# Make scripts executable
chmod +x *.py 2>/dev/null || true

# Copy .env from jamf-snipe-sync if not exists
if [ ! -f ".env" ] && [ -f "$JAMF_DIR/.env" ]; then
    echo "🔐 Copying credentials from Jamf sync..."
    cp $JAMF_DIR/.env .
fi

# Create systemd directory if needed
mkdir -p systemd

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
sudo chown itsystems:itsystems /var/log/jamf-snipe-sync.log /var/log/intune-snipe-sync.log

# Show status
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                        ✅ SETUP COMPLETE!                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📂 Installation Locations:"
echo "  • Jamf sync:   /opt/jamf-snipe-sync"
echo "  • Intune sync: /opt/intune-snipe-sync"
echo ""
echo "⏰ Scheduled Syncs:"
echo "═══════════════════════════════════════════════════════════════════════════"
sudo systemctl list-timers jamf-snipe-ultimate-sync.timer intune-snipe-sync.timer --no-pager
echo ""

echo "📊 Timer Status:"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Jamf Sync:"
sudo systemctl status jamf-snipe-ultimate-sync.timer --no-pager | head -5
echo ""
echo "Intune Sync:"
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

