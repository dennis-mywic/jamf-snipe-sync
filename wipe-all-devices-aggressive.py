#!/usr/bin/env python3
"""
Aggressively wipe ALL devices from Snipe-IT with retry logic for rate limiting
"""

import requests
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

def wipe_all_devices_aggressive():
    """Delete ALL devices from Snipe-IT with aggressive retry logic"""
    
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    print("🗑️  AGGRESSIVELY WIPING ALL DEVICES FROM SNIPE-IT")
    print("=" * 60)
    
    # Get all devices
    response = requests.get(
        f'{SNIPE_IT_URL}/api/v1/hardware',
        headers=snipe_headers,
        params={'limit': 500}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get devices: {response.status_code}")
        return
    
    devices = response.json().get('rows', [])
    
    print(f"Found {len(devices)} devices to delete")
    
    if not devices:
        print("✅ No devices found!")
        return
    
    # Show sample devices to be deleted
    print("\\n🔍 SAMPLE DEVICES TO DELETE (first 5):")
    for i, device in enumerate(devices[:5], 1):
        print(f"{i:2d}. {device.get('name', 'N/A')} | {device.get('serial', 'N/A')}")
    
    if len(devices) > 5:
        print(f"... and {len(devices) - 5} more devices")
    
    # Final warning and confirmation
    print("\\n⚠️  WARNING: This will PERMANENTLY DELETE ALL DEVICES!")
    print("   This action cannot be undone.")
    
    confirm1 = input(f"\\n❓ Are you sure you want to delete ALL {len(devices)} devices? (yes/NO): ")
    if confirm1.lower() != 'yes':
        print("❌ Cancelled - no devices deleted")
        return
    
    confirm2 = input("❓ Type 'WIPE EVERYTHING' to confirm: ")
    if confirm2 != 'WIPE EVERYTHING':
        print("❌ Cancelled - confirmation text didn't match")
        return
    
    print("\\n🗑️  Starting aggressive deletion process...")
    print("    (Will retry rate-limited requests automatically)")
    
    # Delete each device with aggressive retry
    success_count = 0
    failed_count = 0
    
    for i, device in enumerate(devices, 1):
        device_id = device['id']
        device_name = device.get('name', 'Unknown')
        device_serial = device.get('serial', 'Unknown')
        
        # Retry logic for rate limiting
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                delete_response = requests.delete(
                    f'{SNIPE_IT_URL}/api/v1/hardware/{device_id}',
                    headers=snipe_headers,
                    timeout=30
                )
                
                if delete_response.status_code == 200:
                    print(f"✅ Deleted ({i}/{len(devices)}): {device_name} | {device_serial}")
                    success_count += 1
                    break
                elif delete_response.status_code == 429:
                    # Rate limited - wait and retry
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"⏳ Rate limited - waiting {wait_time}s then retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ Failed ({i}/{len(devices)}): {device_name} | {device_serial} - Max retries exceeded")
                        failed_count += 1
                        break
                else:
                    print(f"❌ Failed ({i}/{len(devices)}): {device_name} | {device_serial} - {delete_response.status_code}")
                    failed_count += 1
                    break
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⏳ Error - waiting {wait_time}s then retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Error deleting {device_name}: {str(e)}")
                    failed_count += 1
                    break
        
        # Small delay between devices to be nice to the API
        time.sleep(0.2)
    
    print("\\n" + "=" * 60)
    print(f"🎯 AGGRESSIVE DELETION COMPLETE")
    print(f"✅ Successfully deleted: {success_count} devices")
    print(f"❌ Failed to delete: {failed_count} devices")
    
    if success_count > 0:
        print(f"\\n🎉 Snipe-IT is now clean and ready for fresh sync!")
        
        # Check final count
        final_response = requests.get(f'{SNIPE_IT_URL}/api/v1/hardware', headers=snipe_headers, params={'limit': 500})
        if final_response.status_code == 200:
            remaining_devices = len(final_response.json().get('rows', []))
            print(f"\\n📊 Final device count: {remaining_devices}")
            if remaining_devices == 0:
                print("🎉 SUCCESS! All devices deleted!")
            else:
                print(f"⚠️  {remaining_devices} devices still remain")

if __name__ == '__main__':
    wipe_all_devices_aggressive()
