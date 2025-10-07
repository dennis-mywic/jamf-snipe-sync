# 🚀 Quick Start Guide - Jamf to Snipe-IT Ultimate Sync

## 📋 Pre-Flight Checklist

- [ ] Python 3.8+ installed
- [ ] `.env` file created with API credentials
- [ ] Network access to both Jamf Pro and Snipe-IT
- [ ] API credentials tested and working
- [ ] 30-60 minutes available for sync to complete

## ⚡ Quick Setup (5 Minutes)

### 1. Navigate to Directory
```bash
cd /Users/dennis/dev/jamf-snipe-sync
```

### 2. Create Environment File

Create `.env` file:
```bash
cat > .env << 'EOF'
JAMF_URL=https://your-jamf-instance.jamfcloud.com
JAMF_CLIENT_ID=your_client_id
JAMF_CLIENT_SECRET=your_client_secret
SNIPE_IT_URL=https://your-snipe-it-instance.com
SNIPE_IT_API_TOKEN=your_api_token
EOF
```

**⚠️ Important**: Replace the placeholder values with your actual credentials!

### 3. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Test Connection (Optional but Recommended)
```bash
# Test Jamf connection
python3 -c "
from dotenv import load_dotenv
import os, requests
load_dotenv()
r = requests.post(f'{os.getenv(\"JAMF_URL\")}/api/oauth/token',
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    data={'client_id': os.getenv('JAMF_CLIENT_ID'), 
          'grant_type': 'client_credentials',
          'client_secret': os.getenv('JAMF_CLIENT_SECRET')})
print('✅ Jamf connection OK' if r.status_code == 200 else f'❌ Jamf error: {r.status_code}')
"

# Test Snipe-IT connection
python3 -c "
from dotenv import load_dotenv
import os, requests
load_dotenv()
r = requests.get(f'{os.getenv(\"SNIPE_IT_URL\")}/api/v1/hardware?limit=1',
    headers={'Authorization': f'Bearer {os.getenv(\"SNIPE_IT_API_TOKEN\")}'})
print('✅ Snipe-IT connection OK' if r.status_code == 200 else f'❌ Snipe-IT error: {r.status_code}')
"
```

## 🎯 Run the Sync (One Command)

```bash
./run-ultimate-sync.sh
```

That's it! The script will:
1. ✅ Validate your environment
2. ✅ Fetch ALL devices from Jamf
3. ✅ Sync to Snipe-IT with correct categories
4. ✅ Map users automatically
5. ✅ Verify 100% completion

## 📊 What to Expect

### Timeline
```
[0:00-0:02]  Authentication & Setup
[0:02-0:10]  Fetching devices from Jamf Pro
[0:10-0:45]  Syncing devices to Snipe-IT
[0:45-0:50]  Verification (optional)
[0:50-0:55]  Final reports
```

### Console Output
```
🚀 JAMF TO SNIPE-IT ULTIMATE 100% SYNC
══════════════════════════════════════
Started: 2025-10-07 14:30:00

✅ Environment variables validated
🔐 Authenticating with Jamf Pro...
✅ Successfully obtained Jamf access token

📥 FETCHING DEVICES FROM JAMF PRO
══════════════════════════════════════
📥 Fetching all computers from Jamf Pro...
  📄 Page 0: Retrieved 200 computers (Total: 200)
  📄 Page 1: Retrieved 125 computers (Total: 325)
✅ Retrieved 325 total computers

📥 Fetching all mobile devices from Jamf Pro...
  📄 Page 0: Retrieved 162 mobile devices (Total: 162)
✅ Retrieved 162 total mobile devices

🔍 GATHERING DEVICE DETAILS
══════════════════════════════════════
  [1/325] Computer: C02ABC123DEF
  [2/325] Computer: C02ABC456GHI
  ...

🔄 SYNCING DEVICES TO SNIPE-IT
══════════════════════════════════════
Processing Batch 1/5 (Devices 1-100 of 487)
══════════════════════════════════════
[1/487] Processing: C02ABC123DEF
  PRESTAGE: 'Staff Setup' → Staff
✅ Updated: C02ABC123DEF → Staff Mac Laptop
  👤 Checked out to: john.doe@example.com

[2/487] Processing: C02ABC456GHI
  PRESTAGE: 'Student Setup' → Student
✅ Created: C02ABC456GHI → Student Loaner Laptop
  ...
```

## ✅ Success Indicators

Look for these in the output:

```
🎉 ══════════════════════════════════════════════════════════ 🎉
🎉                      100% SUCCESS!                         🎉
🎉              ALL DEVICES SYNCED SUCCESSFULLY!              🎉
🎉 ══════════════════════════════════════════════════════════ 🎉
```

## 📝 Log Files

After completion, you'll have:

```
jamf_snipe_ultimate_sync_20251007_143000.log  # Detailed sync log
sync_runner_20251007_143000.log               # Runner script log
verification_20251007_150000.log              # Verification log (if run)
```

## 🔍 Verify the Sync

After sync completes, verify 100% accuracy:

```bash
python3 verify-100-percent-sync.py
```

Expected output:
```
Sync Accuracy: 100.00%

🎉 ══════════════════════════════════════════════════════════ 🎉
🎉                   100% SYNC VERIFIED!                      🎉
🎉           ALL DEVICES PRESENT IN SNIPE-IT!                 🎉
🎉 ══════════════════════════════════════════════════════════ 🎉
```

## 🚨 Common Issues & Quick Fixes

### Issue: "Command 'python3' not found"
```bash
# Install Python 3
# macOS:
brew install python3
# or use the macOS installer from python.org
```

### Issue: ".env file not found"
```bash
# Create .env file (see step 2 above)
# Make sure you're in the correct directory
pwd  # Should show: /Users/dennis/dev/jamf-snipe-sync
```

### Issue: "Failed to get Jamf token"
```bash
# Check your Jamf credentials in .env
# Test manually:
curl -X POST "https://your-jamf.jamfcloud.com/api/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "grant_type=client_credentials" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

### Issue: "Rate limited" or "429 errors"
```bash
# The script handles this automatically with retries
# If persistent, increase RATE_LIMIT_DELAY in the script
# Edit: jamf-snipe-ultimate-100-percent-sync.py
# Change: RATE_LIMIT_DELAY = 2.0  (from 1.5)
```

### Issue: "Sync takes too long"
```bash
# This is normal for large device counts
# 500 devices ≈ 45-60 minutes
# The script is designed for reliability over speed
# You can run it in the background:
nohup ./run-ultimate-sync.sh > sync.log 2>&1 &
```

## 🔄 Regular Sync Schedule

For ongoing use, schedule daily sync:

### Using Cron
```bash
# Edit crontab
crontab -e

# Add this line (runs at 2 AM daily)
0 2 * * * cd /Users/dennis/dev/jamf-snipe-sync && /usr/bin/python3 jamf-snipe-ultimate-100-percent-sync.py >> /var/log/jamf-sync.log 2>&1
```

### Using launchd (macOS)
```bash
# Create launch agent
cat > ~/Library/LaunchAgents/com.wic.jamf-sync.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wic.jamf-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/dennis/dev/jamf-snipe-sync/jamf-snipe-ultimate-100-percent-sync.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/var/log/jamf-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/jamf-sync.error.log</string>
</dict>
</plist>
EOF

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.wic.jamf-sync.plist
```

## 📚 Additional Resources

- **Full Documentation**: [README-ULTIMATE-SYNC.md](README-ULTIMATE-SYNC.md)
- **Main Script**: `jamf-snipe-ultimate-100-percent-sync.py`
- **Verification Script**: `verify-100-percent-sync.py`
- **Runner Script**: `run-ultimate-sync.sh`

## 💡 Pro Tips

1. **First Run**: Use the interactive runner (`./run-ultimate-sync.sh`) for first-time setup
2. **Automation**: After testing, schedule automated daily sync
3. **Monitoring**: Check logs weekly to ensure sync remains at 100%
4. **Verification**: Run verification monthly to catch any drift
5. **Updates**: Keep API credentials current and rotate them regularly

## 🎯 Quick Command Reference

```bash
# Full interactive sync
./run-ultimate-sync.sh

# Direct sync (no prompts)
python3 jamf-snipe-ultimate-100-percent-sync.py

# Verify sync
python3 verify-100-percent-sync.py

# Check logs
tail -f jamf_snipe_ultimate_sync_*.log

# View latest log
ls -lt *.log | head -1

# Count devices in Jamf
# (requires jq: brew install jq)
curl -s -X POST "${JAMF_URL}/api/oauth/token" ... | jq .

# Count assets in Snipe-IT
curl -s -H "Authorization: Bearer ${SNIPE_IT_API_TOKEN}" \
  "${SNIPE_IT_URL}/api/v1/hardware?limit=1" | jq .total
```

## ✨ Expected Results

After a successful sync, you should have:

- ✅ Every Jamf device in Snipe-IT
- ✅ Correct categories (Student, Staff, SSC, iPads, Apple TVs)
- ✅ User assignments where applicable
- ✅ Detailed sync logs
- ✅ 100% verification pass

## 🏁 Summary

1. **Setup**: 5 minutes (one-time)
2. **Run**: One command (`./run-ultimate-sync.sh`)
3. **Wait**: 30-60 minutes (automated)
4. **Verify**: Check for 100% success
5. **Automate**: Schedule daily sync

**That's it! Your Jamf and Snipe-IT inventories are now perfectly in sync!**

---

**Questions or Issues?**  
Check the logs first - they contain detailed information about every operation.

**Last Updated**: October 7, 2025

