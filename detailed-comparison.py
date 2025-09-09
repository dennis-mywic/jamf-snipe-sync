#!/usr/bin/env python3
"""
Detailed comparison to find exactly which devices are missing
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_jamf_token():
    response = requests.post(
        f'{os.getenv("JAMF_URL")}/api/oauth/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data={
            'client_id': os.getenv('JAMF_CLIENT_ID'),
            'client_secret': os.getenv('JAMF_CLIENT_SECRET'),
            'grant_type': 'client_credentials'
        }
    )
    return response.json().get('access_token')

def main():
    print("🔍 DETAILED DEVICE COMPARISON")
    print("=" * 50)
    
    # Get Jamf devices
    token = get_jamf_token()
    jamf_headers = {'Authorization': f'Bearer {token}'}
    
    # Get computers with details
    computers_response = requests.get(
        f'{os.getenv("JAMF_URL")}/api/v1/computers-inventory',
        headers=jamf_headers,
        params={'page': 0, 'page-size': 1000}
    )
    computers = computers_response.json().get('results', [])
    
    jamf_computer_serials = []
    for comp in computers:
        general = comp.get('general', {})
        serial = general.get('name', '')  # This is where the serial is stored
        device_name = general.get('name', '')
        model = comp.get('hardware', {}).get('model', '') if comp.get('hardware') else 'Unknown'
        
        if serial:
            jamf_computer_serials.append({
                'serial': serial,
                'name': device_name,
                'model': model,
                'type': 'Computer'
            })
    
    # Get mobile devices
    mobile_response = requests.get(
        f'{os.getenv("JAMF_URL")}/api/v2/mobile-devices',
        headers=jamf_headers
    )
    mobile_devices = mobile_response.json().get('results', [])
    
    jamf_mobile_serials = []
    for mobile in mobile_devices:
        serial = mobile.get('serialNumber', '')
        name = mobile.get('name', '')
        model = mobile.get('model', '')
        
        if serial:
            jamf_mobile_serials.append({
                'serial': serial,
                'name': name,
                'model': model,
                'type': 'Mobile'
            })
    
    # Get Snipe devices
    snipe_headers = {
        'Authorization': f'Bearer {os.getenv("SNIPE_IT_API_TOKEN")}',
        'Accept': 'application/json'
    }
    
    snipe_response = requests.get(
        f'{os.getenv("SNIPE_IT_URL")}/api/v1/hardware',
        headers=snipe_headers,
        params={'limit': 500}
    )
    snipe_devices = snipe_response.json().get('rows', [])
    
    snipe_serials = []
    for device in snipe_devices:
        serial = device.get('serial', '')
        name = device.get('name', '')
        model = device.get('model', {}).get('name', '') if device.get('model') else ''
        
        if serial:
            snipe_serials.append({
                'serial': serial,
                'name': name,
                'model': model
            })
    
    # Create sets for comparison
    jamf_all_devices = jamf_computer_serials + jamf_mobile_serials
    jamf_serial_set = {device['serial'] for device in jamf_all_devices}
    snipe_serial_set = {device['serial'] for device in snipe_serials}
    
    # Find missing devices
    missing_serials = jamf_serial_set - snipe_serial_set
    extra_serials = snipe_serial_set - jamf_serial_set
    
    print(f"📊 DETAILED COUNTS:")
    print(f"Jamf computers: {len(jamf_computer_serials)}")
    print(f"Jamf mobile devices: {len(jamf_mobile_serials)}")
    print(f"Jamf total: {len(jamf_all_devices)}")
    print(f"Snipe devices: {len(snipe_serials)}")
    print(f"Missing from Snipe: {len(missing_serials)}")
    print(f"Extra in Snipe: {len(extra_serials)}")
    
    if missing_serials:
        print(f"\\n🔍 MISSING DEVICES ({len(missing_serials)}):")
        for i, serial in enumerate(sorted(missing_serials), 1):
            # Find device details
            jamf_device = next((d for d in jamf_all_devices if d['serial'] == serial), None)
            if jamf_device:
                print(f"{i:2d}. {serial} | {jamf_device['name']} | {jamf_device['model']} ({jamf_device['type']})")
            else:
                print(f"{i:2d}. {serial} | Unknown device")
    
    if extra_serials:
        print(f"\\n➕ EXTRA DEVICES IN SNIPE ({len(extra_serials)}):")
        for i, serial in enumerate(sorted(extra_serials), 1):
            snipe_device = next((d for d in snipe_serials if d['serial'] == serial), None)
            if snipe_device:
                print(f"{i:2d}. {serial} | {snipe_device['name']} | {snipe_device['model']}")
    
    if not missing_serials and not extra_serials:
        print("\\n✅ PERFECT MATCH! All devices are synced correctly.")
    
    return missing_serials

if __name__ == '__main__':
    missing_serials = main()
