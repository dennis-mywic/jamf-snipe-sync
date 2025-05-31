# Device Migration Tool

This tool helps migrate devices from Kandji and Jamf to Snipe-IT.

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API credentials:
```bash
# Kandji API Configuration
KANDJI_API_TOKEN=your_kandji_api_token
KANDJI_BASE_URL=your_kandji_base_url

# Jamf API Configuration
JAMF_API_USERNAME=your_jamf_username
JAMF_API_PASSWORD=your_jamf_password
JAMF_BASE_URL=your_jamf_base_url

# Snipe-IT Configuration
SNIPE_API_TOKEN=your_snipe_api_token
SNIPE_BASE_URL=your_snipe_base_url
```

## Usage

Run the migration script:
```bash
python migrate_devices.py
```

The script will:
1. Migrate all devices from Kandji
2. Migrate all devices from Jamf
3. Save the results to `migration_results.csv`

## Notes

- The script creates a CSV report of all migrations, including any errors
- Make sure to test with a small subset of devices first
- You may need to adjust the model mapping in the `_get_snipe_model_id` method
- The script assumes all devices are in "Ready to Deploy" status (status_id: 1) 