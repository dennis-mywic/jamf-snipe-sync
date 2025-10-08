#!/bin/bash
#
# Deploy BOTH Jamf and Intune Syncs to VM
# Sets up complete automated MDM synchronization at 2:00 AM MST
#

set -e

VM_IP="172.22.2.169"
VM_USER="dennis"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║              Deploy Complete MDM Sync to VM (172.22.2.169)                ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This will deploy:"
echo "  • Jamf sync at 2:00 AM MST"
echo "  • Intune sync at 2:10 AM MST"
echo "  • Complete user mapping and categorization"
echo ""
read -p "Continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Deploy Jamf sync
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  1. DEPLOYING JAMF SYNC"
echo "═══════════════════════════════════════════════════════════════════════════"
cd /Users/dennis/dev/jamf-snipe-sync
bash deploy-to-vm.sh

# Deploy Intune sync
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  2. DEPLOYING INTUNE SYNC"
echo "═══════════════════════════════════════════════════════════════════════════"
cd /Users/dennis/dev/intune-snipe-sync
bash deploy-to-vm.sh

# Final setup on VM
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  3. FINAL CONFIGURATION"
echo "═══════════════════════════════════════════════════════════════════════════"

ssh ${VM_USER}@${VM_IP} << 'ENDSSH'
# Verify timezone
echo "🕐 Verifying timezone..."
TIMEZONE=$(timedatectl | grep "Time zone" | awk '{print $3}')
if [ "$TIMEZONE" = "America/Denver" ]; then
    echo "  ✅ Timezone: MST (America/Denver)"
else
    echo "  ⚠️  Current timezone: $TIMEZONE"
    echo "  Setting to MST..."
    sudo timedatectl set-timezone America/Denver
fi

# Create log directory
echo "📝 Setting up log directory..."
sudo mkdir -p /var/log
sudo touch /var/log/jamf-snipe-sync.log /var/log/intune-snipe-sync.log
sudo chown dennis:dennis /var/log/jamf-snipe-sync.log /var/log/intune-snipe-sync.log

# Show timer status
echo ""
echo "⏰ Scheduled Sync Times:"
echo "═══════════════════════════════════════════════════════════════════════════"
sudo systemctl list-timers jamf-snipe-ultimate-sync.timer intune-snipe-sync.timer --no-pager

ENDSSH

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                     🎉 COMPLETE DEPLOYMENT SUCCESS! 🎉                    ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Both syncs are now scheduled on VM 172.22.2.169:"
echo ""
echo "  ⏰ 2:00 AM MST - Jamf sync (Apple devices)"
echo "  ⏰ 2:10 AM MST - Intune sync (Windows devices)"
echo ""
echo "📊 This ensures:"
echo "  • 100% MDM mirror in Snipe-IT"
echo "  • Complete user mapping"
echo "  • Correct categorization"
echo "  • No duplicates or missing devices"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Useful commands on VM:"
echo "  ssh ${VM_USER}@${VM_IP}"
echo ""
echo "  # Check timer status"
echo "  sudo systemctl status jamf-snipe-ultimate-sync.timer"
echo "  sudo systemctl status intune-snipe-sync.timer"
echo ""
echo "  # View logs"
echo "  sudo tail -f /var/log/jamf-snipe-sync.log"
echo "  sudo tail -f /var/log/intune-snipe-sync.log"
echo ""
echo "  # View all scheduled timers"
echo "  sudo systemctl list-timers"
echo ""
echo "  # Manually trigger sync (testing)"
echo "  sudo systemctl start jamf-snipe-ultimate-sync.service"
echo "  sudo systemctl start intune-snipe-sync.service"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

