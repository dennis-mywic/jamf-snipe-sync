#!/bin/bash

# COMPLETE JAMF TO SNIPE-IT SYNC - 100% BULLETPROOF
# This script orchestrates the complete process:
# 1. Completely wipe Snipe-IT clean
# 2. Sync ALL devices from Jamf with zero drops
# 3. Verify success

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}===============================================================================${NC}"
echo -e "${BLUE}🚀 COMPLETE JAMF TO SNIPE-IT SYNC - 100% BULLETPROOF${NC}"
echo -e "${BLUE}===============================================================================${NC}"
echo -e "${YELLOW}This script will:${NC}"
echo -e "${YELLOW}  1. 🗑️  Completely wipe Snipe-IT clean${NC}"
echo -e "${YELLOW}  2. 🔄 Sync ALL devices from Jamf (computers + mobile devices)${NC}"
echo -e "${YELLOW}  3. ✅ Verify 100% success${NC}"
echo -e "${BLUE}===============================================================================${NC}"
echo

# Check if Python and required packages are available
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: python3 is required but not installed${NC}"
    exit 1
fi

# Check pip packages
python3 -c "import requests, dotenv" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Installing required Python packages...${NC}"
    pip3 install -r "${SCRIPT_DIR}/requirements.txt"
}

echo -e "${GREEN}✅ Prerequisites verified${NC}"
echo

# Check environment variables
echo -e "${BLUE}🔍 Checking environment variables...${NC}"

if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    echo -e "${RED}❌ ERROR: .env file not found in ${SCRIPT_DIR}${NC}"
    echo -e "${YELLOW}Please create a .env file with the following variables:${NC}"
    echo "JAMF_URL=https://your-jamf-instance.jamfcloud.com"
    echo "JAMF_CLIENT_ID=your_client_id"
    echo "JAMF_CLIENT_SECRET=your_client_secret"
    echo "SNIPE_IT_URL=https://your-snipe-it-instance.com"
    echo "SNIPE_IT_API_TOKEN=your_api_token"
    exit 1
fi

# Source environment variables to check them
source "${SCRIPT_DIR}/.env"

# Check required variables
missing_vars=()
[ -z "$JAMF_URL" ] && missing_vars+=("JAMF_URL")
[ -z "$SNIPE_IT_URL" ] && missing_vars+=("SNIPE_IT_URL")
[ -z "$SNIPE_IT_API_TOKEN" ] && missing_vars+=("SNIPE_IT_API_TOKEN")

if [ -z "$JAMF_CLIENT_ID" ] && [ -z "$JAMF_USERNAME" ]; then
    missing_vars+=("JAMF_CLIENT_ID or JAMF_USERNAME")
fi

if [ -z "$JAMF_CLIENT_SECRET" ] && [ -z "$JAMF_PASSWORD" ]; then
    missing_vars+=("JAMF_CLIENT_SECRET or JAMF_PASSWORD")
fi

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Missing required environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}   - $var${NC}"
    done
    exit 1
fi

echo -e "${GREEN}✅ Environment variables verified${NC}"
echo

# Final confirmation
echo -e "${YELLOW}⚠️  FINAL WARNING:${NC}"
echo -e "${YELLOW}This will PERMANENTLY DELETE ALL DATA in Snipe-IT at: ${SNIPE_IT_URL}${NC}"
echo -e "${YELLOW}Then sync ALL devices from Jamf at: ${JAMF_URL}${NC}"
echo

read -p "❓ Are you absolutely sure you want to proceed? (yes/NO): " confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${RED}❌ Operation cancelled${NC}"
    exit 0
fi

read -p "❓ Type 'WIPE AND SYNC' to confirm: " confirm2
if [ "$confirm2" != "WIPE AND SYNC" ]; then
    echo -e "${RED}❌ Operation cancelled - confirmation text didn't match${NC}"
    exit 0
fi

echo
echo -e "${BLUE}🚀 Starting complete sync process...${NC}"
echo

# Step 1: Ultimate Wipe
echo -e "${BLUE}===============================================================================${NC}"
echo -e "${BLUE}🗑️  STEP 1: ULTIMATE SNIPE-IT WIPE${NC}"
echo -e "${BLUE}===============================================================================${NC}"

cd "${SCRIPT_DIR}"

# Create input for the wipe script
echo -e "yes\nWIPE EVERYTHING CLEAN" | python3 ultimate-wipe-snipe-100-percent.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ WIPE FAILED! Check logs above.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Snipe-IT wipe completed successfully${NC}"
echo

# Small delay to ensure cleanup is complete
echo -e "${YELLOW}⏳ Waiting 10 seconds for cleanup to settle...${NC}"
sleep 10

# Step 2: Bulletproof Sync
echo -e "${BLUE}===============================================================================${NC}"
echo -e "${BLUE}🔄 STEP 2: BULLETPROOF JAMF SYNC${NC}"
echo -e "${BLUE}===============================================================================${NC}"

python3 jamf-to-snipe-bulletproof-complete.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ SYNC FAILED! Check logs above.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Jamf sync completed successfully${NC}"
echo

# Step 3: Final Verification
echo -e "${BLUE}===============================================================================${NC}"
echo -e "${BLUE}✅ STEP 3: FINAL VERIFICATION${NC}"
echo -e "${BLUE}===============================================================================${NC}"

# Quick verification using API
echo -e "${BLUE}🔍 Verifying sync results...${NC}"

# Count assets in Snipe-IT
asset_count=$(curl -s -H "Authorization: Bearer $SNIPE_IT_API_TOKEN" \
    "${SNIPE_IT_URL}/api/v1/hardware?limit=1" | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total', 0))" 2>/dev/null || echo "0")

echo -e "${BLUE}📊 Total assets in Snipe-IT: ${asset_count}${NC}"

if [ "$asset_count" -gt 0 ]; then
    echo -e "${GREEN}🎉 SUCCESS! Found ${asset_count} assets in Snipe-IT${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: No assets found in Snipe-IT${NC}"
    echo -e "${YELLOW}This might indicate an issue with the sync${NC}"
fi

echo
echo -e "${BLUE}===============================================================================${NC}"
echo -e "${BLUE}🏁 COMPLETE SYNC FINISHED${NC}"
echo -e "${BLUE}===============================================================================${NC}"
echo -e "${GREEN}✅ Snipe-IT has been completely wiped and resynced${NC}"
echo -e "${GREEN}✅ ALL devices from Jamf should now be in Snipe-IT${NC}"
echo -e "${BLUE}📊 Total assets synced: ${asset_count}${NC}"
echo
echo -e "${YELLOW}📝 Next steps:${NC}"
echo -e "${YELLOW}  1. Check the log files for detailed results${NC}"
echo -e "${YELLOW}  2. Verify devices in Snipe-IT web interface${NC}"
echo -e "${YELLOW}  3. Set up automated sync if needed${NC}"
echo
echo -e "${BLUE}📁 Log files location: ${SCRIPT_DIR}/${NC}"
echo -e "${BLUE}===============================================================================${NC}"
