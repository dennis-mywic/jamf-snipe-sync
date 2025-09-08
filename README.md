# Jamf Pro to Snipe-IT Device Sync System

> **Automated synchronization system that keeps Jamf Pro and Snipe-IT device inventories in perfect sync**

## Overview

This Python-based system automatically synchronizes device information between Jamf Pro (macOS device management) and Snipe-IT (asset management system). It ensures that all Apple devices managed in Jamf Pro are accurately reflected in your Snipe-IT inventory with up-to-date information including serial numbers, device names, models, and status.

## 🔄 What It Does

- **Bi-directional Sync**: Pulls device data from Jamf Pro and updates/creates corresponding assets in Snipe-IT
- **Real-time Updates**: Keeps device information current including names, serial numbers, and status
- **Automated Execution**: Runs on a schedule via systemd timers for hands-off operation
- **Error Handling**: Robust logging and error recovery for reliable operation
- **Apple Device Focus**: Specifically designed for macOS devices (MacBooks, iMacs, etc.)

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
├── jamf-to-snipe.py           # Main synchronization script
├── requirements.txt           # Python dependencies
├── .env.backup               # Environment variable template
├── ecosystem.config.js       # PM2 configuration
├── package.json             # Node.js dependencies (if any)
├── systemd/                 # Systemd service files
│   ├── jamf-snipe-sync.service
│   └── jamf-snipe-sync.timer
└── apple-device-sync/       # Additional sync modules (submodule)
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

#### Basic Sync (All Devices)
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

#### Using Systemd (Recommended)

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

#### Using PM2 (Alternative)

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
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

- ✅ **Automated Device Discovery**: Finds all Apple devices in Jamf Pro
- ✅ **Smart Matching**: Matches devices by serial number and asset tags
- ✅ **Incremental Sync**: Only updates changed data for efficiency
- ✅ **Error Recovery**: Handles API failures gracefully with retry logic
- ✅ **Comprehensive Logging**: Detailed logs for monitoring and debugging
- ✅ **Flexible Scheduling**: Configurable sync intervals
- ✅ **Data Validation**: Ensures data integrity between systems
- ✅ **Manual Override**: Command-line tools for manual operations

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
