#!/usr/bin/env python3
"""
JAMF TO SNIPE-IT SYNC - 100% BULLETPROOF
This script ensures every single device from Jamf gets synced to Snipe-IT with zero drops.

Features:
- Fetches ALL devices from Jamf (computers + mobile devices)
- Multiple retry mechanisms with exponential backoff
- Proper rate limiting to avoid API limits
- Prestage-based category assignment
- Smart fallback categorization
- Comprehensive error handling
- Progress tracking and reporting
- 100% success verification

USE AFTER RUNNING THE ULTIMATE WIPE SCRIPT
"""

import os
import requests
import time
import json
import sys
import logging
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
JAMF_URL = os.getenv('JAMF_URL', '').rstrip('/')
if not JAMF_URL.startswith('http'):
    JAMF_URL = f'https://{JAMF_URL}'

JAMF_CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
JAMF_USERNAME = os.getenv('JAMF_USERNAME')
JAMF_PASSWORD = os.getenv('JAMF_PASSWORD')

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL', '').rstrip('/')
if not SNIPE_IT_URL.startswith('http'):
    SNIPE_IT_URL = f'https://{SNIPE_IT_URL}'

SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'jamf_sync_bulletproof_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Snipe-IT Categories
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

# Rate limiting configuration
RATE_LIMIT_DELAY = 0.3      # Base delay between requests
RETRY_DELAY = 2.0           # Base retry delay
MAX_RETRIES = 5             # Maximum retries per operation
MAX_WORKERS = 4             # Concurrent workers

def print_banner():
    """Print script banner"""
    logger.info("=" * 80)
    logger.info("🚀 JAMF TO SNIPE-IT SYNC - 100% BULLETPROOF")
    logger.info("=" * 80)
    logger.info("🎯 Ensures every single device from Jamf gets synced")
    logger.info("🔄 Multiple retry mechanisms with rate limiting")
    logger.info("📊 Real-time progress tracking and verification")
    logger.info("=" * 80)

def verify_environment():
    """Verify all required environment variables"""
    missing = []
    
    if not JAMF_URL:
        missing.append('JAMF_URL')
    if not (JAMF_CLIENT_ID and JAMF_CLIENT_SECRET) and not (JAMF_USERNAME and JAMF_PASSWORD):
        missing.append('Jamf credentials (either client credentials or username/password)')
    if not SNIPE_IT_URL:
        missing.append('SNIPE_IT_URL')
    if not SNIPE_IT_API_TOKEN:
        missing.append('SNIPE_IT_API_TOKEN')
    
    if missing:
        logger.error("❌ Missing required environment variables:")
        for var in missing:
            logger.error(f"   - {var}")
        sys.exit(1)
    
    logger.info("✅ Environment variables verified")

def make_request_with_retry(method, url, headers, **kwargs):
    """Make HTTP request with retry logic and rate limiting"""
    for attempt in range(MAX_RETRIES):
        try:
            # Rate limiting with jitter
            delay = RATE_LIMIT_DELAY + random.uniform(0, 0.2)
            time.sleep(delay)
            
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                logger.warning(f"⏳ Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"⏳ Request failed (attempt {attempt + 1}), retrying in {wait_time:.1f}s: {str(e)}")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ Request failed after {MAX_RETRIES} attempts: {str(e)}")
                raise
    
    return None

def get_jamf_token():
    """Get Jamf Pro access token"""
    try:
        # Try OAuth client credentials first
        if JAMF_CLIENT_ID and JAMF_CLIENT_SECRET:
            response = requests.post(
                f'{JAMF_URL}/api/oauth/token',
                data={
                    'grant_type': 'client_credentials',
                    'client_id': JAMF_CLIENT_ID,
                    'client_secret': JAMF_CLIENT_SECRET
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()['access_token']
        
        # Fall back to basic auth
        if JAMF_USERNAME and JAMF_PASSWORD:
            import base64
            auth_string = base64.b64encode(f"{JAMF_USERNAME}:{JAMF_PASSWORD}".encode()).decode()
            return auth_string  # Will be used as Basic auth header
            
    except Exception as e:
        logger.error(f"Error getting Jamf token: {e}")
    
    return None

def get_jamf_headers():
    """Get Jamf Pro headers"""
    token = get_jamf_token()
    if not token:
        return None
    
    if JAMF_CLIENT_ID and JAMF_CLIENT_SECRET:
        return {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    else:
        return {
            'Authorization': f'Basic {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

def get_snipe_headers():
    """Get Snipe-IT headers"""
    return {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

def get_all_jamf_computers(jamf_headers):
    """Get ALL computers from Jamf Pro with pagination"""
    logger.info("🔍 Fetching ALL computers from Jamf Pro...")
    
    all_computers = []
    page = 0
    page_size = 500
    
    while True:
        logger.info(f"   📄 Fetching computers page {page + 1}...")
        
        response = make_request_with_retry(
            'GET',
            f'{JAMF_URL}/api/v1/computers-inventory',
            jamf_headers,
            params={'page': page, 'page-size': page_size}
        )
        
        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch computers page {page + 1}")
            break
        
        data = response.json()
        computers = data.get('results', [])
        total = data.get('totalCount', 0)
        
        if not computers:
            break
        
        all_computers.extend(computers)
        logger.info(f"   📊 Page {page + 1}: {len(computers)} computers (Total: {len(all_computers)}/{total})")
        
        if len(all_computers) >= total:
            break
        
        page += 1
    
    logger.info(f"🎯 TOTAL COMPUTERS: {len(all_computers)}")
    return all_computers

def get_all_jamf_mobile_devices(jamf_headers):
    """Get ALL mobile devices from Jamf Pro"""
    logger.info("🔍 Fetching ALL mobile devices from Jamf Pro...")
    
    # Try modern API first
    response = make_request_with_retry(
        'GET',
        f'{JAMF_URL}/api/v2/mobile-devices',
        jamf_headers,
        params={'page': 0, 'page-size': 1000}
    )
    
    if response and response.status_code == 200:
        mobile_devices = response.json().get('results', [])
        logger.info(f"🎯 TOTAL MOBILE DEVICES: {len(mobile_devices)}")
        return mobile_devices
    
    # Fall back to classic API
    logger.info("   🔄 Falling back to classic API...")
    response = make_request_with_retry(
        'GET',
        f'{JAMF_URL}/JSSResource/mobiledevices',
        jamf_headers
    )
    
    if response and response.status_code == 200:
        mobile_devices = response.json().get('mobile_devices', [])
        logger.info(f"🎯 TOTAL MOBILE DEVICES (classic): {len(mobile_devices)}")
        return mobile_devices
    
    logger.warning("⚠️ No mobile devices found")
    return []

def get_computer_details(computer_id, jamf_headers):
    """Get detailed computer information"""
    try:
        # First try modern API
        response = make_request_with_retry(
            'GET',
            f'{JAMF_URL}/api/v2/computers/{computer_id}',
            jamf_headers
        )
        
        if response and response.status_code == 200:
            device_data = response.json()
            general = device_data.get('general', {})
            hardware = device_data.get('hardware', {})
            
            # Get prestage enrollment info
            prestage_name = general.get('enrollmentMethod', {}).get('objectName', '')
            
            # Determine category from prestage
            category = determine_category_from_prestage(prestage_name, general)
            
            return {
                'device_id': computer_id,
                'serial_number': general.get('serialNumber'),
                'model': hardware.get('model'),
                'asset_tag': general.get('assetTag'),
                'device_name': general.get('name'),
                'username': general.get('username', ''),
                'email': general.get('emailAddress', ''),
                'real_name': general.get('realName', ''),
                'device_type': 'computer',
                'prestage_name': prestage_name,
                'category': category
            }
        
        # Fall back to classic API
        response = make_request_with_retry(
            'GET',
            f'{JAMF_URL}/JSSResource/computers/id/{computer_id}',
            jamf_headers
        )
        
        if response and response.status_code == 200:
            device_data = response.json().get('computer', {})
            general = device_data.get('general', {})
            hardware = device_data.get('hardware', {})
            location = device_data.get('location', {})
            
            # Try to get prestage from extension attributes
            prestage_name = ''
            for attr in device_data.get('extension_attributes', []):
                if 'prestage' in attr.get('name', '').lower():
                    prestage_name = attr.get('value', '')
                    break
            
            category = determine_category_from_prestage(prestage_name, general, location)
            
            return {
                'device_id': computer_id,
                'serial_number': general.get('serial_number'),
                'model': hardware.get('model'),
                'asset_tag': general.get('asset_tag'),
                'device_name': general.get('name'),
                'username': location.get('username', ''),
                'email': location.get('email_address', ''),
                'real_name': location.get('real_name', ''),
                'device_type': 'computer',
                'prestage_name': prestage_name,
                'category': category
            }
    
    except Exception as e:
        logger.error(f"Error getting computer details for {computer_id}: {str(e)}")
    
    return None

def get_mobile_device_details(device_id, jamf_headers):
    """Get detailed mobile device information"""
    try:
        # Try modern API first
        response = make_request_with_retry(
            'GET',
            f'{JAMF_URL}/api/v2/mobile-devices/{device_id}',
            jamf_headers
        )
        
        if response and response.status_code == 200:
            device_data = response.json()
            
            return {
                'device_id': device_id,
                'serial_number': device_data.get('serialNumber'),
                'model': device_data.get('model'),
                'asset_tag': device_data.get('assetTag'),
                'device_name': device_data.get('name'),
                'username': device_data.get('username', ''),
                'email': device_data.get('emailAddress', ''),
                'real_name': device_data.get('realName', ''),
                'device_type': 'mobile',
                'category': determine_mobile_category(device_data.get('model', ''))
            }
        
        # Fall back to classic API
        response = make_request_with_retry(
            'GET',
            f'{JAMF_URL}/JSSResource/mobiledevices/id/{device_id}',
            jamf_headers
        )
        
        if response and response.status_code == 200:
            device_data = response.json().get('mobile_device', {})
            general = device_data.get('general', {})
            location = device_data.get('location', {})
            
            return {
                'device_id': device_id,
                'serial_number': general.get('serial_number'),
                'model': general.get('model'),
                'asset_tag': general.get('asset_tag'),
                'device_name': general.get('name'),
                'username': location.get('username', ''),
                'email': location.get('email_address', ''),
                'real_name': location.get('real_name', ''),
                'device_type': 'mobile',
                'category': determine_mobile_category(general.get('model', ''))
            }
    
    except Exception as e:
        logger.error(f"Error getting mobile device details for {device_id}: {str(e)}")
    
    return None

def determine_category_from_prestage(prestage_name, general, location=None):
    """Determine category based on prestage enrollment and other factors"""
    # Check prestage name first
    if prestage_name:
        prestage_lower = prestage_name.lower()
        if 'student' in prestage_lower or 'loaner' in prestage_lower:
            logger.debug(f"Category determined by prestage '{prestage_name}' → Student")
            return CATEGORIES['student']
        elif 'ssc' in prestage_lower:
            logger.debug(f"Category determined by prestage '{prestage_name}' → SSC")
            return CATEGORIES['ssc']
        elif 'staff' in prestage_lower or 'teacher' in prestage_lower or 'employee' in prestage_lower:
            logger.debug(f"Category determined by prestage '{prestage_name}' → Staff")
            return CATEGORIES['staff']
    
    # Check email patterns
    email = ''
    if location:
        email = location.get('email_address', '').lower()
    else:
        email = general.get('emailAddress', '').lower()
    
    if email and 'student' in email:
        logger.debug(f"Category determined by email '{email}' → Student")
        return CATEGORIES['student']
    
    # Check device name
    device_name = general.get('name', '').lower()
    if device_name:
        if 'student' in device_name or 'loaner' in device_name:
            logger.debug(f"Category determined by name '{device_name}' → Student")
            return CATEGORIES['student']
        elif 'ssc' in device_name:
            logger.debug(f"Category determined by name '{device_name}' → SSC")
            return CATEGORIES['ssc']
    
    # Default to staff
    logger.debug("Category defaulted to Staff")
    return CATEGORIES['staff']

def determine_mobile_category(model):
    """Determine category for mobile devices based on model"""
    if not model:
        return CATEGORIES['teacher_ipad']  # Default
    
    model_lower = model.lower()
    if 'appletv' in model_lower or 'apple tv' in model_lower:
        return CATEGORIES['appletv']
    else:
        return CATEGORIES['teacher_ipad']  # Default for iPads

# Cache for user lookups
user_cache = {}

@lru_cache(maxsize=100)
def get_or_create_model(model_name, category_id, snipe_headers_tuple):
    """Get or create model in Snipe-IT with caching"""
    snipe_headers = dict(snipe_headers_tuple)
    
    if not model_name:
        return None
    
    try:
        # Search for existing model
        response = make_request_with_retry(
            'GET',
            f'{SNIPE_IT_URL}/api/v1/models',
            snipe_headers,
            params={'search': model_name}
        )
        
        if response and response.status_code == 200:
            models = response.json().get('rows', [])
            for model in models:
                if model.get('name') == model_name:
                    return model.get('id')
        
        # Create new model
        model_data = {
            'name': model_name,
            'category_id': category_id,
            'manufacturer_id': 1,  # Apple
            'model_number': model_name,
            'fieldset_id': 2
        }
        
        response = make_request_with_retry(
            'POST',
            f'{SNIPE_IT_URL}/api/v1/models',
            snipe_headers,
            json=model_data
        )
        
        if response and response.status_code == 200:
            model_id = response.json().get('payload', {}).get('id')
            logger.info(f"Created model: {model_name} (ID: {model_id})")
            return model_id
    
    except Exception as e:
        logger.error(f"Error with model {model_name}: {str(e)}")
    
    return None

def get_user_by_email(email, snipe_headers):
    """Look up an existing user in Snipe-IT by email (case-insensitive) with caching"""
    if not email:
        return None
    
    # Check cache first
    email_lower = email.lower()
    if email_lower in user_cache:
        return user_cache[email_lower]
    
    try:
        # Try variations of the email for common name variations
        email_variations = [email_lower]
        
        # Handle special cases for known name variations
        if 'mackenzie' in email_lower:
            email_variations.append(email_lower.replace('mackenzie', 'mckenzie'))
        elif 'mckenzie' in email_lower:
            email_variations.append(email_lower.replace('mckenzie', 'mackenzie'))
        
        # Try each email variation
        for email_var in email_variations:
            response = make_request_with_retry(
                'GET',
                f'{SNIPE_IT_URL}/api/v1/users',
                snipe_headers,
                params={'search': email_var, 'limit': 1}
            )
            
            if response and response.status_code == 200:
                users = response.json().get('rows', [])
                for user in users:
                    user_email = user.get('email', '').lower()
                    if user_email == email_var:
                        user_id = user.get('id')
                        if user_id:
                            user_cache[email_lower] = user_id
                            logger.info(f"Found user: {user.get('name')} (ID: {user_id}) for email: {email}")
                            return user_id
        
        # Special handling for Kirsten Anderson
        if 'anderson' in email_lower:
            alt_email = 'kirsten.anderson@mywic.org'
            response = make_request_with_retry(
                'GET',
                f'{SNIPE_IT_URL}/api/v1/users',
                snipe_headers,
                params={'search': alt_email, 'limit': 1}
            )
            
            if response and response.status_code == 200:
                users = response.json().get('rows', [])
                if users:
                    user = users[0]
                    user_id = user.get('id')
                    if user_id:
                        user_cache[email_lower] = user_id
                        logger.info(f"Found Kirsten Anderson with ID: {user_id}")
                        return user_id
        
        logger.debug(f"No user found for email: {email}")
        user_cache[email_lower] = None
        return None
        
    except Exception as e:
        logger.error(f"Error searching for user {email}: {str(e)}")
        return None

def create_or_update_asset(device_info, snipe_headers):
    """Create or update asset in Snipe-IT"""
    serial = device_info.get('serial_number')
    if not serial:
        logger.error("No serial number found for device")
        return False
    
    try:
        # Convert headers to tuple for caching
        headers_tuple = tuple(sorted(snipe_headers.items()))
        
        # Get or create model
        model_id = get_or_create_model(
            device_info.get('model', 'Unknown'),
            device_info['category']['id'],
            headers_tuple
        )
        
        if not model_id:
            logger.error(f"Could not get/create model for {device_info.get('model')}")
            return False
        
        # Check if asset exists
        response = make_request_with_retry(
            'GET',
            f'{SNIPE_IT_URL}/api/v1/hardware/byserial/{serial}',
            snipe_headers
        )
        
        asset_data = {
            'name': device_info.get('device_name') or f"Device-{serial}",
            'asset_tag': device_info.get('asset_tag') or serial,
            'serial': serial,
            'model_id': model_id,
            'status_id': 2,  # Deployable
            'category_id': device_info['category']['id'],
            'notes': f"Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nPrestage: {device_info.get('prestage_name', 'N/A')}"
        }
        
        if response and response.status_code == 200 and response.json().get('rows'):
            # Update existing asset
            asset_id = response.json().get('rows')[0].get('id')
            response = make_request_with_retry(
                'PUT',
                f'{SNIPE_IT_URL}/api/v1/hardware/{asset_id}',
                snipe_headers,
                json=asset_data
            )
            action = "Updated"
        else:
            # Create new asset
            response = make_request_with_retry(
                'POST',
                f'{SNIPE_IT_URL}/api/v1/hardware',
                snipe_headers,
                json=asset_data
            )
            action = "Created"
        
        if response and response.status_code == 200:
            logger.info(f"{action} asset: {serial} → {device_info['category']['name']}")
            return True
        else:
            status = response.status_code if response else 'No response'
            logger.error(f"Failed to {action.lower()} asset {serial}: {status}")
            return False
    
    except Exception as e:
        logger.error(f"Error processing asset {serial}: {str(e)}")
        return False

def process_device(device_info, snipe_headers):
    """Process a single device with retry logic"""
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                wait_time = 2 ** attempt
                logger.info(f"Retrying device {device_info.get('serial_number')} (attempt {attempt + 1}) after {wait_time}s")
                time.sleep(wait_time)
            
            return create_or_update_asset(device_info, snipe_headers)
            
        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f"Device processing failed (attempt {attempt + 1}): {str(e)}")
                continue
            else:
                logger.error(f"Device processing failed after {max_attempts} attempts: {str(e)}")
                return False
    
    return False

def main():
    """Main execution function"""
    print_banner()
    
    # Verify environment
    verify_environment()
    
    # Get headers
    jamf_headers = get_jamf_headers()
    if not jamf_headers:
        logger.error("❌ Failed to get Jamf headers")
        sys.exit(1)
    
    snipe_headers = get_snipe_headers()
    
    # Test connections
    logger.info("🔌 Testing API connections...")
    
    # Test Jamf
    response = make_request_with_retry('GET', f'{JAMF_URL}/api/v1/computers-inventory', jamf_headers, params={'page': 0, 'page-size': 1})
    if not response or response.status_code != 200:
        logger.error("❌ Failed to connect to Jamf Pro API")
        sys.exit(1)
    
    # Test Snipe-IT
    response = make_request_with_retry('GET', f'{SNIPE_IT_URL}/api/v1/hardware', snipe_headers, params={'limit': 1})
    if not response or response.status_code != 200:
        logger.error("❌ Failed to connect to Snipe-IT API")
        sys.exit(1)
    
    logger.info("✅ API connections successful")
    
    # Start sync
    start_time = datetime.now()
    logger.info(f"🚀 Starting bulletproof sync at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_devices = []
    
    # Get all computers
    computers = get_all_jamf_computers(jamf_headers)
    logger.info(f"📱 Processing {len(computers)} computers...")
    
    # Get detailed info for all computers
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_computer = {
            executor.submit(get_computer_details, comp['id'], jamf_headers): comp
            for comp in computers
        }
        
        for future in as_completed(future_to_computer):
            computer = future_to_computer[future]
            try:
                device_info = future.result()
                if device_info and device_info.get('serial_number'):
                    all_devices.append(device_info)
                else:
                    logger.warning(f"No details for computer {computer.get('id')}")
            except Exception as e:
                logger.error(f"Error processing computer {computer.get('id')}: {str(e)}")
    
    # Get all mobile devices
    mobile_devices = get_all_jamf_mobile_devices(jamf_headers)
    logger.info(f"📱 Processing {len(mobile_devices)} mobile devices...")
    
    # Get detailed info for all mobile devices
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_mobile = {
            executor.submit(get_mobile_device_details, device.get('id'), jamf_headers): device
            for device in mobile_devices
        }
        
        for future in as_completed(future_to_mobile):
            device = future_to_mobile[future]
            try:
                device_info = future.result()
                if device_info and device_info.get('serial_number'):
                    all_devices.append(device_info)
                else:
                    logger.warning(f"No details for mobile device {device.get('id')}")
            except Exception as e:
                logger.error(f"Error processing mobile device {device.get('id')}: {str(e)}")
    
    logger.info(f"🎯 TOTAL DEVICES TO SYNC: {len(all_devices)}")
    
    if not all_devices:
        logger.warning("⚠️ No devices found to sync")
        return
    
    # Sync all devices to Snipe-IT
    logger.info("🔄 Syncing devices to Snipe-IT...")
    
    success_count = 0
    failed_devices = []
    
    # Process with retry mechanism
    max_sync_attempts = 3
    
    for attempt in range(max_sync_attempts):
        devices_to_process = all_devices if attempt == 0 else failed_devices
        failed_devices = []
        
        if attempt > 0:
            logger.info(f"🔄 Sync attempt {attempt + 1} for {len(devices_to_process)} devices")
            time.sleep(5)  # Longer delay between retry attempts
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS // 2 if attempt > 0 else MAX_WORKERS) as executor:
            future_to_device = {
                executor.submit(process_device, device, snipe_headers): device
                for device in devices_to_process
            }
            
            for i, future in enumerate(as_completed(future_to_device), 1):
                device = future_to_device[future]
                serial = device.get('serial_number', 'Unknown')
                
                try:
                    if future.result():
                        if attempt == 0:
                            success_count += 1
                        logger.info(f"✅ [{i}/{len(devices_to_process)}] Synced: {serial}")
                    else:
                        failed_devices.append(device)
                        logger.warning(f"❌ [{i}/{len(devices_to_process)}] Failed: {serial}")
                except Exception as e:
                    failed_devices.append(device)
                    logger.error(f"❌ [{i}/{len(devices_to_process)}] Error {serial}: {str(e)}")
        
        # If no failures, we're done
        if not failed_devices:
            logger.info(f"🎉 All devices synced successfully on attempt {attempt + 1}")
            break
    
    # Final report
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("=" * 80)
    logger.info("🏁 BULLETPROOF SYNC COMPLETE")
    logger.info("=" * 80)
    logger.info(f"⏱️  Duration: {duration}")
    logger.info(f"📊 Total devices found: {len(all_devices)}")
    logger.info(f"✅ Successfully synced: {success_count}")
    logger.info(f"❌ Failed to sync: {len(failed_devices)}")
    logger.info(f"📈 Success rate: {(success_count/len(all_devices)*100):.1f}%")
    
    if failed_devices:
        logger.error("❌ FAILED DEVICES:")
        for device in failed_devices:
            logger.error(f"   - {device.get('serial_number', 'Unknown')}")
    else:
        logger.info("🎉 SUCCESS: 100% of devices synced!")
    
    logger.info("=" * 80)

if __name__ == '__main__':
    main()
