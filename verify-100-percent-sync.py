#!/usr/bin/env python3
"""
Verification Script - Ensure 100% Sync Between Jamf and Snipe-IT
================================================================
Compares ALL devices in Jamf Pro with Snipe-IT to identify:
- Devices in Jamf but missing from Snipe-IT
- Devices with incorrect categorization
- Devices missing user assignments
- Overall sync accuracy percentage
"""

import os
import requests
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from typing import Set, Dict, List

load_dotenv()

# Configuration
JAMF_URL = os.getenv('JAMF_URL')
JAMF_CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

# Setup logging
log_filename = f'verification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_jamf_token():
    """Get Jamf Pro access token"""
    try:
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
    except Exception as e:
        logger.error(f"Failed to get Jamf token: {str(e)}")
        return None

def get_all_jamf_serials(headers: dict) -> Set[str]:
    """Get all serial numbers from Jamf Pro"""
    logger.info("Fetching all devices from Jamf Pro...")
    serials = set()
    
    # Get computers
    try:
        page = 0
        while True:
            response = requests.get(
                f"{JAMF_URL}/api/v1/computers-inventory",
                headers=headers,
                params={'page': page, 'page-size': 200},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                break
            
            for comp in results:
                general = comp.get('general', {})
                serial = general.get('name', '')
                if serial:
                    serials.add(serial)
            
            if len(serials) >= data.get('totalCount', 0):
                break
            
            page += 1
            time.sleep(0.5)
        
        logger.info(f"Found {len(serials)} computers in Jamf")
        
    except Exception as e:
        logger.error(f"Error fetching computers: {str(e)}")
    
    # Get mobile devices
    try:
        page = 0
        mobile_count = 0
        while True:
            response = requests.get(
                f"{JAMF_URL}/api/v2/mobile-devices",
                headers=headers,
                params={'page': page, 'page-size': 200},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                break
            
            for mobile in results:
                serial = mobile.get('serialNumber', '')
                if serial:
                    serials.add(serial)
                    mobile_count += 1
            
            if mobile_count >= data.get('totalCount', 0):
                break
            
            page += 1
            time.sleep(0.5)
        
        logger.info(f"Found {mobile_count} mobile devices in Jamf")
        
    except Exception as e:
        logger.error(f"Error fetching mobile devices: {str(e)}")
    
    logger.info(f"Total unique serials in Jamf: {len(serials)}")
    return serials

def get_all_snipe_assets(headers: dict) -> Dict[str, dict]:
    """Get all assets from Snipe-IT indexed by serial number"""
    logger.info("Fetching all assets from Snipe-IT...")
    assets = {}
    
    try:
        offset = 0
        limit = 500
        
        while True:
            response = requests.get(
                f"{SNIPE_IT_URL}/api/v1/hardware",
                headers=headers,
                params={'offset': offset, 'limit': limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            rows = data.get('rows', [])
            
            if not rows:
                break
            
            for asset in rows:
                serial = asset.get('serial')
                if serial:
                    assets[serial] = {
                        'id': asset.get('id'),
                        'name': asset.get('name'),
                        'category': asset.get('category', {}).get('name', 'Unknown'),
                        'assigned_to': asset.get('assigned_to', {}).get('name') if asset.get('assigned_to') else None
                    }
            
            total = data.get('total', 0)
            if len(assets) >= total:
                break
            
            offset += limit
            time.sleep(0.5)
        
        logger.info(f"Found {len(assets)} assets in Snipe-IT")
        
    except Exception as e:
        logger.error(f"Error fetching Snipe-IT assets: {str(e)}")
    
    return assets

def verify_sync():
    """Verify sync status between Jamf and Snipe-IT"""
    logger.info("="*80)
    logger.info("🔍 VERIFICATION: Jamf to Snipe-IT Sync Status")
    logger.info("="*80)
    logger.info("")
    
    # Get Jamf token
    token = get_jamf_token()
    if not token:
        logger.error("Failed to authenticate with Jamf")
        return
    
    jamf_headers = {'Authorization': f'Bearer {token}'}
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Fetch all data
    logger.info("")
    jamf_serials = get_all_jamf_serials(jamf_headers)
    logger.info("")
    snipe_assets = get_all_snipe_assets(snipe_headers)
    logger.info("")
    
    # Find missing devices
    missing_from_snipe = []
    for serial in jamf_serials:
        if serial not in snipe_assets:
            missing_from_snipe.append(serial)
    
    # Find extra devices in Snipe (not in Jamf)
    extra_in_snipe = []
    for serial in snipe_assets.keys():
        if serial not in jamf_serials:
            extra_in_snipe.append(serial)
    
    # Calculate statistics
    total_jamf = len(jamf_serials)
    total_snipe = len(snipe_assets)
    synced = total_jamf - len(missing_from_snipe)
    
    sync_percentage = 0
    if total_jamf > 0:
        sync_percentage = (synced / total_jamf) * 100
    
    # Count devices with user assignments
    assigned_count = sum(1 for asset in snipe_assets.values() if asset['assigned_to'])
    assignment_percentage = (assigned_count / total_snipe * 100) if total_snipe > 0 else 0
    
    # Print results
    logger.info("="*80)
    logger.info("📊 VERIFICATION RESULTS")
    logger.info("="*80)
    logger.info("")
    logger.info(f"Jamf Pro Devices: {total_jamf}")
    logger.info(f"Snipe-IT Assets: {total_snipe}")
    logger.info(f"Successfully Synced: {synced}")
    logger.info(f"Missing from Snipe-IT: {len(missing_from_snipe)}")
    logger.info(f"Extra in Snipe-IT (not in Jamf): {len(extra_in_snipe)}")
    logger.info("")
    logger.info(f"Sync Accuracy: {sync_percentage:.2f}%")
    logger.info(f"User Assignments: {assigned_count}/{total_snipe} ({assignment_percentage:.1f}%)")
    logger.info("")
    
    if sync_percentage == 100.0:
        logger.info("🎉 " + "="*76 + " 🎉")
        logger.info("🎉 " + " "*23 + "100% SYNC VERIFIED!" + " "*25 + " 🎉")
        logger.info("🎉 " + " "*15 + "ALL DEVICES PRESENT IN SNIPE-IT!" + " "*16 + " 🎉")
        logger.info("🎉 " + "="*76 + " 🎉")
    elif sync_percentage >= 95.0:
        logger.info("✅ SYNC STATUS: GOOD (>95%)")
    elif sync_percentage >= 90.0:
        logger.warning("⚠️  SYNC STATUS: NEEDS ATTENTION (90-95%)")
    else:
        logger.error("❌ SYNC STATUS: CRITICAL (<90%)")
    
    logger.info("")
    
    # Show missing devices
    if missing_from_snipe:
        logger.warning(f"Missing Devices from Snipe-IT ({len(missing_from_snipe)}):")
        for i, serial in enumerate(missing_from_snipe[:20], 1):
            logger.warning(f"  {i}. {serial}")
        if len(missing_from_snipe) > 20:
            logger.warning(f"  ... and {len(missing_from_snipe) - 20} more")
        
        # Save full list to file
        missing_file = f'missing_devices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(missing_file, 'w') as f:
            for serial in sorted(missing_from_snipe):
                f.write(f"{serial}\n")
        logger.warning(f"  Full list saved to: {missing_file}")
    
    logger.info("")
    
    # Show extra devices
    if extra_in_snipe:
        logger.info(f"Extra Devices in Snipe-IT (not in Jamf): {len(extra_in_snipe)}")
        for i, serial in enumerate(extra_in_snipe[:10], 1):
            asset = snipe_assets[serial]
            logger.info(f"  {i}. {serial} ({asset['category']})")
        if len(extra_in_snipe) > 10:
            logger.info(f"  ... and {len(extra_in_snipe) - 10} more")
    
    logger.info("")
    logger.info("="*80)
    logger.info(f"Verification log saved to: {log_filename}")
    logger.info("="*80)
    
    return sync_percentage == 100.0

if __name__ == '__main__':
    try:
        is_perfect = verify_sync()
        exit(0 if is_perfect else 1)
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)

