# Jamf Pro to Snipe-IT Device Sync

This script synchronizes Mac devices between Jamf Pro and Snipe-IT asset management systems. It runs daily at 1 AM Mountain Time to ensure both systems stay in sync.

## Features

- Syncs Mac devices from Jamf Pro to Snipe-IT
- Creates/updates device records in Snipe-IT
- Matches and assigns devices to users based on email
- Handles case-insensitive email matching
- Includes retry logic for rate limits
- Runs automatically via systemd timer

## Prerequisites

- Python 3.x
- Access to Jamf Pro API
- Access to Snipe-IT API
- Ubuntu server (for systemd service)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/dennis-mywic/apple-device-sync.git
cd apple-device-sync
```

2. Install dependencies:
```bash
pip3 install requests python-dotenv
```

3. Create a `.env` file with your credentials:
```bash
JAMF_URL=https://your-jamf-instance.com
JAMF_CLIENT_ID=your-client-id
JAMF_CLIENT_SECRET=your-client-secret
SNIPE_IT_URL=https://your-snipeit-instance.com
SNIPE_IT_API_TOKEN=your-api-token
```

4. Install the systemd service and timer:
```bash
sudo cp systemd/jamf-snipe-sync.* /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/jamf-snipe-sync.*
sudo systemctl daemon-reload
sudo systemctl enable jamf-snipe-sync.timer
sudo systemctl start jamf-snipe-sync.timer
```

## Usage

The script will run automatically every day at 1 AM Mountain Time. To run it manually:

```bash
python3 jamf-to-snipe.py
```

## Logging

Logs are written to standard output and can be viewed using:
```bash
journalctl -u jamf-snipe-sync.service
```

## Configuration

The script uses the following environment variables:
- `JAMF_URL`: Your Jamf Pro instance URL
- `JAMF_CLIENT_ID`: OAuth client ID for Jamf Pro
- `JAMF_CLIENT_SECRET`: OAuth client secret for Jamf Pro
- `SNIPE_IT_URL`: Your Snipe-IT instance URL
- `SNIPE_IT_API_TOKEN`: API token for Snipe-IT

## Troubleshooting

Common issues:
1. Rate limiting: The script includes retry logic with exponential backoff
2. User not found: Check email addresses match between systems
3. Authentication: Verify your API credentials are correct

## License

MIT License
