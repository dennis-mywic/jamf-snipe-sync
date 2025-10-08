# 🚀 Deploy to VM (172.22.2.169) - 2:00 AM MST Schedule

## Quick Deployment

### One-Command Deploy (Recommended)

```bash
cd /Users/dennis/dev
./deploy-both-syncs-to-vm.sh
```

This single command will:
1. Deploy Jamf sync to VM (scheduled for 2:00 AM MST)
2. Deploy Intune sync to VM (scheduled for 2:10 AM MST)
3. Configure timezone to MST
4. Install all dependencies
5. Enable systemd timers

---

## What Gets Deployed

### Jamf Sync (2:00 AM MST)
- `jamf-snipe-ultimate-100-percent-sync.py` - Main sync engine
- `verify-100-percent-sync.py` - Verification tool
- `cleanup-and-sync-100-percent.py` - Cleanup tool
- Systemd timer for daily 2:00 AM MST execution

### Intune Sync (2:10 AM MST)
- `intune-pull-devices.py` - Pull from Intune
- `push-devices-to-snipe.py` - Push to Snipe-IT
- `fix-missing-27-devices.py` - Fix asset tag conflicts
- Systemd timer for daily 2:10 AM MST execution

---

## Manual Deployment (Step-by-Step)

### Step 1: Deploy Jamf Sync

```bash
cd /Users/dennis/dev/jamf-snipe-sync
./deploy-to-vm.sh
```

### Step 2: Deploy Intune Sync

```bash
cd /Users/dennis/dev/intune-snipe-sync
./deploy-to-vm.sh
```

---

## Verify Deployment on VM

After deployment, SSH to the VM and check:

```bash
ssh dennis@172.22.2.169

# Check timezone
timedatectl
# Should show: Time zone: America/Denver (MST)

# Check timers are enabled
sudo systemctl list-timers

# Check specific timer status
sudo systemctl status jamf-snipe-ultimate-sync.timer
sudo systemctl status intune-snipe-sync.timer

# View when next sync will run
sudo systemctl list-timers jamf-snipe-ultimate-sync.timer intune-snipe-sync.timer
```

Expected output:
```
NEXT                        LEFT       LAST  PASSED  UNIT
Wed 2025-10-09 02:00:00 MST 17h left   n/a   n/a     jamf-snipe-ultimate-sync.timer
Wed 2025-10-09 02:10:00 MST 17h left   n/a   n/a     intune-snipe-sync.timer
```

---

## Test Manually (Before Waiting for 2 AM)

```bash
ssh dennis@172.22.2.169

# Test Jamf sync
sudo systemctl start jamf-snipe-ultimate-sync.service
sudo journalctl -u jamf-snipe-ultimate-sync.service -f

# Test Intune sync
sudo systemctl start intune-snipe-sync.service
sudo journalctl -u intune-snipe-sync.service -f
```

---

## Monitor Logs on VM

```bash
ssh dennis@172.22.2.169

# Real-time Jamf sync log
sudo tail -f /var/log/jamf-snipe-sync.log

# Real-time Intune sync log
sudo tail -f /var/log/intune-snipe-sync.log

# View service logs
sudo journalctl -u jamf-snipe-ultimate-sync.service -n 100
sudo journalctl -u intune-snipe-sync.service -n 100
```

---

## Sync Schedule

| Time | Service | What It Does |
|------|---------|--------------|
| 2:00 AM MST | Jamf Sync | Syncs all 191 Apple devices with user mapping |
| 2:10 AM MST | Intune Sync | Syncs all 63 Windows devices with user mapping |

**Total time**: ~30-40 minutes  
**Result**: Perfect 100% MDM mirror (254 devices)

---

## Manage Services on VM

```bash
ssh dennis@172.22.2.169

# Stop timers (disable automation)
sudo systemctl stop jamf-snipe-ultimate-sync.timer
sudo systemctl stop intune-snipe-sync.timer

# Start timers (enable automation)
sudo systemctl start jamf-snipe-ultimate-sync.timer
sudo systemctl start intune-snipe-sync.timer

# Disable timers (prevent auto-start on boot)
sudo systemctl disable jamf-snipe-ultimate-sync.timer
sudo systemctl disable intune-snipe-sync.timer

# Enable timers (auto-start on boot)
sudo systemctl enable jamf-snipe-ultimate-sync.timer
sudo systemctl enable intune-snipe-sync.timer

# Check timer status
sudo systemctl status jamf-snipe-ultimate-sync.timer
sudo systemctl status intune-snipe-sync.timer
```

---

## Troubleshooting on VM

### Check if syncs ran successfully

```bash
ssh dennis@172.22.2.169

# Check last sync status
sudo systemctl status jamf-snipe-ultimate-sync.service
sudo systemctl status intune-snipe-sync.service

# View recent logs
sudo journalctl -u jamf-snipe-ultimate-sync.service --since "24 hours ago"
sudo journalctl -u intune-snipe-sync.service --since "24 hours ago"
```

### If sync fails

```bash
# View full error log
sudo journalctl -u jamf-snipe-ultimate-sync.service -n 500

# Manually run sync to see errors
cd /home/dennis/jamf-snipe-sync
python3 jamf-snipe-ultimate-100-percent-sync.py

# Check credentials
cat /home/dennis/jamf-snipe-sync/.env
```

---

## Update Syncs on VM

To update the sync scripts on the VM:

```bash
ssh dennis@172.22.2.169

# Update Jamf sync
cd /home/dennis/jamf-snipe-sync
git pull origin main
sudo systemctl restart jamf-snipe-ultimate-sync.timer

# Update Intune sync
cd /home/dennis/intune-snipe-sync
git pull origin main
sudo systemctl restart intune-snipe-sync.timer
```

---

## Success Criteria

After deployment and first run, you should have:

- ✅ 254 devices in Snipe-IT
- ✅ All 191 Jamf devices with correct categories
- ✅ All 63 Intune devices with user assignments
- ✅ No duplicates or missing devices
- ✅ Logs showing 100% success rate

---

**Built for West Island College IT Department**  
**VM**: 172.22.2.169  
**Schedule**: Daily at 2:00 AM MST (Jamf) and 2:10 AM MST (Intune)  
**Status**: Production Ready ✅

