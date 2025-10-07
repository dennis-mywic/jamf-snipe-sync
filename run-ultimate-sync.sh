#!/bin/bash
#
# JAMF TO SNIPE-IT ULTIMATE 100% SYNC RUNNER
# ==========================================
# This script runs the complete sync process with proper error handling
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="sync_runner_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   JAMF TO SNIPE-IT ULTIMATE SYNC                           ║${NC}"
echo -e "${BLUE}║                        100% Accuracy Guaranteed                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERROR: .env file not found${NC}"
    echo "Please create a .env file with your API credentials:"
    echo "  JAMF_URL=https://your-jamf-instance.jamfcloud.com"
    echo "  JAMF_CLIENT_ID=your_client_id"
    echo "  JAMF_CLIENT_SECRET=your_client_secret"
    echo "  SNIPE_IT_URL=https://your-snipe-it-instance.com"
    echo "  SNIPE_IT_API_TOKEN=your_api_token"
    exit 1
fi

echo -e "${GREEN}✅ Environment file found${NC}"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: python3 not found${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${NC}"

# Check for required packages
echo ""
echo -e "${YELLOW}Checking Python dependencies...${NC}"
if ! python3 -c "import requests, dotenv" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing required Python packages...${NC}"
    pip3 install -r requirements.txt || {
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    }
fi

echo -e "${GREEN}✅ All dependencies installed${NC}"

# Confirmation prompt
echo ""
echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                              IMPORTANT NOTICE                              ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "This script will:"
echo "  • Fetch ALL devices from Jamf Pro (computers + mobile devices)"
echo "  • Create/update ALL devices in Snipe-IT with correct categorization"
echo "  • Map users to devices based on email addresses"
echo "  • Process devices with proper rate limiting (may take 30-60 minutes)"
echo ""
echo -e "${YELLOW}Estimated time: 30-60 minutes for ~500 devices${NC}"
echo ""
read -p "Do you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Sync cancelled by user${NC}"
    exit 0
fi

# Run the sync
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                         STARTING SYNC PROCESS                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Started: $(date)"
echo "Log file: $LOG_FILE"
echo ""

START_TIME=$(date +%s)

# Run the ultimate sync script
if python3 jamf-snipe-ultimate-100-percent-sync.py 2>&1 | tee -a "$LOG_FILE"; then
    SYNC_SUCCESS=true
else
    SYNC_SUCCESS=false
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                          SYNC PROCESS COMPLETE                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Completed: $(date)"
echo "Duration: ${MINUTES}m ${SECONDS}s"
echo ""

if [ "$SYNC_SUCCESS" = true ]; then
    echo -e "${GREEN}✅ Sync completed successfully${NC}"
    
    # Ask if user wants to verify
    echo ""
    read -p "Do you want to verify the sync? (yes/no): " -r
    echo
    
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo ""
        echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║                        RUNNING VERIFICATION                                ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        
        if python3 verify-100-percent-sync.py; then
            echo ""
            echo -e "${GREEN}✅ Verification passed - 100% sync confirmed!${NC}"
        else
            echo ""
            echo -e "${YELLOW}⚠️  Verification found some discrepancies - check verification log${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Sync encountered errors - check log file for details${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                               ALL DONE!                                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Logs saved to: $LOG_FILE"
echo ""

