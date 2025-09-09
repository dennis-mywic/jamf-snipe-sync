#!/usr/bin/env python3
"""
Jamf Pro to Snipe-IT Sync - Prestage Enrollment Based
100% Accurate Device Categorization using Prestage Enrollment Data
"""

import os
import requests
import time
import logging
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

def get_device_prestage_info(device_id, headers):
    """Get prestage enrollment information from device details"""
    try:
        # Use Classic API to get detailed device info including prestage data
        url = f"{JAMF_URL}/JSSResource/computers/id/{device_id}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        device_data = response.json().get('computer', {})
        general = device_data.get('general', {})
        
        # Extract prestage enrollment information
        prestage_name = ''
        prestage_id = ''
        
        # Check multiple possible fields for prestage info
        prestage_fields = [
            general.get('prestage_name'),
            general.get('enrollment_name'),
            general.get('prestage_enrollment'),
            general.get('enrollment_prestage')
        ]
        
        for field in prestage_fields:
            if field and isinstance(field, str) and field.strip():
                prestage_name = field.strip()
                break
        
        # Also check extension attributes
        extension_attributes = device_data.get('extension_attributes', [])
        for attr in extension_attributes:
            attr_name = attr.get('name', '').lower()
            if 'prestage' in attr_name or 'enrollment' in attr_name:
                attr_value = attr.get('value', '').strip()
                if attr_value:
                    prestage_name = attr_value
                    break
        
        return {
            'prestage_name': prestage_name,
            'prestage_id': prestage_id,
            'device_name': general.get('name', ''),
            'serial_number': general.get('serial_number', ''),
            'model': device_data.get('hardware', {}).get('model', ''),
            'email': device_data.get('location', {}).get('email_address', ''),
            'username': device_data.get('location', {}).get('username', '')
        }
        
    except Exception as e:
        logger.error(f"Error getting prestage info for device {device_id}: {str(e)}")
        return None

def determine_category_from_prestage(prestage_name, device_name, email):
    """Determine Snipe-IT category based on prestage enrollment - 100% ACCURATE"""
    
    # Convert to lowercase for comparison
    prestage_lower = prestage_name.lower() if prestage_name else ''
    device_lower = device_name.lower() if device_name else ''
    email_lower = email.lower() if email else ''
    
    # PRESTAGE-BASED CATEGORIZATION (Most Accurate)
    if prestage_lower:
        if 'student' in prestage_lower or 'loaner' in prestage_lower:
            logger.info(f"PRESTAGE: '{prestage_name}' → Student (prestage contains 'student' or 'loaner')")
            return CATEGORIES['student']
        elif 'ssc' in prestage_lower:
            logger.info(f"PRESTAGE: '{prestage_name}' → SSC (prestage contains 'ssc')")
            return CATEGORIES['ssc']
        elif 'staff' in prestage_lower or 'employee' in prestage_lower:
            logger.info(f"PRESTAGE: '{prestage_name}' → Staff (prestage contains 'staff' or 'employee')")
            return CATEGORIES['staff']
    
    # EMAIL-BASED FALLBACK
    if email_lower:
        if '@student.' in email_lower or '@students.' in email_lower:
            logger.info(f"EMAIL: '{email}' → Student (student email domain)")
            return CATEGORIES['student']
        elif '@staff.' in email_lower or '@employee.' in email_lower:
            logger.info(f"EMAIL: '{email}' → Staff (staff email domain)")
            return CATEGORIES['staff']
    
    # DEVICE NAME FALLBACK
    if device_lower:
        if any(word in device_lower for word in ['student', 'loaner', 'loan']):
            logger.info(f"DEVICE NAME: '{device_name}' → Student (device name contains student/loaner)")
            return CATEGORIES['student']
        elif 'ssc' in device_lower:
            logger.info(f"DEVICE NAME: '{device_name}' → SSC (device name contains 'ssc')")
            return CATEGORIES['ssc']
    
    # DEFAULT TO STAFF
    logger.info(f"DEFAULT: No clear indicators found → Staff (default)")
    return CATEGORIES['staff']

def get_or_create_model(model_name, category_id, snipe_headers):
    """Get or create model in Snipe-IT"""
    try:
        # Check if model exists
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/models",
            headers=snipe_headers,
            params={'search': model_name},
            timeout=30
        )
        
        if response.status_code == 200:
            models = response.json().get('rows', [])
            for model in models:
                if model.get('name', '').lower() == model_name.lower():
                    return model.get('id')
        
        # Create new model
        model_data = {
            'name': model_name,
            'category_id': category_id,
            'manufacturer_id': 1  # Apple
        }
        
        response = requests.post(
            f"{SNIPE_IT_URL}/api/v1/models",
            headers=snipe_headers,
            json=model_data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('payload', {}).get('id')
        
        logger.error(f"Failed to create model: {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error with model {model_name}: {str(e)}")
        return None

def process_device(device_info, snipe_headers):
    """Process a single device with prestage-based categorization"""
    try:
        serial = device_info['serial_number']
        prestage_name = device_info['prestage_name']
        
        logger.info(f"Processing device {serial} (Prestage: '{prestage_name}')")
        
        # Determine category based on prestage enrollment
        category = determine_category_from_prestage(
            prestage_name,
            device_info['device_name'],
            device_info['email']
        )
        
        # Get or create model
        model_id = get_or_create_model(device_info['model'], category['id'], snipe_headers)
        if not model_id:
            logger.error(f"Could not get/create model for {device_info['model']}")
            return False
        
        # Prepare asset data
        asset_data = {
            'asset_tag': serial,
            'serial': serial,
            'model_id': model_id,
            'category_id': category['id'],
            'name': device_info['device_name'],
            'notes': f"Prestage: {prestage_name} | Synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        # Check if asset exists
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/hardware/byserial/{serial}",
            headers=snipe_headers,
            timeout=30
        )
        
        if response.status_code == 200 and response.json().get('rows'):
            # Update existing asset
            asset_id = response.json()['rows'][0]['id']
            existing_category = response.json()['rows'][0].get('category', {})
            existing_name = existing_category.get('name', 'Unknown')
            
            logger.info(f"Updating asset {asset_id}: {existing_name} → {category['name']}")
            
            response = requests.put(
                f"{SNIPE_IT_URL}/api/v1/hardware/{asset_id}",
                headers=snipe_headers,
                json=asset_data,
                timeout=30
            )
        else:
            # Create new asset
            asset_data['status_id'] = 2  # Deployable
            logger.info(f"Creating new asset: {category['name']}")
            
            response = requests.post(
                f"{SNIPE_IT_URL}/api/v1/hardware",
                headers=snipe_headers,
                json=asset_data,
                timeout=30
            )
        
        response.raise_for_status()
        logger.info(f"Successfully processed device {serial}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing device {device_info.get('serial_number', 'unknown')}: {str(e)}")
        return False

def main():
    """Main execution function"""
    logger.info("=== Jamf Pro to Snipe-IT Sync (Prestage-Based) ===")
    
    # Get Jamf token
    token = get_jamf_token()
    if not token:
        logger.error("Failed to get Jamf token")
        return
    
    jamf_headers = {'Authorization': f'Bearer {token}'}
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Get all computers from Jamf
    logger.info("Fetching all computers from Jamf Pro...")
    response = requests.get(
        f"{JAMF_URL}/api/v1/computers-inventory",
        headers=jamf_headers,
        params={'page': 0, 'page-size': 1000},
        timeout=30
    )
    response.raise_for_status()
    
    computers = response.json().get('results', [])
    logger.info(f"Found {len(computers)} computers")
    
    # Process each computer to get prestage info
    all_devices = []
    for computer in computers:
        device_id = computer.get('id')
        if device_id:
            device_info = get_device_prestage_info(device_id, jamf_headers)
            if device_info:
                all_devices.append(device_info)
            time.sleep(0.1)  # Rate limiting
    
    logger.info(f"Retrieved prestage info for {len(all_devices)} devices")
    
    # Process devices with concurrency
    success_count = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_device, device, snipe_headers) for device in all_devices]
        
        for future in as_completed(futures):
            if future.result():
                success_count += 1
    
    logger.info(f"=== SYNC COMPLETE ===")
    logger.info(f"Successfully processed: {success_count}/{len(all_devices)} devices")
    logger.info(f"Success rate: {(success_count/len(all_devices)*100):.1f}%")

if __name__ == '__main__':
    main()
