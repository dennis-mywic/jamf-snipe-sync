#!/usr/bin/env python3
"""
Connection Test Script
=====================
Tests API connections to Jamf Pro and Snipe-IT before running the full sync.
"""

import os
import sys
import requests
from dotenv import load_dotenv
from typing import Tuple

# Load environment
load_dotenv()

# Configuration
JAMF_URL = os.getenv('JAMF_URL')
JAMF_CLIENT_ID = os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET = os.getenv('JAMF_CLIENT_SECRET')
SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def test_env_vars() -> bool:
    """Test that all required environment variables are set"""
    print_header("1. Testing Environment Variables")
    
    required_vars = {
        'JAMF_URL': JAMF_URL,
        'JAMF_CLIENT_ID': JAMF_CLIENT_ID,
        'JAMF_CLIENT_SECRET': JAMF_CLIENT_SECRET,
        'SNIPE_IT_URL': SNIPE_IT_URL,
        'SNIPE_IT_API_TOKEN': SNIPE_IT_API_TOKEN
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            # Mask sensitive values
            if 'SECRET' in var_name or 'TOKEN' in var_name:
                display_value = var_value[:10] + '...' if len(var_value) > 10 else '***'
            else:
                display_value = var_value
            print(f"  ✅ {var_name}: {display_value}")
        else:
            print(f"  ❌ {var_name}: NOT SET")
            all_set = False
    
    if all_set:
        print("\n✅ All environment variables are set")
    else:
        print("\n❌ Some environment variables are missing")
        print("\nPlease create a .env file with:")
        print("  JAMF_URL=https://your-jamf-instance.jamfcloud.com")
        print("  JAMF_CLIENT_ID=your_client_id")
        print("  JAMF_CLIENT_SECRET=your_client_secret")
        print("  SNIPE_IT_URL=https://your-snipe-it-instance.com")
        print("  SNIPE_IT_API_TOKEN=your_api_token")
    
    return all_set

def test_jamf_auth() -> Tuple[bool, str]:
    """Test Jamf Pro authentication"""
    print_header("2. Testing Jamf Pro Authentication")
    
    try:
        print(f"  Connecting to: {JAMF_URL}")
        print(f"  Using Client ID: {JAMF_CLIENT_ID[:10]}...")
        
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
        
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"\n✅ Successfully authenticated with Jamf Pro")
            print(f"  Token received: {token[:20]}...")
            return True, token
        else:
            print(f"\n❌ Authentication failed")
            print(f"  Status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"\n❌ Error connecting to Jamf Pro: {str(e)}")
        return False, None

def test_jamf_computers(token: str) -> bool:
    """Test fetching computers from Jamf"""
    print_header("3. Testing Jamf Pro Computer Access")
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        print(f"  Fetching computers from Jamf Pro...")
        
        response = requests.get(
            f"{JAMF_URL}/api/v1/computers-inventory",
            headers=headers,
            params={'page': 0, 'page-size': 10},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('totalCount', 0)
            results = data.get('results', [])
            print(f"\n✅ Successfully fetched computer data")
            print(f"  Total computers: {total}")
            print(f"  Sample retrieved: {len(results)}")
            
            if results:
                sample = results[0]
                general = sample.get('general', {})
                print(f"  Sample device: {general.get('name', 'Unknown')}")
            
            return True
        else:
            print(f"\n❌ Failed to fetch computers")
            print(f"  Status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error fetching computers: {str(e)}")
        return False

def test_jamf_mobile(token: str) -> bool:
    """Test fetching mobile devices from Jamf"""
    print_header("4. Testing Jamf Pro Mobile Device Access")
    
    try:
        headers = {'Authorization': f'Bearer {token}'}
        print(f"  Fetching mobile devices from Jamf Pro...")
        
        response = requests.get(
            f"{JAMF_URL}/api/v2/mobile-devices",
            headers=headers,
            params={'page': 0, 'page-size': 10},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('totalCount', 0)
            results = data.get('results', [])
            print(f"\n✅ Successfully fetched mobile device data")
            print(f"  Total mobile devices: {total}")
            print(f"  Sample retrieved: {len(results)}")
            
            if results:
                sample = results[0]
                print(f"  Sample device: {sample.get('name', 'Unknown')} ({sample.get('serialNumber', 'No Serial')})")
            
            return True
        else:
            print(f"\n❌ Failed to fetch mobile devices")
            print(f"  Status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error fetching mobile devices: {str(e)}")
        return False

def test_snipe_auth() -> bool:
    """Test Snipe-IT authentication"""
    print_header("5. Testing Snipe-IT Authentication")
    
    try:
        headers = {
            'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        print(f"  Connecting to: {SNIPE_IT_URL}")
        print(f"  Using API Token: {SNIPE_IT_API_TOKEN[:10]}...")
        
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/hardware",
            headers=headers,
            params={'limit': 1},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"\n✅ Successfully authenticated with Snipe-IT")
            print(f"  Total assets in Snipe-IT: {total}")
            return True
        else:
            print(f"\n❌ Authentication failed")
            print(f"  Status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error connecting to Snipe-IT: {str(e)}")
        return False

def test_snipe_models() -> bool:
    """Test Snipe-IT model access"""
    print_header("6. Testing Snipe-IT Model Access")
    
    try:
        headers = {
            'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        print(f"  Fetching models from Snipe-IT...")
        
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/models",
            headers=headers,
            params={'limit': 10},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            rows = data.get('rows', [])
            print(f"\n✅ Successfully fetched model data")
            print(f"  Total models: {total}")
            print(f"  Sample retrieved: {len(rows)}")
            
            if rows:
                sample = rows[0]
                print(f"  Sample model: {sample.get('name', 'Unknown')}")
            
            return True
        else:
            print(f"\n❌ Failed to fetch models")
            print(f"  Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error fetching models: {str(e)}")
        return False

def test_snipe_users() -> bool:
    """Test Snipe-IT user access"""
    print_header("7. Testing Snipe-IT User Access")
    
    try:
        headers = {
            'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        print(f"  Fetching users from Snipe-IT...")
        
        response = requests.get(
            f"{SNIPE_IT_URL}/api/v1/users",
            headers=headers,
            params={'limit': 10},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            rows = data.get('rows', [])
            print(f"\n✅ Successfully fetched user data")
            print(f"  Total users: {total}")
            print(f"  Sample retrieved: {len(rows)}")
            
            if rows:
                sample = rows[0]
                print(f"  Sample user: {sample.get('name', 'Unknown')}")
            
            return True
        else:
            print(f"\n❌ Failed to fetch users")
            print(f"  Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error fetching users: {str(e)}")
        return False

def main():
    """Run all connection tests"""
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "JAMF TO SNIPE-IT CONNECTION TEST" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    
    results = {
        'Environment': False,
        'Jamf Auth': False,
        'Jamf Computers': False,
        'Jamf Mobile': False,
        'Snipe-IT Auth': False,
        'Snipe-IT Models': False,
        'Snipe-IT Users': False
    }
    
    # Test environment variables
    results['Environment'] = test_env_vars()
    if not results['Environment']:
        print_summary(results)
        sys.exit(1)
    
    # Test Jamf authentication
    jamf_success, jamf_token = test_jamf_auth()
    results['Jamf Auth'] = jamf_success
    
    if jamf_success:
        # Test Jamf data access
        results['Jamf Computers'] = test_jamf_computers(jamf_token)
        results['Jamf Mobile'] = test_jamf_mobile(jamf_token)
    
    # Test Snipe-IT
    results['Snipe-IT Auth'] = test_snipe_auth()
    
    if results['Snipe-IT Auth']:
        results['Snipe-IT Models'] = test_snipe_models()
        results['Snipe-IT Users'] = test_snipe_users()
    
    # Print summary
    print_summary(results)
    
    # Exit with appropriate code
    if all(results.values()):
        print("\n🎉 ALL TESTS PASSED - Ready to run sync!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed - Fix issues before running sync")
        sys.exit(1)

def print_summary(results: dict):
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All systems operational - Ready for sync!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Fix issues before syncing")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

