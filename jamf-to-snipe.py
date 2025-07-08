import requests
import os
import time
import argparse
import urllib.parse

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Ensure URL is properly formatted
JAMF_URL = os.getenv('JAMF_URL', '').rstrip('/')
if not JAMF_URL.startswith('https://'):
    JAMF_URL = f"https://{JAMF_URL}"

# Jamf Pro API credentials
CLIENT_ID = "ce1b6f6c-693c-4610-969c-da9a0f897d4e"
CLIENT_SECRET = "HSGaXnwNVK0KzsP6YHLfbaVXynjfZ81tN4xaygXWlG7m8FQYiJ0zsFiw1QJwPS3B"

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')
JAMF_SMART_GROUP_ID = os.getenv('JAMF_SMART_GROUP_ID')  # Optional: for filtering specific devices

# Define categories
CATEGORIES = {
    'staff': {'id': 16, 'name': 'Staff Mac Laptop'},
    'student': {'id': 12, 'name': 'Student Loaner Laptop'}
}

if not all([JAMF_URL, SNIPE_IT_URL, SNIPE_IT_API_TOKEN]):
    print("Missing one or more required environment variables.")
    exit(1)

def get_jamf_token():
    """Get an access token from Jamf Pro API using client credentials"""
    token_url = f"{JAMF_URL}/api/oauth/token"
    
    # Create form data
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        # Convert data to form-urlencoded format
        form_data = urllib.parse.urlencode(data)
        
        response = requests.post(token_url, headers=headers, data=form_data)
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Error getting Jamf token: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

def get_jamf_headers():
    """Get headers for Jamf Pro API using OAuth token"""
    token = get_jamf_token()
    if not token:
        return None
        
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

def get_jamf_url():
    """Get the proper Jamf API URL by ensuring it ends with /JSSResource"""
    base_url = JAMF_URL.rstrip('/')
    if not base_url.endswith('/JSSResource'):
        base_url += '/JSSResource'
    return base_url

def make_request_with_retry(method, url, headers, json=None, max_retries=3, retry_delay=5):
    """Make a request with retry logic for rate limits"""
    for attempt in range(max_retries):
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=json)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=json)
            
            if response.status_code != 429:  # Not rate limited
                return response
                
            # If rate limited, wait and retry
            print(f"Rate limited, waiting {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:  # Last attempt
                raise
            print(f"Request failed, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
    
    return response  # Return last response if all retries failed

def get_user(email, snipe_headers):
    """Look up an existing user in Snipe-IT by email (case-insensitive) or username"""
    if not email:
        return None
    
    # Try different search formats
    email_variants = [
        email.lower(),  # lowercase
        email.replace('@', ''),  # no @ symbol
        email.split('@')[0]  # username part only
    ]
    
    # Try name-based search if email contains a name
    username = email.split('@')[0].lower()
    if 'anderson' in username:  # Special case for Kristen/Kirsten Anderson
        email_variants.extend([
            'anderson',  # Last name only
            'kirstenanderson',  # Alternate spelling
            'kirsten.anderson'  # Alternate format
        ])
    
    for email_try in email_variants:
        # Try to find existing user
        url = f"{SNIPE_IT_URL}/api/v1/users?search={email_try}"
        
        try:
            resp = make_request_with_retry('GET', url, snipe_headers)
            resp.raise_for_status()
            
            if resp.status_code == 200:
                users = resp.json().get('rows', [])
                print(f"\nSearching with: {email_try}")
                print(f"Found {len(users)} potential matches:")
                for user in users:
                    print(f"- {user.get('name')} ({user.get('email')}) [username: {user.get('username')}]")
                
                # Check for matches
                for user in users:
                    # Match by email
                    if user.get('email', '').lower() == email.lower():
                        print(f"Found email match: {user.get('name')} ({user.get('email')})")
                        return user.get('id')
                    # Match by username
                    if user.get('username', '').lower() == email.split('@')[0].lower():
                        print(f"Found username match: {user.get('name')} ({user.get('email')})")
                        return user.get('id')
                    # For Kristen/Kirsten Anderson, match by name
                    if 'anderson' in username:
                        user_name = user.get('name', '').lower()
                        user_email = user.get('email', '').lower()
                        if ('kirsten' in user_name or 'kristen' in user_name) and 'anderson' in user_name:
                            print(f"Found name match: {user.get('name')} ({user.get('email')})")
                            return user.get('id')
                        if 'kirstenanderson' in user_email or 'kristenanderson' in user_email:
                            print(f"Found email match: {user.get('name')} ({user.get('email')})")
                            return user.get('id')
        
        except requests.exceptions.RequestException as e:
            print(f"Error with search {email_try}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            continue
    
    print(f"No existing user found for email: {email}")
    return None

def fetch_jamf_devices(smart_group_id=None):
    """Fetch devices from Jamf Pro API, optionally filtered by Smart Group"""
    headers = get_jamf_headers()
    if not headers:
        return []
        
    base_url = JAMF_URL.rstrip('/') + '/JSSResource'
    
    # If using a smart group, get devices from that group
    if smart_group_id:
        url = f"{base_url}/computergroups/id/{smart_group_id}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching smart group: {resp.status_code}")
            print(f"Response: {resp.text}")
            return []
        computers = resp.json().get('computer_group', {}).get('computers', [])
        device_ids = [comp.get('id') for comp in computers]
    else:
        # Get all computers
        url = f"{base_url}/computers"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching computers: {resp.status_code}")
            print(f"Response: {resp.text}")
            return []
        computers = resp.json().get('computers', [])
        device_ids = [comp.get('id') for comp in computers]
    
    # Fetch detailed information for each device
    all_devices = []
    for device_id in device_ids:
        url = f"{base_url}/computers/id/{device_id}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            device_data = resp.json().get('computer', {})
            location = device_data.get('location', {})
            
            # Extract user information
            username = location.get('username', '')
            email = location.get('email_address', '')
            real_name = location.get('real_name', '')
            
            all_devices.append({
                'serial_number': device_data.get('general', {}).get('serial_number'),
                'model': device_data.get('hardware', {}).get('model'),
                'asset_tag': device_data.get('general', {}).get('asset_tag'),
                'device_name': device_data.get('general', {}).get('name'),
                'username': username,
                'email': email,
                'real_name': real_name
            })
            time.sleep(1)  # Rate limiting
        else:
            print(f"Error fetching device {device_id}: {resp.status_code}")
            print(f"Response: {resp.text}")
    
    return all_devices

def get_jamf_computers(token):
    """Get all computers from Jamf Pro"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    try:
        # Try the computers-inventory endpoint first
        response = requests.get(f"{JAMF_URL}/api/v1/computers-inventory", headers=headers)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print(f"Error getting computers from Jamf: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return []

def get_or_create_category(name="Staff Macs"):
    """Get or create a category in Snipe-IT"""
    headers = {"Authorization": f"Bearer {SNIPE_IT_API_TOKEN}", "Accept": "application/json", "Content-Type": "application/json"}
    
    # Try to find existing category
    url = f"{SNIPE_IT_URL}/api/v1/categories?search={name}"
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        categories = resp.json().get('rows', [])
        for category in categories:
            if category.get('name') == name:
                return category.get('id')
    
    # Create new category if not found
    create_url = f"{SNIPE_IT_URL}/api/v1/categories"
    create_data = {
        "name": name,
        "category_type": "asset",
        "use_default_eula": False,
        "require_acceptance": False,
        "checkin_email": False
    }
    
    create_resp = requests.post(create_url, headers=headers, json=create_data)
    
    if create_resp.status_code == 200:
        new_category = create_resp.json()
        print(f"Created new category: {name}")
        return new_category.get('payload', {}).get('id')
    else:
        print(f"Failed to create category: {create_resp.text}")
        return None

def get_or_create_model(model_name, category_id):
    headers = {"Authorization": f"Bearer {SNIPE_IT_API_TOKEN}", "Accept": "application/json", "Content-Type": "application/json"}
    # First try to find existing model
    url = f"{SNIPE_IT_URL}/api/v1/models?search={model_name}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None
    rows = resp.json().get('rows', [])
    for row in rows:
        if row['name'] == model_name:
            # Update model to correct category if needed
            if row.get('category_id') != category_id:
                update_url = f"{SNIPE_IT_URL}/api/v1/models/{row['id']}"
                update_data = {"category_id": category_id}
                update_resp = requests.put(update_url, headers=headers, json=update_data)
                if update_resp.status_code == 200:
                    print(f"Updated model {model_name} to category {category_id}")
            return row['id']
    
    # Create new model if not found
    create_url = f"{SNIPE_IT_URL}/api/v1/models"
    create_data = {"name": model_name, "manufacturer_id": 1, "category_id": category_id}
    create_resp = requests.post(create_url, headers=headers, json=create_data)
    if create_resp.status_code == 200:
        new_model = create_resp.json().get('payload', {})
        if 'id' in new_model:
            print(f"Created new model {model_name} in category {category_id}")
            return new_model['id']
    return None

def sync_device(device, category_id):
    headers = {"Authorization": f"Bearer {SNIPE_IT_API_TOKEN}", "Accept": "application/json", "Content-Type": "application/json"}
    serial = device.get('serial_number')
    if not serial:
        return False
    
    model_name = device.get('model') or 'Unknown Model'
    model_id = get_or_create_model(model_name, category_id)
    if not model_id:
        print(f"Failed to get/create model for {serial}")
        return False
    
    asset_tag = device.get('asset_tag') or serial
    name = device.get('device_name') or serial
    
    # Get user in Snipe-IT
    user_id = None
    if device.get('username') or device.get('email'):
        user_id = get_user(device.get('email'), headers)
    
    # Check if device already exists
    search_url = f"{SNIPE_IT_URL}/api/v1/hardware?search={serial}"
    try:
        search_resp = make_request_with_retry('GET', search_url, headers)
        search_resp.raise_for_status()
        existing_devices = search_resp.json().get('rows', [])
        device_id = None
        
        # Look for exact serial match
        for existing in existing_devices:
            if existing.get('serial') == serial:
                device_id = existing.get('id')
                break
        
        if device_id:
            # Update existing device
            update_url = f"{SNIPE_IT_URL}/api/v1/hardware/{device_id}"
            update_data = {
                "name": name,
                "serial": serial,
                "asset_tag": asset_tag,
                "category_id": category_id,
                "model_id": model_id,
                "status_id": 2,  # Available
                "notes": "Synced via Jamf Pro API"
            }
            
            update_resp = make_request_with_retry('PUT', update_url, headers, json=update_data)
            if update_resp.status_code != 200:
                print(f"Failed to update device {serial}: {update_resp.text}")
                return False
            print(f"Updated device {serial}")
        else:
            # Create new device
            create_url = f"{SNIPE_IT_URL}/api/v1/hardware"
            create_data = {
                "name": name,
                "serial": serial,
                "asset_tag": asset_tag,
                "category_id": category_id,
                "model_id": model_id,
                "status_id": 2,  # Available
                "notes": "Synced via Jamf Pro API"
            }
            
            create_resp = make_request_with_retry('POST', create_url, headers, json=create_data)
            if create_resp.status_code != 200:
                print(f"Failed to create device {serial}: {create_resp.text}")
                return False
            device_id = create_resp.json().get('payload', {}).get('id')
            print(f"Created device {serial}")
        
        # If we have both user and device IDs, perform checkout
        if user_id and device_id:
            checkout_url = f"{SNIPE_IT_URL}/api/v1/hardware/{device_id}/checkout"
            checkout_data = {
                "assigned_user": user_id,
                "checkout_to_type": "user",
                "note": "Automatically checked out via Jamf sync"
            }
            
            checkout_resp = make_request_with_retry('POST', checkout_url, headers, json=checkout_data)
            if checkout_resp.status_code == 200:
                print(f"Checked out device {serial} to user ID {user_id}")
            else:
                print(f"Failed to checkout device {serial}: {checkout_resp.text}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error syncing device {serial}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Sync devices from Jamf to Snipe-IT')
    parser.add_argument('--category', choices=['staff', 'student'], default='staff',
                      help='Category of devices to sync (staff or student)')
    parser.add_argument('--smart-group', type=int,
                      help='Jamf Smart Group ID to filter devices (optional)')
    args = parser.parse_args()
    
    category = CATEGORIES[args.category]
    print(f"\nSyncing {category['name']} devices...")
    
    print("\nStep 1: Fetching devices from Jamf...")
    devices = fetch_jamf_devices(args.smart_group)
    print(f"Found {len(devices)} devices")
    
    print("\nStep 2: Syncing devices to Snipe-IT...")
    successful = 0
    failed = 0
    for device in devices:
        retries = 0
        while retries < 3:  # Try up to 3 times
            if sync_device(device, category['id']):
                successful += 1
                break
            retries += 1
            time.sleep(5)  # Wait 5 seconds between retries
        else:
            failed += 1
        time.sleep(2)  # Wait 2 seconds between devices
    
    print("\nSync Summary:")
    print(f"Total devices from Jamf: {len(devices)}")
    print(f"Successfully synced: {successful}")
    print(f"Failed to sync: {failed}")

if __name__ == "__main__":
    main() 