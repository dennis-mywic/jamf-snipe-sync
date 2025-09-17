#!/bin/bash

# JAMF TO SNIPE-IT BULLETPROOF SYNC - PRODUCTION DEPLOYMENT
# This script deploys the bulletproof sync to your production VM

set -e

echo "🚀 DEPLOYING JAMF TO SNIPE-IT BULLETPROOF SYNC TO PRODUCTION"
echo "============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/jamf-snipe-sync"
SERVICE_NAME="jamf-snipe-sync-production"

echo -e "${BLUE}📋 This script will:${NC}"
echo -e "${BLUE}  1. Install bulletproof sync to ${INSTALL_DIR}${NC}"
echo -e "${BLUE}  2. Set up systemd service and timer${NC}"
echo -e "${BLUE}  3. Schedule automatic runs at 2AM Mountain Time${NC}"
echo -e "${BLUE}  4. Install Python dependencies${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Step 1: Create installation directory
echo -e "${YELLOW}📁 Creating installation directory...${NC}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Step 2: Clone/update repository
echo -e "${YELLOW}📥 Downloading latest bulletproof sync...${NC}"
if [ -d ".git" ]; then
    echo "   🔄 Updating existing repository..."
    git fetch origin
    git reset --hard origin/main
else
    echo "   📦 Cloning repository..."
    git clone https://github.com/dennis-mywic/jamf-snipe-sync.git .
fi

# Step 3: Install Python dependencies
echo -e "${YELLOW}🐍 Installing Python dependencies...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Installing...${NC}"
    apt update
    apt install -y python3 python3-pip python3-venv
fi

# Create virtual environment
echo "   📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Make scripts executable
echo -e "${YELLOW}🔧 Setting up executable permissions...${NC}"
chmod +x run-complete-jamf-sync.sh
chmod +x jamf-to-snipe-bulletproof-complete.py
chmod +x ultimate-wipe-snipe-100-percent.py

# Step 5: Install systemd service and timer
echo -e "${YELLOW}⚙️  Installing systemd service and timer...${NC}"
cp systemd/jamf-snipe-sync-production.service /etc/systemd/system/
cp systemd/jamf-snipe-sync-production.timer /etc/systemd/system/

# Step 6: Enable and start the timer
echo -e "${YELLOW}🕐 Setting up automatic scheduling (2AM Mountain Time)...${NC}"
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}.timer
systemctl start ${SERVICE_NAME}.timer

# Step 7: Verify setup
echo -e "${YELLOW}✅ Verifying installation...${NC}"
systemctl status ${SERVICE_NAME}.timer --no-pager

echo
echo -e "${GREEN}🎉 PRODUCTION DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}==============================================${NC}"
echo
echo -e "${BLUE}📊 Service Status:${NC}"
systemctl list-timers ${SERVICE_NAME}.timer --no-pager
echo
echo -e "${BLUE}📋 Next Steps:${NC}"
echo -e "${BLUE}  1. Create .env file with your API credentials:${NC}"
echo -e "${BLUE}     sudo nano ${INSTALL_DIR}/.env${NC}"
echo
echo -e "${BLUE}  2. Add your Snipe-IT API key:${NC}"
echo -e "${BLUE}     sudo nano ${INSTALL_DIR}/snipe_api_key.txt${NC}"
echo
echo -e "${BLUE}  3. Test the sync manually:${NC}"
echo -e "${BLUE}     cd ${INSTALL_DIR} && sudo ./run-complete-jamf-sync.sh${NC}"
echo
echo -e "${BLUE}  4. Check logs:${NC}"
echo -e "${BLUE}     sudo journalctl -u ${SERVICE_NAME}.service -f${NC}"
echo
echo -e "${YELLOW}⏰ Automatic Sync Schedule: Daily at 2AM Mountain Time${NC}"
echo -e "${YELLOW}🔧 Service Management:${NC}"
echo -e "${YELLOW}   Start:   sudo systemctl start ${SERVICE_NAME}.timer${NC}"
echo -e "${YELLOW}   Stop:    sudo systemctl stop ${SERVICE_NAME}.timer${NC}"
echo -e "${YELLOW}   Status:  sudo systemctl status ${SERVICE_NAME}.timer${NC}"
echo -e "${YELLOW}   Logs:    sudo journalctl -u ${SERVICE_NAME}.service${NC}"
echo
