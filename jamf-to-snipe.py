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

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'sync_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Constants and Configuration
JAMF_URL = os.getenv('JAMF_URL', '').rstrip('/')
if not JAMF_URL.startswith('https://'):
    JAMF_URL = f"https://{JAMF_URL}"

CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')
JAMF_SMART_GROUP_ID = os.getenv('JAMF_SMART_GROUP_ID')

# Define categories
CATEGORIES = {
    'staff': {'id': 16, 'name': 'Staff Mac Laptop'},
    'student': {'id': 12, 'name': 'Student Loaner Laptop'}
}

# Create session with retry logic and connection pooling
def create_session():
    """Create a session with optimized retry settings"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # Reduced from 5 to 3 - if it fails after 3 retries, it's likely a real issue
        backoff_factor=2,  # More reasonable backoff - will retry after 2, 4, 8 seconds
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        respect_retry_after_header=True  # Honor server's retry-after header if present
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # Increased to handle concurrent requests
        pool_maxsize=10,  # Increased to match pool_connections
        pool_block=True  # Block when pool is full instead of discarding
    )
    session.mount("https://", adapter)
    session.headers.update({'User-Agent': 'JamfToSnipeSync/1.0'})  # Add user agent
    return session

# Create separate sessions for each API to avoid connection pool conflicts
jamf_session = create_session()
snipe_session = create_session()

@lru_cache(maxsize=1)
def get_jamf_token():
    """Get an access token from Jamf Pro API using client credentials with caching"""
    token_url = f"{JAMF_URL}/api/oauth/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        logger.debug(f"Requesting token from {token_url}")
        form_data = urllib.parse.urlencode(data)
        response = jamf_session.post(token_url, headers=headers, data=form_data)
        logger.debug(f"Token request status code: {response.status_code}")
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting Jamf token: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response: {e.response.text}")
        return None

def get_jamf_headers():
    """Get headers for Jamf Pro API using OAuth token"""
    token = get_jamf_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    } if token else None

# Cache for user lookups
user_cache = {}

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
        resp = snipe_session.get(url, headers=snipe_headers)
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
            json=model_data
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
    
    # Add delay before API call to prevent rate limiting
    time.sleep(3)
    
    try:
        # Use exact email match instead of search
        url = f"{SNIPE_IT_URL}/api/v1/users?email={urllib.parse.quote(email_lower)}&limit=1"
        logger.debug(f"Looking up user with email: {email_lower}")
        
        resp = snipe_session.get(url, headers=snipe_headers)
        
        # Check response before trying to parse JSON
        if resp.status_code == 200:
            try:
                users = resp.json().get('rows', [])
                if users:
                    user = users[0]
                    user_id = user.get('id')
                    if user_id:
                        user_cache[email_lower] = user_id
                        logger.debug(f"Found user {email_lower} with ID: {user_id}")
                        return user_id
            except ValueError as e:
                logger.warning(f"Invalid JSON response for user {email_lower}: {str(e)}")
        
        # Special handling for Kirsten Anderson
        if 'anderson' in email_lower:
            time.sleep(3)
            alt_email = 'kirsten.anderson@mywic.org'
            url = f"{SNIPE_IT_URL}/api/v1/users?email={urllib.parse.quote(alt_email)}&limit=1"
            
            resp = snipe_session.get(url, headers=snipe_headers)
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

def process_device(device, snipe_headers):
    """Process a single device for syncing"""
    try:
        serial = device.get('serial_number')
        logger.info(f"Processing device {serial}")
        
        # Add delay at the start of each device processing
        time.sleep(3)  # 3 second delay between devices
        
        # Convert headers to tuple for caching
        headers_tuple = tuple(sorted(snipe_headers.items()))
        
        # Determine category based on email domain
        email = device.get('email', '').lower()
        category = CATEGORIES['staff'] if '@mywic.org' in email else CATEGORIES['student']
        
        # Get model ID
        model_id = _get_or_create_model(device.get('model'), category['id'], headers_tuple)
        if not model_id:
            logger.error(f"Could not get/create model for {device.get('model')} - skipping device {serial}")
            return False
            
        # Get user ID - but don't fail if we can't get it
        user_id = None
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
            'category_id': category['id'],
            'name': device.get('device_name'),
            'notes': f"Last synced via Jamf Pro API at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        # Only set status_id for new assets
        if not resp.status_code == 200 or not resp.json().get('rows'):
            asset_data['status_id'] = 2  # Deployable
        
        # Check if asset exists
        url = f"{SNIPE_IT_URL}/api/v1/hardware/byserial/{serial}"
        resp = snipe_session.get(url, headers=snipe_headers)
        
        asset_id = None
        if resp.status_code == 200 and resp.json().get('rows'):
            # Update existing asset
            asset_id = resp.json().get('rows')[0].get('id')
            logger.info(f"Updating existing asset {asset_id} for serial {serial}")
            resp = snipe_session.put(
                f"{SNIPE_IT_URL}/api/v1/hardware/{asset_id}",
                headers=snipe_headers,
                json=asset_data
            )
        else:
            # Create new asset
            logger.info(f"Creating new asset for serial {serial}")
            resp = snipe_session.post(
                f"{SNIPE_IT_URL}/api/v1/hardware",
                headers=snipe_headers,
                json=asset_data
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
            
            # Add delay before checkout
            time.sleep(3)
            
            checkout_url = f"{SNIPE_IT_URL}/api/v1/hardware/{asset_id}/checkout"
            try:
                checkout_resp = snipe_session.post(
                    checkout_url,
                    headers=snipe_headers,
                    json=checkout_data
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

def fetch_jamf_devices(smart_group_id=None):
    """Fetch devices from Jamf Pro API with concurrent processing"""
    headers = get_jamf_headers()
    if not headers:
        logger.error("Failed to get Jamf headers")
        return []
        
    base_url = f"{JAMF_URL}/JSSResource"
    
    try:
        # Get device IDs
        if smart_group_id:
            url = f"{base_url}/computergroups/id/{smart_group_id}"
            logger.debug(f"Fetching devices from smart group: {url}")
        else:
            url = f"{base_url}/computers"
            logger.debug(f"Fetching all devices: {url}")
            
        resp = jamf_session.get(url, headers=headers)
        logger.debug(f"Device list request status code: {resp.status_code}")
        resp.raise_for_status()
        
        device_ids = [comp.get('id') for comp in resp.json().get('computers', [])]
        
        # Fetch detailed information concurrently
        all_devices = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_id = {
                executor.submit(fetch_device_details, device_id, headers, base_url): device_id
                for device_id in device_ids
            }
            
            for future in as_completed(future_to_id):
                device_id = future_to_id[future]
                try:
                    device_data = future.result()
                    if device_data:
                        all_devices.append(device_data)
                except Exception as e:
                    logger.error(f"Error fetching device {device_id}: {str(e)}")
        
        return all_devices
        
    except Exception as e:
        logger.error(f"Error fetching devices: {str(e)}")
        return []

def fetch_device_details(device_id, headers, base_url):
    """Fetch detailed information for a single device"""
    try:
        url = f"{base_url}/computers/id/{device_id}"
        resp = jamf_session.get(url, headers=headers)
        resp.raise_for_status()
        
        device_data = resp.json().get('computer', {})
        location = device_data.get('location', {})
        
        return {
            'serial_number': device_data.get('general', {}).get('serial_number'),
            'model': device_data.get('hardware', {}).get('model'),
            'asset_tag': device_data.get('general', {}).get('asset_tag'),
            'device_name': device_data.get('general', {}).get('name'),
            'username': location.get('username', ''),
            'email': location.get('email_address', ''),
            'real_name': location.get('real_name', '')
        }
    except Exception as e:
        logger.error(f"Error fetching device details for {device_id}: {str(e)}")
        return None

def main():
    """Main execution function"""
    if not all([JAMF_URL, SNIPE_IT_URL, SNIPE_IT_API_TOKEN]):
        logger.error("Missing required environment variables")
        return
    
    # Set up Snipe-IT headers
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Fetch all devices
    logger.info("Fetching devices from Jamf Pro...")
    devices = fetch_jamf_devices(JAMF_SMART_GROUP_ID)
    logger.info(f"Found {len(devices)} devices")
    
    # Process devices with limited concurrency
    success_count = 0
    with ThreadPoolExecutor(max_workers=1) as executor:  # Keep at 1 worker
        # Create futures for each device
        futures = []
        for device in devices:
            # Add delay between submissions
            time.sleep(5)  # Increased from 3 to 5 seconds delay
            future = executor.submit(process_device, device, snipe_headers)
            futures.append((future, device.get('serial_number')))
        
        # Process completed futures
        for future, serial in futures:
            try:
                if future.result():
                    success_count += 1
                    logger.info(f"Successfully processed device {serial}")
                else:
                    logger.warning(f"Failed to process device {serial}")
            except Exception as e:
                logger.error(f"Error processing device {serial}: {str(e)}")
    
    logger.info(f"Sync completed. Successfully processed {success_count} out of {len(devices)} devices")

if __name__ == '__main__':
    main() 