#!/bin/bash
#
# Deploy Jamf-Snipe Sync to VM at 172.22.2.169
# Schedules daily sync at 2:00 AM MST
#

set -e

VM_IP="172.22.2.169"
VM_USER="dennis"
REMOTE_DIR="/home/dennis/jamf-snipe-sync"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║         Deploying Jamf-Snipe Ultimate Sync to VM (172.22.2.169)           ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Create remote directory
echo "📁 Creating remote directory..."
ssh ${VM_USER}@${VM_IP} "mkdir -p ${REMOTE_DIR}"

# Copy files
echo "📤 Copying sync files..."
scp jamf-snipe-ultimate-100-percent-sync.py ${VM_USER}@${VM_IP}:${REMOTE_DIR}/
scp verify-100-percent-sync.py ${VM_USER}@${VM_IP}:${REMOTE_DIR}/
scp cleanup-and-sync-100-percent.py ${VM_USER}@${VM_IP}:${REMOTE_DIR}/
scp test-connection.py ${VM_USER}@${VM_IP}:${REMOTE_DIR}/
scp requirements.txt ${VM_USER}@${VM_IP}:${REMOTE_DIR}/
scp .env ${VM_USER}@${VM_IP}:${REMOTE_DIR}/

# Copy documentation
echo "📄 Copying documentation..."
scp README-ULTIMATE-SYNC.md ${VM_USER}@${VM_IP}:${REMOTE_DIR}/
scp QUICK-START-GUIDE.md ${VM_USER}@${VM_IP}:${REMOTE_DIR}/
scp COMMANDS.txt ${VM_USER}@${VM_IP}:${REMOTE_DIR}/

# Copy systemd files
echo "⚙️  Copying systemd configuration..."
scp systemd/jamf-snipe-ultimate-sync.service ${VM_USER}@${VM_IP}:/tmp/
scp systemd/jamf-snipe-ultimate-sync.timer ${VM_USER}@${VM_IP}:/tmp/

# Install on VM
echo "🔧 Installing on VM..."
ssh ${VM_USER}@${VM_IP} << 'ENDSSH'
set -e

# Set timezone to MST
echo "🕐 Setting timezone to MST..."
sudo timedatectl set-timezone America/Denver

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd /home/dennis/jamf-snipe-sync
pip3 install -r requirements.txt --user

# Make scripts executable
chmod +x *.py

# Install systemd files
echo "⚙️  Installing systemd service and timer..."
sudo cp /tmp/jamf-snipe-ultimate-sync.service /etc/systemd/system/
sudo cp /tmp/jamf-snipe-ultimate-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start timer
echo "▶️  Enabling daily sync at 2:00 AM MST..."
sudo systemctl enable jamf-snipe-ultimate-sync.timer
sudo systemctl start jamf-snipe-ultimate-sync.timer

# Check status
echo ""
echo "✅ Installation complete!"
echo ""
echo "Timer status:"
sudo systemctl status jamf-snipe-ultimate-sync.timer --no-pager

echo ""
echo "Next scheduled run:"
sudo systemctl list-timers jamf-snipe-ultimate-sync.timer --no-pager

ENDSSH

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                          ✅ DEPLOYMENT COMPLETE                            ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Jamf sync is now scheduled to run daily at 2:00 AM MST on 172.22.2.169"
echo ""
echo "To check status on VM:"
echo "  ssh ${VM_USER}@${VM_IP}"
echo "  sudo systemctl status jamf-snipe-ultimate-sync.timer"
echo "  sudo journalctl -u jamf-snipe-ultimate-sync.service -f"
echo ""

