import os
import requests
from dotenv import load_dotenv
import time

# Load environment variables from .env
load_dotenv()

KANDJI_API_TOKEN = os.getenv('KANDJI_API_TOKEN')
KANDJI_BASE_URL = os.getenv('KANDJI_BASE_URL')
KANDJI_BLUEPRINT_ID = os.getenv('KANDJI_BLUEPRINT_ID')
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

if not all([KANDJI_API_TOKEN, KANDJI_BASE_URL, KANDJI_BLUEPRINT_ID, SNIPE_IT_URL, SNIPE_IT_API_TOKEN]):
    print("Missing one or more required environment variables.")
    exit(1)
# 1. Fetch devices from Kandji (all devices)
def fetch_kandji_devices():
    url = f"{KANDJI_BASE_URL}/api/v1/devices"
    headers = {"Authorization": f"Bearer {KANDJI_API_TOKEN}"}
    params = {"blueprint_id": KANDJI_BLUEPRINT_ID}
    print("Requesting:", url)
    print("Headers:", headers)
    print("Params:", params)
    resp = requests.get(url, headers=headers, params=params)
    print("Kandji API status code:", resp.status_code)
    content_type = resp.headers.get('Content-Type', '')
    print("Kandji API response content-type:", content_type)
    print("Kandji API response text (first 500 chars):", resp.text[:500])
    if "text/html" in content_type or resp.text.strip().startswith("<!doctype html>"):
        print("ERROR: Received HTML instead of JSON. This usually means your API token is not valid for this endpoint, or your plan does not include API access.")
        print("Please check your API token, permissions, and Kandji plan.")
        exit(1)
    try:
        devices = resp.json()
    except Exception as e:
        print("ERROR: Could not parse JSON from Kandji API response.")
        print("Raw response text:", resp.text)
        print("Exception:", e)
        exit(1)
    if resp.status_code == 401:
        print("ERROR: Unauthorized. Your API token is invalid or expired.")
        print("Please double-check your API token in the .env file.")
        exit(1)
    return devices

# 2. Ensure the 'Student Loaner' tag exists in Snipe-IT
def get_or_create_tag(tag_name):
    url = f"{SNIPE_IT_URL}/api/v1/tags?search={tag_name}"
    headers = {"Authorization": f"Bearer {SNIPE_IT_API_TOKEN}", "Accept": "application/json"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    tags = resp.json().get('rows', [])
    for tag in tags:
        if tag['name'].lower() == tag_name.lower():
            return tag['id']
    # Tag not found, create it
    create_url = f"{SNIPE_IT_URL}/api/v1/tags"
    resp = requests.post(create_url, headers=headers, json={"name": tag_name})
    resp.raise_for_status()
    print("Snipe-IT API response:", resp.json())
    return resp.json()['payload']['id']

# 3. Create or update device in Snipe-IT with the tag
def sync_device_to_snipeit(device, category_id):
    headers = {"Authorization": f"Bearer {SNIPE_IT_API_TOKEN}", "Accept": "application/json", "Content-Type": "application/json"}
    serial = device.get('serial_number')
    asset_tag = device.get('asset_tag') or serial
    name = device.get('device_name') or serial
    model_name = device.get('model')
    model_id = get_model_id(model_name)
    if not model_id:
        print(f"Skipping device {serial} because model '{model_name}' was not found.")
        return
    # Try to find existing device by serial
    search_url = f"{SNIPE_IT_URL}/api/v1/hardware?search={serial}"
    resp = requests.get(search_url, headers=headers)
    resp.raise_for_status()
    rows = resp.json().get('rows', [])
    data = {
        "name": name,
        "serial": serial,
        "asset_tag": asset_tag,
        "category_id": category_id,
        "model_id": model_id,
        "status_id": 2,  # Deployable
    }
    if rows:
        # Update existing device
        device_id = rows[0]['id']
        update_url = f"{SNIPE_IT_URL}/api/v1/hardware/{device_id}"
        resp = requests.put(update_url, headers=headers, json=data)
        resp.raise_for_status()
        print(f"Updated device {serial} in Snipe-IT.")
    else:
        # Create new device
        create_url = f"{SNIPE_IT_URL}/api/v1/hardware"
        resp = requests.post(create_url, headers=headers, json=data)
        resp.raise_for_status()
        print(f"Created device {serial} in Snipe-IT.")

def get_model_id(model_name):
    headers = {"Authorization": f"Bearer {SNIPE_IT_API_TOKEN}", "Accept": "application/json"}
    url = f"{SNIPE_IT_URL}/api/v1/models?search={model_name}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    rows = resp.json().get('rows', [])
    if rows:
        return rows[0]['id']
    else:
        print(f"Model '{model_name}' not found in Snipe-IT.")
        return None

def main():
    print("Fetching devices from Kandji...")
    devices = fetch_kandji_devices()
    print(f"Found {len(devices)} devices in blueprint {KANDJI_BLUEPRINT_ID}.")
    category_id = 12  # Student Loaner Laptop category ID
    for device in devices:
        success = False
        retries = 0
        while not success and retries < 5:
            try:
                sync_device_to_snipeit(device, category_id)
                success = True
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = 5 + retries * 5  # Exponential backoff: 5, 10, 15, ...
                    print(f"429 Too Many Requests. Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    raise
            time.sleep(2)  # Increase delay between requests
    print("Sync complete.")

if __name__ == "__main__":
    main() 