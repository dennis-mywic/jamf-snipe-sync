#!/usr/bin/env python3
"""
Wipe all Apple devices from Snipe-IT for clean resync
"""

import requests
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

def wipe_apple_devices():
    """Delete all Apple devices from Snipe-IT"""
    
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    print("🗑️  WIPING ALL APPLE DEVICES FROM SNIPE-IT")
    print("=" * 50)
    
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
    
    # Find Apple devices
    apple_devices = []
    
    for device in devices:
        manufacturer = device.get('manufacturer', {})
        manufacturer_name = manufacturer.get('name', '') if manufacturer else ''
        
        if 'apple' in manufacturer_name.lower():
            apple_devices.append({
                'id': device.get('id'),
                'name': device.get('name', ''),
                'serial': device.get('serial', ''),
                'model': device.get('model', {}).get('name', '') if device.get('model') else ''
            })
    
    print(f"Found {len(apple_devices)} Apple devices to delete")
    
    if not apple_devices:
        print("✅ No Apple devices found!")
        return
    
    # Show sample devices to be deleted
    print("\\n🔍 SAMPLE DEVICES TO DELETE (first 10):")
    for i, device in enumerate(apple_devices[:10], 1):
        print(f"{i:2d}. {device['name']} | {device['serial']} | {device['model']}")
    
    if len(apple_devices) > 10:
        print(f"... and {len(apple_devices) - 10} more devices")
    
    # Final warning and confirmation
    print("\\n⚠️  WARNING: This will PERMANENTLY DELETE all Apple devices!")
    print("   This action cannot be undone.")
    print("   You'll need to run the sync script afterwards to restore from Jamf.")
    
    confirm1 = input(f"\\n❓ Are you sure you want to delete {len(apple_devices)} Apple devices? (yes/NO): ")
    if confirm1.lower() != 'yes':
        print("❌ Cancelled - no devices deleted")
        return
    
    confirm2 = input("❓ Type 'DELETE ALL' to confirm: ")
    if confirm2 != 'DELETE ALL':
        print("❌ Cancelled - confirmation text didn't match")
        return
    
    print("\\n🗑️  Starting deletion process...")
    
    # Delete each device
    success_count = 0
    failed_count = 0
    
    for i, device in enumerate(apple_devices, 1):
        device_id = device['id']
        
        try:
            delete_response = requests.delete(
                f'{SNIPE_IT_URL}/api/v1/hardware/{device_id}',
                headers=snipe_headers,
                timeout=30
            )
            
            if delete_response.status_code == 200:
                print(f"✅ Deleted ({i}/{len(apple_devices)}): {device['name']} | {device['serial']}")
                success_count += 1
            else:
                print(f"❌ Failed ({i}/{len(apple_devices)}): {device['name']} | {device['serial']} - {delete_response.status_code}")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ Error deleting {device['name']}: {str(e)}")
            failed_count += 1
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    print("\\n" + "=" * 50)
    print(f"🎯 DELETION COMPLETE")
    print(f"✅ Successfully deleted: {success_count} devices")
    print(f"❌ Failed to delete: {failed_count} devices")
    
    if success_count > 0:
        print(f"\\n🎉 Snipe-IT is now clean and ready for fresh sync!")
        print("\\n🚀 Next step: Run the sync script to restore all devices from Jamf:")
        print("   python3 jamf-to-snipe-prestage-bulletproof.py")

if __name__ == '__main__':
    wipe_apple_devices()
