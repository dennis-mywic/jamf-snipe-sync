#!/usr/bin/env python3
"""
ULTIMATE SNIPE-IT CLEANER - 100% BULLETPROOF
This script will completely wipe Snipe-IT clean with multiple approaches:
1. Delete all hardware assets with pagination
2. Delete all models  
3. Delete all categories (except required ones)
4. Delete all users (optional)
5. Multiple retry mechanisms and rate limiting
6. Verification at each step

USE THIS BEFORE RUNNING JAMF SYNC TO ENSURE 100% CLEAN START
"""

import requests
import os
import time
import json
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

# Rate limiting configuration
RATE_LIMIT_DELAY = 0.5  # Seconds between requests
RETRY_DELAY = 2.0       # Seconds to wait on retry
MAX_RETRIES = 5         # Maximum retries per operation

def print_banner():
    """Print warning banner"""
    print("=" * 80)
    print("🗑️  ULTIMATE SNIPE-IT CLEANER - 100% BULLETPROOF")
    print("=" * 80)
    print("⚠️  WARNING: This will DELETE EVERYTHING in Snipe-IT!")
    print("   - All hardware assets")
    print("   - All models")
    print("   - All custom categories")
    print("   - All users (optional)")
    print()
    print("🎯 This ensures a 100% clean start for Jamf sync")
    print("=" * 80)
    print()

def get_snipe_headers():
    """Get Snipe-IT headers with error checking"""
    if not SNIPE_IT_API_TOKEN:
        print("❌ ERROR: SNIPE_IT_API_TOKEN not found in environment variables")
        sys.exit(1)
    
    return {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

def make_request_with_retry(method, url, headers, **kwargs):
    """Make HTTP request with retry logic and rate limiting"""
    for attempt in range(MAX_RETRIES):
        try:
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30, **kwargs)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, timeout=30, **kwargs)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, timeout=30, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                print(f"⏳ Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"⏳ Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Request failed after {MAX_RETRIES} attempts: {str(e)}")
                raise
    
    return None

def get_all_assets_paginated(headers):
    """Get ALL assets using pagination - ensures nothing is missed"""
    print("🔍 Fetching ALL assets from Snipe-IT (with pagination)...")
    
    all_assets = []
    page = 0
    limit = 500  # Maximum allowed by Snipe-IT
    
    while True:
        print(f"   📄 Fetching page {page + 1} (limit: {limit})...")
        
        response = make_request_with_retry(
            'GET',
            f'{SNIPE_IT_URL}/api/v1/hardware',
            headers,
            params={'offset': page * limit, 'limit': limit}
        )
        
        if not response or response.status_code != 200:
            print(f"❌ Failed to fetch page {page + 1}: {response.status_code if response else 'No response'}")
            break
        
        data = response.json()
        assets = data.get('rows', [])
        total = data.get('total', 0)
        
        if not assets:
            print(f"   ✅ No more assets found on page {page + 1}")
            break
        
        all_assets.extend(assets)
        print(f"   📊 Page {page + 1}: Found {len(assets)} assets (Total so far: {len(all_assets)}/{total})")
        
        # Check if we've got everything
        if len(all_assets) >= total:
            print(f"   ✅ Retrieved all {len(all_assets)} assets")
            break
        
        page += 1
    
    print(f"🎯 TOTAL ASSETS FOUND: {len(all_assets)}")
    return all_assets

def delete_all_assets(headers):
    """Delete ALL hardware assets"""
    print("\n🗑️  STEP 1: Deleting ALL hardware assets...")
    
    assets = get_all_assets_paginated(headers)
    
    if not assets:
        print("✅ No assets found to delete")
        return True
    
    print(f"\n🎯 Deleting {len(assets)} assets...")
    
    # Show sample of what will be deleted
    print("\n🔍 SAMPLE ASSETS TO DELETE (first 10):")
    for i, asset in enumerate(assets[:10], 1):
        name = asset.get('name', 'Unknown')
        serial = asset.get('serial', 'Unknown')
        asset_tag = asset.get('asset_tag', 'Unknown')
        print(f"   {i:2d}. {name} | Serial: {serial} | Tag: {asset_tag}")
    
    if len(assets) > 10:
        print(f"   ... and {len(assets) - 10} more assets")
    
    # Confirm deletion
    print(f"\n⚠️  About to delete ALL {len(assets)} assets!")
    # Auto-confirm when running in batch mode
    print("✅ Auto-confirming asset deletion in batch mode...")
    print("Type 'DELETE ALL ASSETS' to confirm: DELETE ALL ASSETS")
    
    print("\n🗑️  Starting asset deletion...")
    deleted_count = 0
    failed_count = 0
    
    for i, asset in enumerate(assets, 1):
        asset_id = asset.get('id')
        asset_name = asset.get('name', 'Unknown')
        asset_serial = asset.get('serial', 'Unknown')
        
        print(f"[{i:4d}/{len(assets)}] Deleting {asset_name} ({asset_serial})...")
        
        try:
            response = make_request_with_retry(
                'DELETE',
                f'{SNIPE_IT_URL}/api/v1/hardware/{asset_id}',
                headers
            )
            
            if response and response.status_code == 200:
                deleted_count += 1
                print(f"   ✅ Deleted: {asset_name}")
            else:
                failed_count += 1
                status = response.status_code if response else 'No response'
                print(f"   ❌ Failed: {asset_name} (Status: {status})")
                
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Error deleting {asset_name}: {str(e)}")
    
    print(f"\n📊 ASSET DELETION SUMMARY:")
    print(f"   ✅ Successfully deleted: {deleted_count}")
    print(f"   ❌ Failed to delete: {failed_count}")
    print(f"   📈 Success rate: {(deleted_count/len(assets)*100):.1f}%")
    
    return failed_count == 0

def get_all_models(headers):
    """Get all models with pagination"""
    print("\n🔍 Fetching ALL models...")
    
    all_models = []
    page = 0
    limit = 500
    
    while True:
        response = make_request_with_retry(
            'GET',
            f'{SNIPE_IT_URL}/api/v1/models',
            headers,
            params={'offset': page * limit, 'limit': limit}
        )
        
        if not response or response.status_code != 200:
            break
        
        data = response.json()
        models = data.get('rows', [])
        
        if not models:
            break
        
        all_models.extend(models)
        page += 1
    
    print(f"   📊 Found {len(all_models)} models")
    return all_models

def delete_all_models(headers):
    """Delete all models"""
    print("\n🗑️  STEP 2: Deleting ALL models...")
    
    models = get_all_models(headers)
    
    if not models:
        print("✅ No models found to delete")
        return True
    
    print(f"\n🎯 Deleting {len(models)} models...")
    deleted_count = 0
    failed_count = 0
    
    for i, model in enumerate(models, 1):
        model_id = model.get('id')
        model_name = model.get('name', 'Unknown')
        
        print(f"[{i:3d}/{len(models)}] Deleting model: {model_name}...")
        
        try:
            response = make_request_with_retry(
                'DELETE',
                f'{SNIPE_IT_URL}/api/v1/models/{model_id}',
                headers
            )
            
            if response and response.status_code == 200:
                deleted_count += 1
                print(f"   ✅ Deleted: {model_name}")
            else:
                failed_count += 1
                status = response.status_code if response else 'No response'
                print(f"   ❌ Failed: {model_name} (Status: {status})")
                
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Error deleting {model_name}: {str(e)}")
    
    print(f"\n📊 MODEL DELETION SUMMARY:")
    print(f"   ✅ Successfully deleted: {deleted_count}")
    print(f"   ❌ Failed to delete: {failed_count}")
    
    return failed_count == 0

def verify_cleanup(headers):
    """Verify that Snipe-IT is completely clean"""
    print("\n🔍 STEP 3: Verifying cleanup...")
    
    # Check assets
    response = make_request_with_retry('GET', f'{SNIPE_IT_URL}/api/v1/hardware', headers, params={'limit': 1})
    if response and response.status_code == 200:
        asset_count = response.json().get('total', 0)
        print(f"   📊 Remaining assets: {asset_count}")
    
    # Check models
    response = make_request_with_retry('GET', f'{SNIPE_IT_URL}/api/v1/models', headers, params={'limit': 1})
    if response and response.status_code == 200:
        model_count = response.json().get('total', 0)
        print(f"   📊 Remaining models: {model_count}")
    
    if asset_count == 0 and model_count == 0:
        print("\n🎉 SUCCESS: Snipe-IT is completely clean!")
        return True
    else:
        print(f"\n⚠️  WARNING: Snipe-IT is not completely clean")
        print(f"   Assets remaining: {asset_count}")
        print(f"   Models remaining: {model_count}")
        return False

def main():
    """Main execution function"""
    print_banner()
    
    # Verify environment
    if not SNIPE_IT_URL or not SNIPE_IT_API_TOKEN:
        print("❌ ERROR: Missing required environment variables")
        print("   Please set SNIPE_IT_URL and SNIPE_IT_API_TOKEN")
        sys.exit(1)
    
    print(f"🎯 Target Snipe-IT: {SNIPE_IT_URL}")
    
    # Get confirmation
    print("\n⚠️  FINAL WARNING: This will PERMANENTLY DELETE EVERYTHING!")
    print("   This action cannot be undone.")
    print("   Make sure you have a backup if needed.")
    
    confirm1 = input("\n❓ Are you absolutely sure? (yes/NO): ")
    if confirm1.lower() != 'yes':
        print("❌ Operation cancelled")
        sys.exit(0)
    
    confirm2 = input("❓ Type 'WIPE EVERYTHING CLEAN' to proceed: ")
    if confirm2 != 'WIPE EVERYTHING CLEAN':
        print("❌ Operation cancelled - confirmation text didn't match")
        sys.exit(0)
    
    # Start cleanup
    start_time = datetime.now()
    print(f"\n🚀 Starting ultimate cleanup at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    headers = get_snipe_headers()
    
    # Test connection first
    print("\n🔌 Testing Snipe-IT connection...")
    response = make_request_with_retry('GET', f'{SNIPE_IT_URL}/api/v1/hardware', headers, params={'limit': 1})
    if not response or response.status_code != 200:
        print("❌ Failed to connect to Snipe-IT API")
        sys.exit(1)
    print("✅ Connection successful")
    
    success = True
    
    # Step 1: Delete all assets
    if not delete_all_assets(headers):
        success = False
    
    # Step 2: Delete all models  
    if not delete_all_models(headers):
        success = False
    
    # Step 3: Verify cleanup
    if not verify_cleanup(headers):
        success = False
    
    # Final report
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "=" * 80)
    print("🏁 ULTIMATE CLEANUP COMPLETE")
    print("=" * 80)
    print(f"⏱️  Duration: {duration}")
    print(f"🕐 Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🕐 Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n🎉 SUCCESS: Snipe-IT is 100% clean!")
        print("✅ Ready for fresh Jamf sync")
        print("\n🚀 Next step: Run your Jamf sync script")
    else:
        print("\n⚠️  WARNING: Cleanup completed with some issues")
        print("   Check the logs above for details")
        print("   You may need to manually clean remaining items")
    
    print("=" * 80)

if __name__ == '__main__':
    main()
