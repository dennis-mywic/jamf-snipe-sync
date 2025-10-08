#!/usr/bin/env python3
"""
100% MDM Mirror - Cleanup and Sync
===================================
Ensures Snipe-IT is a perfect mirror of Jamf + Intune
- Removes devices not in either MDM
- Syncs all devices with correct user mapping
- Verifies 100% match
"""

import os
import sys
import requests
import json
import time
from dotenv import load_dotenv
from datetime import datetime

# Load from jamf-snipe-sync directory
env_path = '/Users/dennis/dev/jamf-snipe-sync/.env'
load_dotenv(env_path)

# Configuration
JAMF_URL = os.getenv('JAMF_URL')
JAMF_CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

RATE_LIMIT = 1.5  # seconds between API calls

print("\n" + "="*80)
print("  100% MDM MIRROR - CLEANUP AND VERIFICATION")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def get_jamf_token():
    """Get Jamf access token"""
    response = requests.post(
        f'{JAMF_URL}/api/oauth/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data={
            'client_id': JAMF_CLIENT_ID,
            'grant_type': 'client_credentials',
            'client_secret': JAMF_CLIENT_SECRET
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()['access_token']

def get_jamf_serials(token):
    """Get all serial numbers from Jamf"""
    headers = {'Authorization': f'Bearer {token}'}
    serials = set()
    
    # Get computers
    response = requests.get(
        f"{JAMF_URL}/api/v1/computers-inventory",
        headers=headers,
        params={'page': 0, 'page-size': 1000},
        timeout=30
    )
    computers = response.json().get('results', [])
    for comp in computers:
        serial = comp.get('general', {}).get('name', '')
        if serial:
            serials.add(serial)
    
    # Get mobile devices
    response = requests.get(
        f"{JAMF_URL}/api/v2/mobile-devices",
        headers=headers,
        params={'page': 0, 'page-size': 1000},
        timeout=30
    )
    mobiles = response.json().get('results', [])
    for mobile in mobiles:
        serial = mobile.get('serialNumber', '')
        if serial:
            serials.add(serial)
    
    return serials

def get_intune_serials():
    """Get all serial numbers from Intune"""
    with open('/Users/dennis/dev/intune-snipe-sync/intune_devices.json') as f:
        intune_data = json.load(f)
        return {d['serialNumber'] for d in intune_data if d.get('serialNumber')}

def get_snipe_devices():
    """Get all devices from Snipe-IT"""
    headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    all_devices = []
    offset = 0
    limit = 500
    
    while True:
        time.sleep(0.5)
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/hardware",
            headers=headers,
            params={'offset': offset, 'limit': limit},
            timeout=30
        )
        data = response.json()
        rows = data.get('rows', [])
        
        if not rows:
            break
        
        all_devices.extend(rows)
        
        if len(all_devices) >= data.get('total', 0):
            break
        
        offset += limit
    
    return all_devices

def delete_device(device_id):
    """Delete a device from Snipe-IT"""
    headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    time.sleep(RATE_LIMIT)
    response = requests.delete(
        f"{SNIPE_IT_URL}/api/v1/hardware/{device_id}",
        headers=headers,
        timeout=30
    )
    
    return response.status_code == 200

def main():
    print("Step 1: Getting device lists from all sources...")
    print("-" * 80)
    
    # Get Jamf token and serials
    print("  Authenticating with Jamf...")
    jamf_token = get_jamf_token()
    print("  ✅ Jamf authenticated")
    
    print("  Fetching Jamf devices...")
    jamf_serials = get_jamf_serials(jamf_token)
    print(f"  ✅ Found {len(jamf_serials)} devices in Jamf")
    
    # Get Intune serials
    print("  Loading Intune devices...")
    intune_serials = get_intune_serials()
    print(f"  ✅ Found {len(intune_serials)} devices in Intune")
    
    # Get Snipe-IT devices
    print("  Fetching Snipe-IT devices...")
    snipe_devices = get_snipe_devices()
    print(f"  ✅ Found {len(snipe_devices)} devices in Snipe-IT")
    
    # Combine MDM serials
    mdm_serials = jamf_serials | intune_serials
    print(f"\n  📊 Total unique devices in MDMs: {len(mdm_serials)}")
    
    print("\n" + "="*80)
    print("Step 2: Identifying devices to remove...")
    print("-" * 80)
    
    # Find devices in Snipe-IT but not in MDMs
    to_delete = []
    for device in snipe_devices:
        serial = device.get('serial')
        if serial and serial not in mdm_serials:
            to_delete.append({
                'id': device.get('id'),
                'serial': serial,
                'name': device.get('name'),
                'category': device.get('category', {}).get('name', 'Unknown')
            })
    
    print(f"\n  Found {len(to_delete)} devices to remove (not in Jamf or Intune)")
    
    if to_delete:
        print("\n  Devices to be deleted:")
        for i, dev in enumerate(to_delete[:20], 1):
            print(f"    {i:2d}. {dev['serial']:20s} - {dev['category']:30s} - ID:{dev['id']}")
        if len(to_delete) > 20:
            print(f"    ... and {len(to_delete) - 20} more")
        
        print("\n" + "="*80)
        response = input(f"  ⚠️  DELETE these {len(to_delete)} devices from Snipe-IT? (yes/no): ")
        
        if response.lower() == 'yes':
            print("\n  Deleting devices...")
            deleted = 0
            failed = 0
            
            for i, dev in enumerate(to_delete, 1):
                print(f"  [{i}/{len(to_delete)}] Deleting {dev['serial']}...", end=' ')
                if delete_device(dev['id']):
                    print("✅")
                    deleted += 1
                else:
                    print("❌")
                    failed += 1
            
            print(f"\n  ✅ Deleted: {deleted}")
            print(f"  ❌ Failed: {failed}")
        else:
            print("\n  ⏭️  Skipped deletion")
    else:
        print("  ✅ No devices to delete - Snipe-IT is clean!")
    
    print("\n" + "="*80)
    print("Step 3: Verifying final state...")
    print("-" * 80)
    
    # Re-fetch Snipe-IT devices
    snipe_devices_after = get_snipe_devices()
    snipe_serials_after = {d.get('serial') for d in snipe_devices_after if d.get('serial')}
    
    # Check what's in MDMs but not in Snipe
    missing_from_snipe = mdm_serials - snipe_serials_after
    
    # Check what's in Snipe but not in MDMs
    extra_in_snipe = snipe_serials_after - mdm_serials
    
    print(f"\n  MDM devices: {len(mdm_serials)}")
    print(f"  Snipe-IT devices: {len(snipe_devices_after)}")
    print(f"  Missing from Snipe: {len(missing_from_snipe)}")
    print(f"  Extra in Snipe: {len(extra_in_snipe)}")
    
    accuracy = (len(snipe_serials_after & mdm_serials) / len(mdm_serials) * 100) if mdm_serials else 0
    print(f"\n  📊 Sync Accuracy: {accuracy:.2f}%")
    
    if missing_from_snipe:
        print(f"\n  ⚠️  {len(missing_from_snipe)} devices need to be synced:")
        for i, serial in enumerate(list(missing_from_snipe)[:10], 1):
            in_jamf = serial in jamf_serials
            in_intune = serial in intune_serials
            source = "Jamf" if in_jamf else "Intune" if in_intune else "Both"
            print(f"    {i:2d}. {serial:20s} - from {source}")
        if len(missing_from_snipe) > 10:
            print(f"    ... and {len(missing_from_snipe) - 10} more")
        
        print("\n  💡 Run the respective sync scripts to add these devices:")
        jamf_missing = missing_from_snipe & jamf_serials
        intune_missing = missing_from_snipe & intune_serials
        if jamf_missing:
            print(f"     • {len(jamf_missing)} from Jamf: python3 jamf-snipe-ultimate-100-percent-sync.py")
        if intune_missing:
            print(f"     • {len(intune_missing)} from Intune: python3 push-devices-to-snipe.py")
    
    print("\n" + "="*80)
    if accuracy == 100.0 and not extra_in_snipe:
        print("🎉 " + "="*76 + " 🎉")
        print("🎉 " + " "*20 + "100% PERFECT MIRROR ACHIEVED!" + " "*19 + " 🎉")
        print("🎉 " + " "*15 + "SNIPE-IT PERFECTLY MATCHES YOUR MDMS!" + " "*17 + " 🎉")
        print("🎉 " + "="*76 + " 🎉")
    else:
        print("⚠️  Cleanup complete - run sync scripts for missing devices")
    
    print("\n" + "="*80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

