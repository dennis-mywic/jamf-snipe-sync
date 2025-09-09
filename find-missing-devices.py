#!/usr/bin/env python3
"""
Find and sync missing devices between Jamf and Snipe-IT
"""

import requests
import os
import time
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

JAMF_URL = os.getenv('JAMF_URL')
JAMF_CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_jamf_token():
    """Get Jamf Pro API token"""
    try:
        response = requests.post(
            f'{JAMF_URL}/api/oauth/token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'client_id': JAMF_CLIENT_ID,
                'client_secret': JAMF_CLIENT_SECRET,
                'grant_type': 'client_credentials'
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('access_token')
    except Exception as e:
        logger.error(f"Failed to get Jamf token: {str(e)}")
        return None

def get_jamf_devices():
    """Get all devices from Jamf Pro"""
    token = get_jamf_token()
    if not token:
        return [], []
    
    jamf_headers = {'Authorization': f'Bearer {token}'}
    
    # Get computers
    computers_response = requests.get(
        f'{JAMF_URL}/api/v1/computers-inventory',
        headers=jamf_headers,
        params={'page': 0, 'page-size': 1000},
        timeout=30
    )
    computers_response.raise_for_status()
    computers = computers_response.json().get('results', [])
    
    # Get mobile devices
    mobile_response = requests.get(
        f'{JAMF_URL}/api/v2/mobile-devices',
        headers=jamf_headers,
        timeout=30
    )
    mobile_response.raise_for_status()
    mobile_devices = mobile_response.json().get('results', [])
    
    # Extract serials
    computer_serials = []
    for comp in computers:
        serial = comp.get('general', {}).get('name', '')
        if serial:
            computer_serials.append(serial)
    
    mobile_serials = []
    for mobile in mobile_devices:
        serial = mobile.get('serialNumber', '')
        if serial:
            mobile_serials.append(serial)
    
    return computer_serials, mobile_serials

def get_snipe_devices():
    """Get all devices from Snipe-IT"""
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    response = requests.get(
        f'{SNIPE_IT_URL}/api/v1/hardware',
        headers=snipe_headers,
        params={'limit': 500},
        timeout=30
    )
    response.raise_for_status()
    
    devices = response.json().get('rows', [])
    serials = []
    
    for device in devices:
        serial = device.get('serial', '')
        if serial:
            serials.append(serial)
    
    return serials

def sync_missing_device(serial, device_type):
    """Sync a single missing device"""
    try:
        # This would use the same logic as the main sync script
        # For now, let's run the main script with a specific device filter
        logger.info(f"Would sync {device_type} device: {serial}")
        return True
    except Exception as e:
        logger.error(f"Failed to sync {serial}: {str(e)}")
        return False

def find_and_fix_missing():
    """Find missing devices and sync them"""
    
    print("🔍 FINDING MISSING DEVICES BETWEEN JAMF AND SNIPE-IT")
    print("=" * 60)
    
    # Get devices from both systems
    print("📱 Getting devices from Jamf Pro...")
    computer_serials, mobile_serials = get_jamf_devices()
    jamf_serials = set(computer_serials + mobile_serials)
    
    print("💾 Getting devices from Snipe-IT...")
    snipe_serials = set(get_snipe_devices())
    
    # Find missing devices
    missing_serials = jamf_serials - snipe_serials
    
    print(f"\n📊 COMPARISON RESULTS:")
    print(f"Jamf devices: {len(jamf_serials)}")
    print(f"  • Computers: {len(computer_serials)}")
    print(f"  • Mobile devices: {len(mobile_serials)}")
    print(f"Snipe devices: {len(snipe_serials)}")
    print(f"Missing devices: {len(missing_serials)}")
    
    if not missing_serials:
        print("✅ No missing devices found! All Jamf devices are in Snipe-IT.")
        return
    
    print(f"\n🔍 MISSING DEVICES:")
    for i, serial in enumerate(sorted(missing_serials), 1):
        device_type = "Computer" if serial in computer_serials else "Mobile"
        print(f"{i:2d}. {serial} ({device_type})")
    
    # Ask if user wants to sync missing devices
    confirm = input(f"\n❓ Sync the {len(missing_serials)} missing devices? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Sync cancelled")
        return
    
    print(f"\n🚀 SYNCING MISSING DEVICES...")
    
    # For now, let's just run the full sync script again
    # The bulletproof script should handle existing devices gracefully
    print("Running full sync to catch missing devices...")
    
    try:
        import subprocess
        result = subprocess.run(['python3', 'jamf-to-snipe-prestage-bulletproof.py'], 
                              capture_output=True, text=True, timeout=1800)
        
        if result.returncode == 0:
            print("✅ Sync script completed successfully")
            
            # Check results
            print("\n🔍 Verifying results...")
            time.sleep(5)  # Wait for API to update
            
            new_snipe_serials = set(get_snipe_devices())
            still_missing = jamf_serials - new_snipe_serials
            
            print(f"Devices now in Snipe: {len(new_snipe_serials)}")
            print(f"Still missing: {len(still_missing)}")
            
            if len(still_missing) == 0:
                print("🎉 SUCCESS! All devices are now synced!")
            else:
                print(f"⚠️  {len(still_missing)} devices still missing:")
                for serial in sorted(still_missing):
                    print(f"  • {serial}")
        else:
            print(f"❌ Sync script failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error running sync: {str(e)}")

if __name__ == '__main__':
    find_and_fix_missing()
