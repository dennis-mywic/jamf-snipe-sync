# Jamf Pro to Snipe-IT Sync

This script synchronizes device information from Jamf Pro to Snipe-IT asset management system.

## Features

- Syncs both computers and mobile devices from Jamf Pro smart groups
- Supports both OAuth and Basic authentication for Jamf Pro
- Automatic model creation in Snipe-IT
- User assignment based on device ownership
- Improved error handling and retry logic
- Optimized performance with reduced delays and better concurrency

## Prerequisites

- Python 3.7+
- Access to Jamf Pro API
- Access to Snipe-IT API
- Required Python packages (see requirements.txt)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the project directory with the following variables:

```env
# Jamf Pro Configuration
JAMF_URL=your-jamf-instance.jamfcloud.com
JAMF_CLIENT_ID=your-client-id
JAMF_CLIENT_SECRET=your-client-secret
# OR use basic auth:
# JAMF_USERNAME=your-username
# JAMF_PASSWORD=your-password

# Snipe-IT Configuration
SNIPE_IT_URL=https://your-snipe-instance.com
SNIPE_IT_API_TOKEN=your-api-token
SNIPE_IT_URL_FALLBACK=https://172.22.2.74  # Optional fallback URL
```

## Usage

### Manual Run

```bash
python3 jamf-to-snipe.py
```

### Using PM2 (Recommended)

1. Install PM2 if not already installed:
   ```bash
   npm install -g pm2
   ```

2. Start the sync service:
   ```bash
   pm2 start ecosystem.config.js
   ```

3. Monitor the service:
   ```bash
   pm2 status
   pm2 logs jamf-snipe-sync
   ```

4. Stop the service:
   ```bash
   pm2 stop jamf-snipe-sync
   ```

### Health Check

Run the health check script to verify system status:

```bash
python3 health_check.py
```

## Performance Optimizations

The script has been optimized for better performance:

- **Reduced Delays**: Device processing delays reduced from 14 seconds to 2 seconds
- **Improved Concurrency**: Increased worker threads from 1 to 3 for device processing
- **Better Connection Pooling**: Increased connection pool size and improved retry logic
- **Timeout Handling**: Added 30-second timeouts to all API calls
- **Rate Limiting**: Added 429 status code handling for rate limits

## Logging

Logs are written to:
- Console output
- `sync_log_YYYYMMDD_HHMMSS.log` files
- PM2 log files (if using PM2)

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check network connectivity and firewall settings
2. **Authentication Errors**: Verify Jamf Pro credentials and API permissions
3. **Rate Limiting**: The script includes automatic retry logic for rate limits
4. **Missing Models**: The script automatically creates models in Snipe-IT

### Health Check Failures

If the health check fails:

1. Verify all environment variables are set correctly
2. Check API connectivity to both Jamf Pro and Snipe-IT
3. Ensure recent log files exist (indicating successful runs)

### Performance Issues

If the script is running slowly:

1. Check network latency to Jamf Pro and Snipe-IT
2. Verify API response times
3. Consider adjusting worker thread counts in the script

## Configuration Details

### Smart Groups

The script syncs devices from these Jamf Pro smart groups:

**Computers:**
- All Staff Mac (ID: 22)
- Student Loaners (ID: 3)

**Mobile Devices:**
- Apple TVs (ID: 1)
- Check-In iPad (ID: 11)
- Donations iPad (ID: 10)
- Moneris iPad (ID: 9)
- Teacher iPad (ID: 2)

### Snipe-IT Categories

Devices are assigned to these Snipe-IT categories:

- Staff Mac Laptop (ID: 16)
- Student Loaner Laptop (ID: 12)
- Check-In iPad (ID: 20)
- Donations iPad (ID: 19)
- Moneris iPad (ID: 21)
- Teacher iPad (ID: 15)
- Apple TVs (ID: 11)

## Monitoring

The script includes comprehensive logging and monitoring:

- Detailed progress logging
- Error tracking and reporting
- Performance metrics
- Health check functionality

## Support

For issues or questions:

1. Check the logs for detailed error messages
2. Run the health check script
3. Verify API connectivity and credentials
4. Review the troubleshooting section above
