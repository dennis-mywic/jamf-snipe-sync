#!/usr/bin/env python3
"""
Fix Apple devices incorrectly assigned to Lenovo manufacturer
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

def fix_manufacturer_assignments():
    """Fix Apple devices incorrectly assigned to Lenovo manufacturer"""
    
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    print("🔧 FIXING APPLE DEVICE MANUFACTURER ASSIGNMENTS")
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
    
    # Find Apple devices with wrong manufacturer
    apple_devices_to_fix = []
    
    for device in devices:
        manufacturer = device.get('manufacturer', {})
        manufacturer_name = manufacturer.get('name', '') if manufacturer else ''
        manufacturer_id = manufacturer.get('id') if manufacturer else None
        
        model = device.get('model', {})
        model_name = model.get('name', '') if model else ''
        
        # Check if this is an Apple device with wrong manufacturer
        is_apple_device = any(apple_term in model_name.lower() for apple_term in [
            'ipad', 'macbook', 'imac', 'mac mini', 'mac studio', 'apple tv'
        ])
        
        if is_apple_device and manufacturer_id == 1:  # Lenovo manufacturer ID
            apple_devices_to_fix.append({
                'id': device.get('id'),
                'name': device.get('name', ''),
                'serial': device.get('serial', ''),
                'model': model_name,
                'current_manufacturer': manufacturer_name,
                'current_manufacturer_id': manufacturer_id
            })
    
    print(f"Found {len(apple_devices_to_fix)} Apple devices with incorrect manufacturer")
    
    if not apple_devices_to_fix:
        print("✅ No devices need fixing!")
        return
    
    # Show first few devices to fix
    print("\n🔍 DEVICES TO FIX (first 10):")
    for i, device in enumerate(apple_devices_to_fix[:10], 1):
        print(f"{i:2d}. {device['name']} | {device['serial']} | {device['model']}")
    
    # Ask for confirmation
    if len(apple_devices_to_fix) > 10:
        print(f"... and {len(apple_devices_to_fix) - 10} more devices")
    
    confirm = input(f"\n❓ Fix manufacturer for {len(apple_devices_to_fix)} devices? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Cancelled")
        return
    
    # Fix each device
    success_count = 0
    failed_count = 0
    
    for device in apple_devices_to_fix:
        device_id = device['id']
        
        # Update device to use Apple manufacturer (ID: 9)
        update_data = {
            'manufacturer_id': 9  # Apple manufacturer ID
        }
        
        try:
            update_response = requests.patch(
                f'{SNIPE_IT_URL}/api/v1/hardware/{device_id}',
                headers=snipe_headers,
                json=update_data,
                timeout=30
            )
            
            if update_response.status_code == 200:
                print(f"✅ Fixed: {device['name']} | {device['serial']}")
                success_count += 1
            else:
                print(f"❌ Failed: {device['name']} | {device['serial']} - {update_response.status_code}")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ Error fixing {device['name']}: {str(e)}")
            failed_count += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 MANUFACTURER FIX COMPLETE")
    print(f"✅ Successfully fixed: {success_count} devices")
    print(f"❌ Failed to fix: {failed_count} devices")
    
    if success_count > 0:
        print(f"\n🎉 All Apple devices should now show 'Apple' as manufacturer!")

if __name__ == '__main__':
    fix_manufacturer_assignments()
