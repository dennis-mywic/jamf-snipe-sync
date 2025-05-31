# Apple Device Sync (Kandji to Snipe-IT)

This project automates syncing Mac device data from Kandji to Snipe-IT, ensuring your asset inventory is always up to date.

## Main Features
- **Fetches Devices from Kandji:** Uses the Kandji API and a specified blueprint to get all managed Mac devices.
- **Maps Device Fields:** Maps Kandji device fields to Snipe-IT asset fields, using the serial number as the asset tag.
- **Model & Category Handling:** Looks up or creates the correct model in Snipe-IT and assigns assets to the "Student Loaner Laptop" category (ID 12).
- **Status Management:** Sets asset status to "Deployable" (ID 2).
- **API Rate Limiting:** Handles Snipe-IT API rate limiting gracefully.
- **Cross-Platform:** Works on macOS, Linux, or Windows (requires Python 3).

## Key Files
- `kandji_to_snipeit_sync.py`: Main sync script.
- `.env`: Stores API tokens and configuration (not committed to git).

## Environment Variables
Create a `.env` file in the project root with:
```
KANDJI_API_TOKEN=your_kandji_api_token
KANDJI_BASE_URL=https://yourtenant.api.kandji.io
KANDJI_BLUEPRINT_ID=your_blueprint_id
SNIPE_IT_URL=https://your-snipeit-instance
SNIPE_IT_API_TOKEN=your_snipeit_api_token
```

## Usage
1. Install dependencies:
   ```
   pip install requests python-dotenv
   ```
2. Run the sync script:
   ```
   python3 kandji_to_snipeit_sync.py
   ```

## Notes
- Ensure the Snipe-IT category (ID 12) and models exist before running the script.
- The script will skip devices if the model is not found in Snipe-IT.
- Adjust category and status IDs in the script as needed for your environment.

## OS Compatibility
- This project is **not OS dependent**. It runs anywhere Python 3 is available.

## License
MIT # apple-device-sync
