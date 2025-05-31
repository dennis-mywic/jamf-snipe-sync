# Kandji to Snipe-IT Sync

This project syncs Mac device data from Kandji to Snipe-IT, creating or updating assets in the specified Snipe-IT category.

## Features
- Fetches devices from Kandji using the API and a specified blueprint.
- Maps Kandji device fields to Snipe-IT asset fields.
- Uses serial number as the asset tag.
- Looks up or creates the correct model in Snipe-IT.
- Assigns assets to the "Student Loaner Laptop" category (ID 12).
- Sets asset status to "Deployable" (ID 2).
- Handles Snipe-IT API rate limiting.

## Setup
1. Clone this repository or copy the script to your project directory.
2. Create a `.env` file in the `kandji-snipe-sync` directory with the following variables:

```
KANDJI_API_TOKEN=your_kandji_api_token
KANDJI_BASE_URL=https://yourtenant.api.kandji.io
KANDJI_BLUEPRINT_ID=your_blueprint_id
SNIPE_IT_URL=https://your-snipeit-instance
SNIPE_IT_API_TOKEN=your_snipeit_api_token
```

3. Ensure you have Python 3 and the required packages:
```
pip install requests python-dotenv
```

## Usage
From the `kandji-snipe-sync` directory, run:
```
python3 kandji_to_snipeit_sync.py
```

## Notes
- Make sure the Snipe-IT category and models exist before running the script.
- The script will skip devices if the model is not found in Snipe-IT.
- Adjust the category and status IDs in the script as needed for your environment.

## License
MIT # apple-device-sync
