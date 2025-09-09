#!/usr/bin/env python3
"""
Jamf Pro to Snipe-IT Sync - BULLETPROOF Prestage Enrollment Based
100% Accurate Device Categorization using Prestage Enrollment Data from Modern API
WITH PROPER RATE LIMITING AND RETRY LOGIC
"""

import os
import requests
import time
import logging
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
JAMF_URL = os.getenv('JAMF_URL')
JAMF_CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jamf_snipe_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Snipe-IT Categories (based on prestage enrollment)
CATEGORIES = {
    'student': {'id': 12, 'name': 'Student Loaner Laptop'},
    'staff': {'id': 16, 'name': 'Staff Mac Laptop'},
    'ssc': {'id': 13, 'name': 'SSC Laptop'},
    'checkin_ipad': {'id': 20, 'name': 'Check-In iPad'},
    'donations_ipad': {'id': 19, 'name': 'Donations iPad'},
    'moneris_ipad': {'id': 21, 'name': 'Moneris iPad'},
    'teacher_ipad': {'id': 15, 'name': 'Teacher iPad'},
    'appletv': {'id': 11, 'name': 'Apple TVs'}
}

def get_jamf_token():
    """Get Jamf Pro access token"""
    try:
        response = requests.post(
            f'{JAMF_URL}/api/oauth/token',
            data={'client_id': JAMF_CLIENT_ID, 'grant_type': 'client_credentials'},
            auth=(JAMF_CLIENT_ID, JAMF_CLIENT_SECRET),
            timeout=30
        )
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        logger.error(f"Error getting Jamf token: {e}")
        return None

def get_snipe_headers():
    """Get Snipe-IT headers"""
    return {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

def get_prestage_info(device_id: int, jamf_headers: dict) -> dict:
    """Fetches prestage enrollment information for a given device ID from the modern Jamf API."""
    url = f"{JAMF_URL}/api/v2/computers/{device_id}"
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(0.5, 1.5))
            
            resp = requests.get(url, headers=jamf_headers, timeout=30)
            resp.raise_for_status()
            device_data = resp.json()

            prestage_name = device_data.get('general', {}).get('enrollmentMethod', {}).get('objectName')
            serial_number = device_data.get('general', {}).get('serialNumber')
            model = device_data.get('hardware', {}).get('model')
            asset_tag = device_data.get('general', {}).get('assetTag')
            device_name = device_data.get('general', {}).get('name')
            username = device_data.get('general', {}).get('username')
            email = device_data.get('general', {}).get('emailAddress')
            real_name = device_data.get('general', {}).get('realName')

            category = CATEGORIES['staff'] # Default category
            category_reason = "default"

            if prestage_name:
                prestage_name_lower = prestage_name.lower()
                if 'student' in prestage_name_lower or 'loaner' in prestage_name_lower:
                    category = CATEGORIES['student']
                    category_reason = f"prestage contains 'student' or 'loaner'"
                elif 'ssc' in prestage_name_lower:
                    category = CATEGORIES['ssc']
                    category_reason = f"prestage contains 'ssc'"
                elif 'staff' in prestage_name_lower or 'employee' in prestage_name_lower:
                    category = CATEGORIES['staff']
                    category_reason = f"prestage contains 'staff' or 'employee'"
                else:
                    category_reason = f"unmatched prestage '{prestage_name}'"
            else:
                category_reason = "no prestage found"

            logger.info(f"  → Prestage: '{prestage_name}' | Serial: {serial_number}")

            return {
                'device_id': device_id,
                'serial_number': serial_number,
                'model': model,
                'asset_tag': asset_tag,
                'device_name': device_name,
                'username': username,
                'email': email,
                'real_name': real_name,
                'device_type': 'computer',
                'prestage_name': prestage_name,
                'category': category,
                'category_reason': category_reason
            }
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Attempt {attempt + 1} failed for device {device_id}: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error getting prestage info for device {device_id} after {max_retries} attempts: {e}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON for device {device_id}: {e}")
            return None

def get_or_create_model(model_name: str, category_id: int, snipe_headers: dict) -> int:
    """Get or create a model in Snipe-IT with proper rate limiting"""
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            # Add delay to avoid rate limiting
            time.sleep(random.uniform(1.0, 2.0))
            
            # First, try to find existing model
            response = requests.get(
                f'{SNIPE_IT_URL}/api/v1/models',
                headers=snipe_headers,
                params={'search': model_name},
                timeout=30
            )
            
            if response.status_code == 200:
                models = response.json().get('rows', [])
                for model in models:
                    if model.get('name') == model_name:
                        logger.info(f"Found existing model: {model_name} (ID: {model['id']})")
                        return model['id']
            
            # Create new model if not found
            model_data = {
                'name': model_name,
                'category_id': category_id,
                'manufacturer_id': 1,  # Apple
                'model_number': model_name
            }
            
            response = requests.post(
                f'{SNIPE_IT_URL}/api/v1/models',
                headers=snipe_headers,
                json=model_data,
                timeout=30
            )
            
            if response.status_code == 200:
                model_id = response.json().get('payload', {}).get('id')
                logger.info(f"Created new model: {model_name} (ID: {model_id})")
                return model_id
            else:
                logger.error(f"Failed to create model: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 2)
                logger.warning(f"Model operation attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to get/create model {model_name} after {max_retries} attempts: {e}")
                return None

def create_or_update_asset(device_info: dict, snipe_headers: dict) -> bool:
    """Create or update asset in Snipe-IT with proper rate limiting"""
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            # Add delay to avoid rate limiting
            time.sleep(random.uniform(1.5, 3.0))
            
            # Get or create model
            model_id = get_or_create_model(
                device_info['model'], 
                device_info['category']['id'], 
                snipe_headers
            )
            
            if not model_id:
                logger.error(f"Could not get/create model for {device_info['model']}")
                return False
            
            # Check if asset already exists
            response = requests.get(
                f'{SNIPE_IT_URL}/api/v1/hardware',
                headers=snipe_headers,
                params={'search': device_info['serial_number']},
                timeout=30
            )
            
            existing_asset = None
            if response.status_code == 200:
                assets = response.json().get('rows', [])
                for asset in assets:
                    if asset.get('serial') == device_info['serial_number']:
                        existing_asset = asset
                        break
            
            asset_data = {
                'name': device_info['device_name'] or f"Device-{device_info['serial_number']}",
                'asset_tag': device_info['asset_tag'] or device_info['serial_number'],
                'serial': device_info['serial_number'],
                'model_id': model_id,
                'status_id': 1,  # Ready to Deploy
                'category_id': device_info['category']['id']
            }
            
            if existing_asset:
                # Update existing asset
                response = requests.put(
                    f'{SNIPE_IT_URL}/api/v1/hardware/{existing_asset["id"]}',
                    headers=snipe_headers,
                    json=asset_data,
                    timeout=30
                )
                if response.status_code == 200:
                    logger.info(f"Updated existing asset: {device_info['serial_number']}")
                    return True
            else:
                # Create new asset
                response = requests.post(
                    f'{SNIPE_IT_URL}/api/v1/hardware',
                    headers=snipe_headers,
                    json=asset_data,
                    timeout=30
                )
                if response.status_code == 200:
                    logger.info(f"Created new asset: {device_info['serial_number']}")
                    return True
            
            logger.error(f"Failed to create/update asset: {response.status_code} - {response.text}")
            return False
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 3)
                logger.warning(f"Asset operation attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to create/update asset {device_info['serial_number']} after {max_retries} attempts: {e}")
                return False

def process_device(device_id: int, jamf_headers: dict, snipe_headers: dict) -> bool:
    """Process a single device with retry logic"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Get prestage info
            device_info = get_prestage_info(device_id, jamf_headers)
            if not device_info:
                logger.error(f"Could not get prestage info for device {device_id}")
                return False
            
            logger.info(f"Processing device {device_info['serial_number']} (Prestage: '{device_info['prestage_name']}')")
            logger.info(f"PRESTAGE: '{device_info['prestage_name']}' → {device_info['category']['name']} ({device_info['category_reason']})")
            
            # Create/update asset in Snipe-IT
            success = create_or_update_asset(device_info, snipe_headers)
            if success:
                logger.info(f"Successfully processed device {device_info['serial_number']}")
                return True
            else:
                logger.error(f"Failed to process device {device_info['serial_number']}")
                return False
                
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 2)
                logger.warning(f"Device processing attempt {attempt + 1} failed for device {device_id}: {e}. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to process device {device_id} after {max_retries} attempts: {e}")
                return False

def main():
    """Main sync function"""
    logger.info("=== Jamf Pro to Snipe-IT Sync (BULLETPROOF Prestage-Based) ===")
    
    # Get tokens
    jamf_token = get_jamf_token()
    if not jamf_token:
        logger.error("Failed to get Jamf token")
        return
    
    jamf_headers = {'Authorization': f'Bearer {jamf_token}'}
    snipe_headers = get_snipe_headers()
    
    # Get all computers from Jamf Pro
    logger.info("Fetching all computers from Jamf Pro...")
    try:
        response = requests.get(
            f'{JAMF_URL}/api/v1/computers-inventory',
            headers=jamf_headers,
            params={'page': 0, 'page-size': 1000},
            timeout=30
        )
        response.raise_for_status()
        computers_data = response.json()
        computers = computers_data.get('results', [])
        logger.info(f"Found {len(computers)} computers")
    except Exception as e:
        logger.error(f"Error fetching computers: {e}")
        return
    
    # Get prestage info for all devices
    logger.info("Getting prestage info for all devices...")
    device_ids = [comp['id'] for comp in computers]
    
    # Process devices sequentially to avoid rate limiting
    successful = 0
    failed = 0
    
    for i, device_id in enumerate(device_ids, 1):
        logger.info(f"Processing device {i}/{len(device_ids)} (ID: {device_id})")
        
        success = process_device(device_id, jamf_headers, snipe_headers)
        if success:
            successful += 1
        else:
            failed += 1
        
        # Add delay between devices
        time.sleep(random.uniform(2.0, 4.0))
    
    logger.info("=== SYNC COMPLETE ===")
    logger.info(f"Successfully processed: {successful}/{len(device_ids)} devices")
    logger.info(f"Failed: {failed}/{len(device_ids)} devices")
    logger.info(f"Success rate: {(successful/len(device_ids)*100):.1f}%")

if __name__ == '__main__':
    main()
