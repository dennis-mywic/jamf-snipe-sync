import requests
import os
import time
import argparse
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from functools import lru_cache
import logging
from datetime import datetime
import sys
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for cleaner logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'sync_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Jamf Pro settings
JAMF_URL = os.getenv('JAMF_URL', '').rstrip('/')
if not JAMF_URL.startswith('http'):
    JAMF_URL = f'https://{JAMF_URL}'

# Support both OAuth client credentials and basic auth
JAMF_CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
JAMF_USERNAME = os.getenv('JAMF_USERNAME')
JAMF_PASSWORD = os.getenv('JAMF_PASSWORD')

# Snipe-IT settings
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL', '').rstrip('/')
if not SNIPE_IT_URL.startswith('http'):
    # Use environment variable or default to HTTPS
    SNIPE_IT_URL = os.getenv('SNIPE_IT_URL_FALLBACK', 'https://172.22.2.74')

SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN', '')

# Verify required environment variables
if not all([JAMF_URL, SNIPE_IT_URL, SNIPE_IT_API_TOKEN]):
    logger.error('Missing required environment variables. Please check your .env file.')
    sys.exit(1)

if not (JAMF_CLIENT_ID and JAMF_CLIENT_SECRET) and not (JAMF_USERNAME and JAMF_PASSWORD):
    logger.error("Missing Jamf credentials - need either client credentials or username/password")
    sys.exit(1)

# Define categories and smart groups
CATEGORIES = {
    'staff': {'id': 16, 'name': 'Staff Mac Laptop'},
    'student': {'id': 12, 'name': 'Student Loaner Laptop'},
    'ssc': {'id': 13, 'name': 'SSC Laptop'},
    'checkin_ipad': {'id': 20, 'name': 'Check-In iPad'},
    'donations_ipad': {'id': 19, 'name': 'Donations iPad'},
    'moneris_ipad': {'id': 21, 'name': 'Moneris iPad'},
    'teacher_ipad': {'id': 15, 'name': 'Teacher iPad'},
    'appletv': {'id': 11, 'name': 'Apple TVs'}
}

# Smart group IDs
SMART_GROUPS = {
    'computers': {
        'all_staff_mac': {'id': 22, 'name': "All Staff Mac"},
        'student_loaners': {'id': 3, 'name': "Student Loaners"},
        'ssc_laptops': {'id': 25, 'name': "SSC Laptops", 'category': 'ssc'},
        'operations_mac': {'id': 5, 'name': "Operations Mac"}
    },
    'mobile_devices': {
        'apple_tvs': {'id': 1, 'name': "Apple TVs", 'category': 'appletv'},
        'checkin_ipad': {'id': 11, 'name': "Check-In iPad", 'category': 'checkin_ipad'},
        'donations_ipad': {'id': 10, 'name': "Donations iPad", 'category': 'donations_ipad'},
        'moneris_ipad': {'id': 9, 'name': "Moneris iPad", 'category': 'moneris_ipad'},
        'teacher_ipad': {'id': 2, 'name': "Teacher iPad", 'category': 'teacher_ipad'}
    }
}

# Create session with improved retry logic and connection pooling
def create_session():
    """Create a requests session with improved retry logic and connection pooling"""
    session = requests.Session()
    retries = Retry(
        total=5,  # Increased from 3
        backoff_factor=0.5,  # Increased from 0.3
        status_forcelist=[500, 502, 503, 504, 429],  # Added 429 (rate limit)
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]  # Allow POST retries
    )
    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=10,  # Increased connection pool
        pool_maxsize=20,      # Increased max connections
        pool_block=False      # Don't block when pool is full
    )
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

jamf_session = create_session()
snipe_session = create_session()

def get_jamf_headers():
    """Get headers for Jamf Pro API requests"""
    try:
        # Try OAuth client credentials first
        if JAMF_CLIENT_ID and JAMF_CLIENT_SECRET:
            url = f"{JAMF_URL}/api/oauth/token"
            logger.debug(f"Requesting token from {url}")
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': JAMF_CLIENT_ID,
                'client_secret': JAMF_CLIENT_SECRET
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            resp = jamf_session.post(url, data=data, headers=headers, timeout=30)
            logger.debug(f"Token request status code: {resp.status_code}")
            
            if resp.status_code == 200:
                token = resp.json().get('access_token')
                return {
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            else:
                logger.error(f"Failed to get token: {resp.status_code}")
                if hasattr(resp, 'text'):
                    logger.error(f"Response: {resp.text}")
        
        # Fall back to basic auth if OAuth fails or not configured
        if JAMF_USERNAME and JAMF_PASSWORD:
            import base64
            auth_string = base64.b64encode(f"{JAMF_USERNAME}:{JAMF_PASSWORD}".encode()).decode()
            return {
                'Authorization': f'Basic {auth_string}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
        return None
            
    except Exception as e:
        logger.error(f"Error getting headers: {str(e)}")
        return None

# Cache for user lookups and prestage lookups
user_cache = {}
prestage_cache = {}

# Prestage functions removed - now getting prestage info directly from device details

@lru_cache(maxsize=100)
def get_or_create_model(model_name: str, category_id: int, snipe_headers: dict) -> int:
    """Get or create a model in Snipe-IT with caching"""
    # Convert headers dict to a hashable tuple for caching
    headers_tuple = tuple(sorted(snipe_headers.items()))
    return _get_or_create_model(model_name, category_id, headers_tuple)

def _get_or_create_model(model_name: str, category_id: int, headers_tuple: tuple) -> int:
    """Internal function to handle model creation/lookup"""
    if not model_name:
        return None
    
    # Convert headers tuple back to dict
    snipe_headers = dict(headers_tuple)
    
    # Search for existing model
    url = f"{SNIPE_IT_URL}/api/v1/models?search={model_name}"
    try:
        resp = snipe_session.get(url, headers=snipe_headers, timeout=30)
        resp.raise_for_status()
        
        if resp.status_code == 200:
            models = resp.json().get('rows', [])
            for model in models:
                if model.get('name') == model_name:
                    return model.get('id')
        
        # Create new model if not found
        model_data = {
            'name': model_name,
            'model_number': model_name,
            'category_id': category_id,
            'manufacturer_id': 1,  # Apple
            'fieldset_id': 2,      # Asset
        }
        
        resp = snipe_session.post(
            f"{SNIPE_IT_URL}/api/v1/models",
            headers=snipe_headers,
            json=model_data,
            timeout=30
        )
        resp.raise_for_status()
        
        return resp.json().get('payload', {}).get('id')
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error with model {model_name}: {str(e)}")
        return None

@lru_cache(maxsize=100)
def get_user(email: str, snipe_headers: dict) -> int:
    """Look up an existing user in Snipe-IT by email (case-insensitive) with caching"""
    # Convert headers dict to a hashable tuple for caching
    headers_tuple = tuple(sorted(snipe_headers.items()))
    return _get_user(email, headers_tuple)

def _get_user(email: str, headers_tuple: tuple) -> int:
    """Internal function to handle user lookup"""
    if not email:
        return None
    
    # Convert headers tuple back to dict
    snipe_headers = dict(headers_tuple)
    
    # Check cache first
    email_lower = email.lower()
    if email_lower in user_cache:
        return user_cache[email_lower]
    
    # Reduced delay before API call to prevent rate limiting
    time.sleep(1)  # Reduced from 3 seconds
    
    try:
        # Try variations of the email
        email_variations = [email_lower]
        
        # Handle special cases for known name variations
        if 'mackenzie' in email_lower:
            email_variations.append(email_lower.replace('mackenzie', 'mckenzie'))
        elif 'mckenzie' in email_lower:
            email_variations.append(email_lower.replace('mckenzie', 'mackenzie'))
            
        # Try each email variation
        for email_var in email_variations:
            url = f"{SNIPE_IT_URL}/api/v1/users?email={urllib.parse.quote(email_var)}&limit=1"
            logger.debug(f"Looking up user with email: {email_var}")
            
            resp = snipe_session.get(url, headers=snipe_headers, timeout=30)
            
            # Check response before trying to parse JSON
            if resp.status_code == 200:
                try:
                    users = resp.json().get('rows', [])
                    if users:
                        user = users[0]
                        user_id = user.get('id')
                        if user_id:
                            user_cache[email_lower] = user_id
                            logger.debug(f"Found user {email_var} with ID: {user_id}")
                            return user_id
                except ValueError as e:
                    logger.warning(f"Invalid JSON response for user {email_var}: {str(e)}")
        
        # Special handling for Kirsten Anderson
        if 'anderson' in email_lower:
            time.sleep(1)  # Reduced delay
            alt_email = 'kirsten.anderson@mywic.org'
            url = f"{SNIPE_IT_URL}/api/v1/users?email={urllib.parse.quote(alt_email)}&limit=1"
            
            resp = snipe_session.get(url, headers=snipe_headers, timeout=30)
            if resp.status_code == 200:
                try:
                    users = resp.json().get('rows', [])
                    if users:
                        user = users[0]
                        user_id = user.get('id')
                        if user_id:
                            user_cache[email_lower] = user_id
                            logger.debug(f"Found Kirsten Anderson with ID: {user_id}")
                            return user_id
                except ValueError as e:
                    logger.warning(f"Invalid JSON response for Kirsten Anderson: {str(e)}")
        
        logger.debug(f"No user found for email: {email_lower}")
        user_cache[email_lower] = None
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching for user {email_lower}: {str(e)}")
        # Don't cache on request errors so we can retry next time
        return None

def fetch_mobile_device_details(device_id, headers, base_url):
    """Fetch detailed information for a single mobile device"""
    try:
        # First try the classic API
        url = f"{base_url}/mobiledevices/id/{device_id}"
        logger.debug(f"Fetching mobile device details from: {url}")
        resp = jamf_session.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 401:
            # If classic API fails, try the modern API
            # Get a fresh token for the modern API
            new_headers = get_jamf_headers()
            modern_url = f"{JAMF_URL}/api/v2/mobile-devices/{device_id}"
            resp = jamf_session.get(modern_url, headers=new_headers, timeout=30)
            resp.raise_for_status()
            device_data = resp.json()
        else:
            resp.raise_for_status()
            device_data = resp.json().get('mobile_device', {})
            
        if not device_data:
            logger.warning(f"No data found for mobile device {device_id}")
            return None
            
        # Extract relevant fields
        if 'general' in device_data:
            # Classic API response
            general = device_data.get('general', {})
            location = device_data.get('location', {})
            return {
                'serial_number': general.get('serial_number'),
                'model': general.get('model'),
                'asset_tag': general.get('asset_tag'),
                'device_name': general.get('name'),
                'username': location.get('username', ''),
                'email': location.get('email_address', ''),
                'real_name': location.get('real_name', ''),
                'device_type': 'mobile'
            }
        else:
            # Modern API response
            return {
                'serial_number': device_data.get('serialNumber'),
                'model': device_data.get('model'),
                'asset_tag': device_data.get('assetTag'),
                'device_name': device_data.get('name'),
                'username': device_data.get('username', ''),
                'email': device_data.get('emailAddress', ''),
                'real_name': device_data.get('realName', ''),
                'device_type': 'mobile'
            }
            
    except Exception as e:
        logger.error(f"Error fetching mobile device details for {device_id}: {str(e)}")
        return None

def fetch_computer_details(device_id, headers, base_url):
    """Fetch detailed information for a single computer"""
    try:
        # Fetch from Classic API with extended data including prestage
        url = f"{base_url}/computers/id/{device_id}"
        resp = jamf_session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        
        device_data = resp.json().get('computer', {})
        general = device_data.get('general', {})
        location = device_data.get('location', {})
        
        # Try to get prestage enrollment info from multiple possible fields
        prestage_name = ''
        prestage_sources = [
            general.get('mdm_capability_capable_users', {}).get('mdm_capability_capable_user', {}).get('enrollment_method'),
            general.get('enrollment_method'),
            general.get('prestage_enrollment'),
            general.get('prestage'),
        ]
        
        # Also check extension attributes for prestage info
        extension_attributes = device_data.get('extension_attributes', [])
        for attr in extension_attributes:
            attr_name = attr.get('name', '').lower()
            if 'prestage' in attr_name or 'enrollment' in attr_name:
                prestage_name = attr.get('value', '')
                break
        
        # If no prestage found in extension attributes, check the sources
        if not prestage_name:
            for source in prestage_sources:
                if source and str(source).strip():
                    prestage_name = str(source).strip()
                    break
        
        # Determine category based on available information
        category, category_reason = determine_category_from_device_info(general, location, prestage_name)
        
        return {
            'device_id': device_id,
            'serial_number': general.get('serial_number'),
            'model': device_data.get('hardware', {}).get('model'),
            'asset_tag': general.get('asset_tag'),
            'device_name': general.get('name'),
            'username': location.get('username', ''),
            'email': location.get('email_address', ''),
            'real_name': location.get('real_name', ''),
            'device_type': 'computer',
            'prestage_name': prestage_name,
            'category': category,
            'category_reason': category_reason
        }
    except Exception as e:
        logger.error(f"Error fetching computer details for {device_id}: {str(e)}")
        return None

def determine_category_from_device_info(general, location, prestage_name):
    """Determine Snipe-IT category based on available device information"""
    # Check prestage name first
    if prestage_name:
        prestage_lower = prestage_name.lower()
        if 'student' in prestage_lower or 'loaner' in prestage_lower:
            logger.info(f"Category determined by prestage '{prestage_name}' → Student")
            return CATEGORIES['student'], 'prestage'
        elif 'ssc' in prestage_lower:
            logger.info(f"Category determined by prestage '{prestage_name}' → SSC")
            return CATEGORIES['ssc'], 'prestage'
        elif 'staff' in prestage_lower or 'teacher' in prestage_lower or 'employee' in prestage_lower:
            logger.info(f"Category determined by prestage '{prestage_name}' → Staff")
            return CATEGORIES['staff'], 'prestage'
    
    # Check user email patterns
    email = location.get('email_address', '').lower()
    if email:
        # Student email patterns (customize based on your school's pattern)
        if any(pattern in email for pattern in ['student', '@students.', 'pupil']):
            logger.info(f"Category determined by email pattern '{email}' → Student")
            return CATEGORIES['student'], 'email'
    
    # Check device name patterns
    device_name = general.get('name', '').lower()
    if device_name:
        if any(pattern in device_name for pattern in ['student', 'loaner', 'loan']):
            logger.info(f"Category determined by device name '{device_name}' → Student")
            return CATEGORIES['student'], 'device_name'
        elif 'ssc' in device_name:
            logger.info(f"Category determined by device name '{device_name}' → SSC")
            return CATEGORIES['ssc'], 'device_name'
    
    # Default to staff (no clear indicators)
    logger.info(f"Category defaulted to Staff (no clear indicators found)")
    return CATEGORIES['staff'], None

def fetch_devices_from_group(group_id, device_type='computers'):
    """Fetch devices from a specific Jamf Pro smart group"""
    headers = get_jamf_headers()
    if not headers:
        logger.error("Failed to get Jamf headers")
        return []
        
    base_url = f"{JAMF_URL}/JSSResource"
    endpoint = 'computergroups' if device_type == 'computers' else 'mobiledevicegroups'
    
    try:
        # First try the classic API
        url = f"{base_url}/{endpoint}/id/{group_id}"
        logger.debug(f"Fetching devices from group: {url}")
        resp = jamf_session.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 401 and device_type != 'computers':
            # If classic API fails for mobile devices, try the modern API
            # Get a fresh token for the modern API
            new_headers = get_jamf_headers()
            modern_url = f"{JAMF_URL}/api/v2/mobile-device-groups/{group_id}/devices"
            resp = jamf_session.get(modern_url, headers=new_headers, timeout=30)
            resp.raise_for_status()
            devices = resp.json().get('results', [])
            device_ids = [dev.get('id') for dev in devices]
        else:
            # Classic API worked
            resp.raise_for_status()
            if device_type == 'computers':
                devices = resp.json().get('computer_group', {}).get('computers', [])
            else:
                devices = resp.json().get('mobile_device_group', {}).get('mobile_devices', [])
                
            device_ids = [dev.get('id') for dev in devices]
            
        logger.info(f"Found {len(device_ids)} devices in group {group_id}")
        
        # Fetch detailed information concurrently with improved concurrency
        all_devices = []
        with ThreadPoolExecutor(max_workers=8) as executor:  # Increased from 5
            if device_type == 'computers':
                future_to_id = {
                    executor.submit(fetch_computer_details, device_id, headers, base_url): device_id
                    for device_id in device_ids
                }
            else:
                future_to_id = {
                    executor.submit(fetch_mobile_device_details, device_id, headers, base_url): device_id
                    for device_id in device_ids
                }
            
            for future in as_completed(future_to_id):
                device_id = future_to_id[future]
                try:
                    device_data = future.result()
                    if device_data:
                        all_devices.append(device_data)
                        logger.info(f"Successfully fetched details for device {device_id}")
                    else:
                        logger.warning(f"No data returned for device {device_id}")
                except Exception as e:
                    logger.error(f"Error fetching device {device_id}: {str(e)}")
        
        logger.info(f"Successfully fetched details for {len(all_devices)} devices from group {group_id}")
        return all_devices
        
    except Exception as e:
        logger.error(f"Error fetching devices from group {group_id}: {str(e)}")
        return []

def list_smart_groups(device_type='computers'):
    """List all smart groups in Jamf Pro"""
    headers = get_jamf_headers()
    if not headers:
        logger.error("Failed to get Jamf headers")
        return []
        
    base_url = f"{JAMF_URL}/JSSResource"
    endpoint = 'computergroups' if device_type == 'computers' else 'mobiledevicegroups'
    
    try:
        url = f"{base_url}/{endpoint}"
        logger.debug(f"Fetching all groups from: {url}")
        resp = jamf_session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        
        if device_type == 'computers':
            groups = resp.json().get('computer_groups', [])
        else:
            groups = resp.json().get('mobile_device_groups', [])
            
        logger.info(f"Found {len(groups)} {device_type} groups:")
        for group in groups:
            logger.info(f"  - {group.get('name')} (ID: {group.get('id')})")
            
    except Exception as e:
        logger.error(f"Error fetching {device_type} groups: {str(e)}")

def process_device(device, snipe_headers, device_category):
    """Process a single device for syncing"""
    try:
        serial = device.get('serial_number')
        logger.info(f"Processing device {serial}")
        
        # Reduced delay at the start of each device processing
        time.sleep(2)  # Reduced from 14 seconds to 2 seconds
        
        # Convert headers to tuple for caching
        headers_tuple = tuple(sorted(snipe_headers.items()))
        
        # Get model ID
        model_id = _get_or_create_model(device.get('model'), device_category['id'], headers_tuple)
        if not model_id:
            logger.error(f"Could not get/create model for {device.get('model')} - skipping device {serial}")
            return False
            
        # Get user ID if available
        user_id = None
        email = device.get('email')
        if email:
            try:
                user_id = _get_user(email, headers_tuple)
                if user_id:
                    logger.info(f"Successfully found user ID {user_id} for email {email}")
                else:
                    logger.warning(f"No user ID found for email {email} - will create/update asset without user assignment")
            except Exception as e:
                logger.warning(f"Error looking up user for email {email} - will create/update asset without user assignment: {str(e)}")
        
        # Prepare asset data
        asset_data = {
            'asset_tag': serial,
            'serial': serial,
            'model_id': model_id,
            'category_id': device_category['id'],
            'name': device.get('device_name'),
            'notes': f"Last synced via Jamf Pro API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        # Check if asset exists
        url = f"{SNIPE_IT_URL}/api/v1/hardware/byserial/{serial}"
        resp = snipe_session.get(url, headers=snipe_headers, timeout=30)
        
        # Only set status_id for new assets
        if resp.status_code != 200 or not resp.json().get('rows'):
            asset_data['status_id'] = 2  # Deployable
        
        asset_id = None
        if resp.status_code == 200 and resp.json().get('rows'):
            # Update existing asset
            asset_id = resp.json().get('rows')[0].get('id')
            logger.info(f"Updating existing asset {asset_id} for serial {serial}")
            resp = snipe_session.put(
                f"{SNIPE_IT_URL}/api/v1/hardware/{asset_id}",
                headers=snipe_headers,
                json=asset_data,
                timeout=30
            )
        else:
            # Create new asset
            logger.info(f"Creating new asset for serial {serial}")
            resp = snipe_session.post(
                f"{SNIPE_IT_URL}/api/v1/hardware",
                headers=snipe_headers,
                json=asset_data,
                timeout=30
            )
            if resp.status_code == 200:
                asset_id = resp.json().get('payload', {}).get('id')
        
        resp.raise_for_status()
        
        # If we have both asset_id and user_id, checkout the asset to the user
        if asset_id and user_id:
            logger.info(f"Checking out asset {asset_id} to user {user_id}")
            checkout_data = {
                'assigned_user': user_id,  # Using assigned_user as required by the API
                'checkout_to_type': 'user',
                'note': f"Automatically checked out via Jamf sync on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            # Reduced delay before checkout
            time.sleep(1)  # Reduced from 3 seconds
            
            checkout_url = f"{SNIPE_IT_URL}/api/v1/hardware/{asset_id}/checkout"
            try:
                checkout_resp = snipe_session.post(
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
        logger.error(f"Error processing device {device.get('serial_number')}: {str(e)}")
        return False

def main():
    """Main execution function"""
    # List all smart groups first
    logger.info("Listing all smart groups in Jamf Pro...")
    list_smart_groups('computers')
    list_smart_groups('mobile_devices')
    
    # Set up Snipe-IT headers
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    all_devices = []
    
    # Fetch computers from smart groups - simple and accurate categorization
    logger.info("Fetching computers from Jamf Pro...")
    for group_name, group_info in SMART_GROUPS['computers'].items():
        devices = fetch_devices_from_group(group_info['id'], 'computers')
        
        # Simple rule: smart group determines category, period.
        for device in devices:
            if group_name == 'student_loaners':
                device['category'] = CATEGORIES['student']
                logger.info(f"Device {device.get('serial_number')} (Student Loaners group) → Category: Student Loaner Laptop")
            elif group_name == 'ssc_laptops':
                device['category'] = CATEGORIES['ssc']
                logger.info(f"Device {device.get('serial_number')} (SSC Laptops group) → Category: SSC Laptop")
            else:
                device['category'] = CATEGORIES['staff']
                logger.info(f"Device {device.get('serial_number')} ({group_info['name']} group) → Category: Staff Mac Laptop")
        
        all_devices.extend(devices)
    
    # Fetch mobile devices
    logger.info("Fetching mobile devices from Jamf Pro...")
    for group_name, group_info in SMART_GROUPS['mobile_devices'].items():
        devices = fetch_devices_from_group(group_info['id'], 'mobile_devices')
        for device in devices:
            device['category'] = CATEGORIES[group_info['category']]
        all_devices.extend(devices)
        logger.info(f"Added {len(devices)} devices from {group_info['name']}")
    
    logger.info(f"Found total of {len(all_devices)} devices")
    
    # Process all devices with improved concurrency
    success_count = 0
    with ThreadPoolExecutor(max_workers=3) as executor:  # Increased from 1 to 3
        futures = []
        for device in all_devices:
            time.sleep(1)  # Reduced from 5 seconds to 1 second
            future = executor.submit(process_device, device, snipe_headers, device['category'])
            futures.append((future, device.get('serial_number')))
        
        for future, serial in futures:
            try:
                if future.result():
                    success_count += 1
                    logger.info(f"Successfully processed device {serial}")
                else:
                    logger.warning(f"Failed to process device {serial}")
            except Exception as e:
                logger.error(f"Error processing device {serial}: {str(e)}")
    
    logger.info(f"Sync completed. Successfully processed {success_count} out of {len(all_devices)} devices")

if __name__ == '__main__':
    main() 