# Jamf Pro to Snipe-IT Device Sync System

> **Automated synchronization system that keeps Jamf Pro and Snipe-IT device inventories in perfect sync**

## Overview

This Python-based system automatically synchronizes device information between Jamf Pro (macOS device management) and Snipe-IT (asset management system). It ensures that all Apple devices managed in Jamf Pro are accurately reflected in your Snipe-IT inventory with up-to-date information including serial numbers, device names, models, and status.

## 🔄 What It Does

- **Complete Device Sync**: Synchronizes computers, iPads, and Apple TVs from Jamf Pro to Snipe-IT
- **Prestage-Based Categorization**: Uses Jamf prestage enrollments for 100% accurate device categorization
- **User Checkout Management**: Automatically assigns staff devices to users based on Jamf data
- **Mobile Device Support**: Full support for iPads and Apple TVs with proper categorization
- **Real-time Updates**: Keeps device information current including names, serial numbers, and status
- **Automated Execution**: Runs on a schedule via cron jobs for hands-off operation
- **Error Handling**: Robust logging and error recovery for reliable operation
- **Category-Specific Models**: Prevents Snipe-IT model category overrides for accurate classification

## 🏗️ System Architecture

```
┌─────────────┐    API Calls    ┌──────────────┐    API Calls    ┌─────────────┐
│   Jamf Pro  │ ◄──────────────► │  Sync Script │ ◄──────────────► │  Snipe-IT   │
│             │   (Read Data)    │   (Python)   │  (Create/Update) │             │
└─────────────┘                 └──────────────┘                  └─────────────┘
                                        │
                                        ▼
                                ┌──────────────┐
                                │   Logging    │
                                │   & Monitoring│
                                └──────────────┘
```

## 📁 Repository Structure

```
jamf-snipe-sync/
├── jamf-to-snipe-prestage-bulletproof.py  # Enhanced sync script (RECOMMENDED)
├── jamf-to-snipe.py                       # Legacy synchronization script
├── requirements.txt                       # Python dependencies
├── .env.backup                           # Environment variable template
├── run-daily-sync.sh                     # Automated execution wrapper
├── wipe-all-devices-aggressive.py        # Cleanup utility
├── fix-apple-manufacturer.py             # Manufacturer correction tool
├── fix-apple-models.py                   # Model correction tool
├── detailed-comparison.py                # Device analysis utility
├── find-missing-devices.py               # Missing device detection
├── ecosystem.config.js                   # PM2 configuration
├── package.json                          # Node.js dependencies (if any)
├── systemd/                              # Systemd service files
│   ├── jamf-snipe-sync.service
│   └── jamf-snipe-sync.timer
└── apple-device-sync/                    # Additional sync modules (submodule)
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- Access to Jamf Pro API
- Access to Snipe-IT API
- Linux server (for automated execution)

### 1. Clone Repository

```bash
git clone https://github.com/dennis-mywic/jamf-snipe-sync.git
cd jamf-snipe-sync
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file with your API credentials:

```bash
# Jamf Pro Configuration
JAMF_URL=https://your-jamf-instance.jamfcloud.com
JAMF_CLIENT_ID=your_jamf_client_id
JAMF_CLIENT_SECRET=your_jamf_client_secret

# Snipe-IT Configuration
SNIPE_IT_URL=https://your-snipe-it-instance.com
SNIPE_IT_API_TOKEN=your_snipe_it_api_token

# Optional: Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/jamf-snipe-sync.log
```

### 4. Test Configuration

```bash
python jamf-to-snipe.py --test
```

## 🚀 Running the Script

### Manual Execution

> **Note:** On Ubuntu/Debian systems, you may need to use `python3` instead of `python`. See troubleshooting section below if you get "Command 'python' not found".

#### Enhanced Script (Recommended)
```bash
# Use the enhanced script with prestage-based categorization
python3 jamf-to-snipe-prestage-bulletproof.py
```

#### Legacy Script (Basic Sync)
```bash
python jamf-to-snipe.py
# Or on Ubuntu/Debian systems:
python3 jamf-to-snipe.py
```

#### Sync with Verbose Logging
```bash
python jamf-to-snipe.py --verbose
# Or: python3 jamf-to-snipe.py --verbose
```

#### Dry Run (Test Without Changes)
```bash
python jamf-to-snipe.py --dry-run
# Or: python3 jamf-to-snipe.py --dry-run
```

#### Sync Specific Device Types
```bash
# Sync only MacBooks
python jamf-to-snipe.py --device-type macbook

# Sync only iMacs
python jamf-to-snipe.py --device-type imac
```

#### Force Full Resync
```bash
python jamf-to-snipe.py --force-resync
```

#### Manual Execution with Custom Config
```bash
# Use custom environment file
python jamf-to-snipe.py --env-file /path/to/custom/.env

# Specify log output
python jamf-to-snipe.py --log-file /custom/path/sync.log
```

### Automated Execution

#### Using Cron (Recommended for Daily Sync)

**1. Set up timezone (if needed):**
```bash
# Set server timezone to your local timezone
sudo timedatectl set-timezone America/Denver  # For MST
# Verify timezone
timedatectl
```

**2. Create wrapper script:**
```bash
sudo nano /opt/jamf-snipe-sync/run-daily-sync.sh
```

Add this content:
```bash
#!/bin/bash
# Daily Jamf to Snipe-IT Sync

LOG_FILE="/var/log/jamf-snipe-sync.log"
SCRIPT_DIR="/opt/jamf-snipe-sync"

echo "=== Jamf Sync Started: $(date) ===" >> "$LOG_FILE"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
    source .env
fi

/usr/bin/python3 jamf-to-snipe-prestage-bulletproof.py >> "$LOG_FILE" 2>&1

echo "=== Jamf Sync Completed: $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
```

**3. Make script executable:**
```bash
sudo chmod +x /opt/jamf-snipe-sync/run-daily-sync.sh
```

**4. Add to cron for daily execution:**
```bash
crontab -e
# Add this line for 2:00 AM daily:
0 2 * * * /opt/jamf-snipe-sync/run-daily-sync.sh
```

**5. Verify cron job:**
```bash
crontab -l
```

#### Using Systemd (Alternative)

1. **Install systemd files:**
```bash
sudo cp systemd/jamf-snipe-sync.service /etc/systemd/system/
sudo cp systemd/jamf-snipe-sync.timer /etc/systemd/system/
```

2. **Enable and start the timer:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable jamf-snipe-sync.timer
sudo systemctl start jamf-snipe-sync.timer
```

3. **Check status:**
```bash
sudo systemctl status jamf-snipe-sync.timer
sudo systemctl status jamf-snipe-sync.service
```

## 📊 Monitoring & Logs

### View Real-time Logs
```bash
# Systemd logs
sudo journalctl -u jamf-snipe-sync.service -f

# PM2 logs
pm2 logs jamf-snipe-sync

# Direct log file
tail -f /var/log/jamf-snipe-sync.log
```

### Check Sync Status
```bash
# Last sync run
python jamf-to-snipe.py --status

# Sync statistics
python jamf-to-snipe.py --stats
```

## 🔧 Configuration Options

### Script Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--dry-run` | Test sync without making changes | `--dry-run` |
| `--verbose` | Enable detailed logging | `--verbose` |
| `--force-resync` | Force full resynchronization | `--force-resync` |
| `--device-type` | Sync specific device types only | `--device-type macbook` |
| `--env-file` | Use custom environment file | `--env-file /path/.env` |
| `--log-file` | Custom log file location | `--log-file /custom/sync.log` |
| `--test` | Test API connections only | `--test` |
| `--status` | Show last sync status | `--status` |
| `--stats` | Display sync statistics | `--stats` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JAMF_URL` | Yes | Jamf Pro instance URL |
| `JAMF_CLIENT_ID` | Yes | Jamf Pro API client ID |
| `JAMF_CLIENT_SECRET` | Yes | Jamf Pro API client secret |
| `SNIPE_IT_URL` | Yes | Snipe-IT instance URL |
| `SNIPE_IT_API_TOKEN` | Yes | Snipe-IT API token |
| `LOG_LEVEL` | No | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | No | Custom log file path |
| `SYNC_INTERVAL` | No | Sync interval in minutes (default: 60) |

## 🧪 Testing & Troubleshooting

### Python Command Issues

#### "Command 'python' not found" Error
This is common on Ubuntu/Debian systems where `python` command isn't available by default.

**Solution 1: Use python3 directly**
```bash
python3 jamf-to-snipe.py --verbose
```

**Solution 2: Install python-is-python3 (Recommended)**
```bash
sudo apt update
sudo apt install python-is-python3
# Now 'python' command will work
python jamf-to-snipe.py --verbose
```

**Solution 3: Check Python installation**
```bash
# Check if Python3 is installed
which python3
python3 --version

# Install if missing
sudo apt update
sudo apt install python3 python3-pip
```

**Install Dependencies**
```bash
# Install required packages
pip3 install -r requirements.txt
# Or if pip3 doesn't work:
python3 -m pip install -r requirements.txt
```

### Test API Connections
```bash
# Test Jamf Pro connection
python jamf-to-snipe.py --test-jamf
# Or: python3 jamf-to-snipe.py --test-jamf

# Test Snipe-IT connection
python jamf-to-snipe.py --test-snipe
# Or: python3 jamf-to-snipe.py --test-snipe

# Test both connections
python jamf-to-snipe.py --test
# Or: python3 jamf-to-snipe.py --test
```

### Common Issues

#### DNS Resolution Errors
**Error:** `Failed to resolve 'snipe.mywic.ca' - No address associated with hostname`

This indicates DNS issues with your Snipe-IT domain.

**Solutions:**
```bash
# Check if domain resolves
nslookup snipe.mywic.ca
dig snipe.mywic.ca

# Test direct IP connection (if you know the IP)
ping your-snipe-it-ip-address

# Check /etc/hosts file for local DNS entries
cat /etc/hosts

# Test with curl
curl -I https://snipe.mywic.ca
```

**Fix DNS Issues:**
```bash
# Add to /etc/hosts if needed (replace with actual IP)
echo "192.168.1.100 snipe.mywic.ca" | sudo tee -a /etc/hosts

# Or update your environment to use IP instead of domain
# In .env file:
SNIPE_IT_URL=https://192.168.1.100  # Use actual IP
```

#### API Authentication Errors
```bash
# Verify credentials
python jamf-to-snipe.py --verify-credentials

# Test with verbose logging
python jamf-to-snipe.py --test --verbose
```

#### Sync Failures
```bash
# Check last error
python jamf-to-snipe.py --last-error

# Run with debug logging
python jamf-to-snipe.py --verbose --log-level DEBUG
```

#### Performance Issues
```bash
# Run partial sync
python jamf-to-snipe.py --limit 100

# Check sync performance
python jamf-to-snipe.py --benchmark
```

## 📈 Features

### Core Functionality
- ✅ **Complete Device Coverage**: Syncs computers, iPads, and Apple TVs from Jamf Pro
- ✅ **Prestage-Based Categorization**: Uses Jamf prestage enrollments for 100% accurate categorization
- ✅ **User Checkout Management**: Automatically assigns staff devices to users based on Jamf data
- ✅ **Category-Specific Models**: Creates models with correct categories to prevent Snipe-IT overrides
- ✅ **Smart Device Matching**: Matches devices by serial number and asset tags

### Device Categories Supported
- 🖥️ **Staff Mac Laptops**: MacBooks assigned to staff with user checkout
- 💻 **Student Loaner Laptops**: MacBooks for student use (available for checkout)
- 🏢 **SSC Laptops**: Student Success Center devices
- 📱 **Teacher iPads**: iPads assigned to staff members
- 🖥️ **Check-In iPads**: Kiosk iPads for student check-ins
- 📺 **Apple TVs**: Classroom and boardroom Apple TV devices

### Technical Features
- ✅ **Automated Device Discovery**: Finds all Apple devices in Jamf Pro
- ✅ **Error Recovery**: Handles API failures gracefully with retry logic
- ✅ **Sequential Processing**: Prevents API rate limiting with intelligent delays
- ✅ **Comprehensive Logging**: Detailed logs for monitoring and debugging
- ✅ **Flexible Scheduling**: Configurable sync intervals via cron
- ✅ **Data Validation**: Ensures data integrity between systems
- ✅ **Manual Override**: Command-line tools for manual operations
- ✅ **Utility Scripts**: Cleanup and maintenance tools included

## 📋 Sync Process Flow

1. **Authentication**: Authenticate with both Jamf Pro and Snipe-IT APIs
2. **Device Discovery**: Retrieve all Apple devices from Jamf Pro
3. **Asset Matching**: Find corresponding assets in Snipe-IT by serial number
4. **Data Comparison**: Compare device information between systems
5. **Update/Create**: Update existing assets or create new ones in Snipe-IT
6. **Logging**: Record all changes and any errors encountered
7. **Cleanup**: Handle any orphaned or outdated records

## 🔐 Security

- API credentials stored in environment variables
- HTTPS-only communication with both APIs
- No sensitive data logged
- Regular credential rotation recommended

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues or questions:
- Check the logs: `/var/log/jamf-snipe-sync.log`
- Review recent sync status: `python jamf-to-snipe.py --status`
- Contact: IT Systems Team

---

**Built for West Island College IT Department**  
*Automated device inventory synchronization between Jamf Pro and Snipe-IT*
