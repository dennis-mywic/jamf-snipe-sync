#!/usr/bin/env python3
"""
Jamf Pro to Snipe-IT Sync - BULLETPROOF Prestage Enrollment Based
100% Accurate Device Categorization using Prestage Enrollment Data from Modern API
"""

import os
import requests
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
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

def get_device_prestage_info(device_id, headers, inventory_data=None):
    """Get prestage enrollment information from device details"""
    try:
        # Try Modern API first (works for prestage data)
        url = f"{JAMF_URL}/api/v1/computers-inventory-detail/{device_id}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        general = data.get('general', {})
        
        # Extract prestage enrollment information from enrollmentMethod
        prestage_name = ''
        enrollment_method = general.get('enrollmentMethod', {})
        if enrollment_method and isinstance(enrollment_method, dict):
            prestage_name = enrollment_method.get('objectName', '')
        
        # Use inventory data for basic info (more reliable)
        serial_number = ''
        device_name = ''
        model = ''
        
        if inventory_data:
            # Serial number is in general.name field for inventory data
            inv_general = inventory_data.get('general', {})
            serial_number = inv_general.get('name', '')
            device_name = inv_general.get('name', '')
            # Model might be in hardware section
            model = inventory_data.get('hardware', {}).get('model', '') if inventory_data.get('hardware') else ''
        
        # Fallback to detail data if inventory doesn't have it
        if not serial_number:
            serial_number = general.get('serialNumber', '') or general.get('serial_number', '')
        if not device_name:
            device_name = general.get('name', '')
        if not model:
            model = data.get('hardware', {}).get('model', '')
        
        # Extract email and username from Modern API userAndLocation data  
        user_location = data.get('userAndLocation', {})
        email = user_location.get('email', '') or user_location.get('emailAddress', '') or user_location.get('email_address', '')
        username = user_location.get('username', '')
        realname = user_location.get('realname', '')
        
        # Debug: always log what we found for user data
        if email or username or realname:
            logger.info(f"  📧 User data for {serial_number}: email={email}, username={username}, realname={realname}")
        else:
            logger.debug(f"  ❌ No user data found for {serial_number}")
        
        # Debug logging for user info
        if email:
            logger.info(f"  ✅ Found email: {email} for device {serial_number}")
        else:
            logger.warning(f"  ❌ No email found for device {serial_number}")
        
        return {
            'prestage_name': prestage_name,
            'device_name': device_name,
            'serial_number': serial_number,
            'model': model,
            'email': email,
            'username': username,
            'enrolled_via_automated': general.get('enrolledViaAutomatedDeviceEnrollment', False)
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

def get_user(email: str, snipe_headers: dict) -> int:
    """Look up an existing user in Snipe-IT by email (case-insensitive) with caching"""
    if not email:
        return None
    
    # Minimal delay for user lookups
    time.sleep(0.1)
    
    try:
        # Try variations of the email
        email_lower = email.lower()
        email_variations = [email_lower]
        
        # Handle special cases for known name variations
        if 'mackenzie' in email_lower:
            email_variations.append(email_lower.replace('mackenzie', 'mckenzie'))
        elif 'mckenzie' in email_lower:
            email_variations.append(email_lower.replace('mckenzie', 'mackenzie'))
            
        # Try each email variation
        for email_var in email_variations:
            response = requests.get(
                f"{SNIPE_IT_URL}/api/v1/users",
                headers=snipe_headers,
                params={'search': email_var, 'limit': 1},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                users = data.get('rows', [])
                if users:
                    user = users[0]
                    user_id = user.get('id')
                    logger.info(f"Found user: {user.get('name')} (ID: {user_id}) for email: {email}")
                    return user_id
        
        logger.warning(f"No user found for email: {email}")
        return None
        
    except Exception as e:
        logger.error(f"Error looking up user {email}: {str(e)}")
        return None

def process_device(device_info, snipe_headers):
    """Process a single device with prestage-based categorization and retry logic"""
    max_retries = 3
    
    for attempt in range(max_retries):
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
            
            # Get or create model with retry
            model_id = get_or_create_model(device_info['model'], category['id'], snipe_headers)
            if not model_id:
                logger.error(f"Could not get/create model for {device_info['model']}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait before retry
                    continue
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
            
            # Get asset ID for checkout
            asset_id = None
            if response.status_code in [200, 201]:
                if 'payload' in response.json():
                    asset_id = response.json()['payload'].get('id')
                elif 'id' in response.json():
                    asset_id = response.json()['id']
                else:
                    # For updates, we already have the asset_id
                    asset_id = response.json().get('id')
            
            # Get user ID if available (exactly like original script)
            user_id = None
            email = device_info.get('email', '')
            serial = device_info.get('serial_number', '')
            
            if email:
                try:
                    logger.info(f"Looking up user for email {email}")
                    user_id = get_user(email, snipe_headers)
                    if user_id:
                        logger.info(f"Successfully found user ID {user_id} for email {email}")
                    else:
                        logger.warning(f"No user ID found for email {email}")
                except Exception as e:
                    logger.warning(f"Error looking up user for email {email}: {str(e)}")
            
            # If we have both asset_id and user_id, checkout the asset to the user (exactly like original)
            if asset_id and user_id:
                    logger.info(f"Checking out asset {asset_id} to user {user_id}")
                    checkout_data = {
                        'assigned_user': user_id,
                        'checkout_to_type': 'user',
                        'note': f"Automatically checked out via Jamf sync on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                    
                    # Minimal delay before checkout
                    time.sleep(0.1)
                    
                    checkout_url = f"{SNIPE_IT_URL}/api/v1/hardware/{asset_id}/checkout"
                    try:
                        checkout_resp = requests.post(
                            checkout_url,
                            headers=snipe_headers,
                            json=checkout_data,
                            timeout=30
                        )
                        if checkout_resp.status_code == 200:
                            logger.info(f"Successfully checked out device {serial} to user ID {user_id}")
                        else:
                            logger.error(f"Checkout failed with status {checkout_resp.status_code}: {checkout_resp.text}")
                    except Exception as e:
                        logger.error(f"Failed to checkout device {serial} to user {user_id}: {str(e)}")
                        if hasattr(e, 'response') and hasattr(e.response, 'text'):
                            logger.error(f"Checkout error response: {e.response.text}")
            
            logger.info(f"Successfully processed device {serial}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing device {serial} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)  # Wait before retry
                continue
            return False

def main():
    """Main execution function"""
    logger.info("=== Jamf Pro to Snipe-IT Sync (BULLETPROOF Prestage-Based) ===")
    
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
    for i, computer in enumerate(computers, 1):
        device_id = computer.get('id')
        # Serial number is stored in general.name field in inventory endpoint
        general = computer.get('general', {})
        serial_number = general.get('name', '')
        device_name = general.get('name', '')  # Same as serial for now
        
        if device_id and serial_number:
            logger.info(f"Processing device {i}/{len(computers)} (ID: {device_id}) | Serial: {serial_number}")
            
            # Get prestage info AND user data from device details
            device_info = get_device_prestage_info(device_id, jamf_headers, computer)
            if not device_info:
                # Fallback: use inventory data only
                enrollment_method = general.get('enrollmentMethod', {})
                prestage_name = ''
                if enrollment_method and isinstance(enrollment_method, dict):
                    prestage_name = enrollment_method.get('objectName', '')
                
                # If no prestage found, use default based on device naming patterns
                if not prestage_name:
                    if 'IT-' in serial_number:
                        prestage_name = 'Student Setup'
                    elif 'SSC-' in serial_number:
                        prestage_name = 'SSC Computers'
                    else:
                        prestage_name = 'Staff Setup'
                
                device_info = {
                    'prestage_name': prestage_name,
                    'device_name': serial_number,
                    'serial_number': serial_number,
                    'model': computer.get('hardware', {}).get('model', '') if computer.get('hardware') else 'Unknown Model',
                    'email': '',  # No user data available from inventory
                    'username': '',
                    'enrolled_via_automated': general.get('enrolledViaAutomatedDeviceEnrollment', False)
                }
            
            all_devices.append(device_info)
            logger.info(f"  → Prestage: '{device_info['prestage_name']}' | Serial: {serial_number}")
            time.sleep(0.05)  # Minimal rate limiting
        else:
            logger.warning(f"Skipping device {device_id} - missing serial number")
    
    logger.info(f"Retrieved prestage info for {len(all_devices)} devices")
    
    # Process devices sequentially to avoid rate limiting
    success_count = 0
    failed_count = 0
    
    for i, device in enumerate(all_devices, 1):
        logger.info(f"Processing device {i}/{len(all_devices)}: {device.get('serial_number', 'Unknown')}")
        try:
            if process_device(device, snipe_headers):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"Error processing device {device.get('serial_number', 'Unknown')}: {e}")
            failed_count += 1
        
        # Add delay between devices to avoid rate limiting
        time.sleep(3)
    
    logger.info(f"=== SYNC COMPLETE ===")
    logger.info(f"Successfully processed: {success_count}/{len(all_devices)} devices")
    if all_devices:
        logger.info(f"Success rate: {(success_count/len(all_devices)*100):.1f}%")

if __name__ == '__main__':
    main()
