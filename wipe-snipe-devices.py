#!/usr/bin/env python3
"""
Snipe-IT Device Cleanup Script
WARNING: This will delete ALL hardware assets in Snipe-IT
"""

import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

headers = {
    'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

def get_all_assets():
    """Get all hardware assets from Snipe-IT"""
    all_assets = []
    page = 0
    limit = 100
    
    while True:
        response = requests.get(
            f'{SNIPE_IT_URL}/api/v1/hardware',
            headers=headers,
            params={'offset': page * limit, 'limit': limit}
        )
        
        if response.status_code != 200:
            print(f"Error fetching assets: {response.status_code} - {response.text}")
            break
            
        data = response.json()
        assets = data.get('rows', [])
        
        if not assets:
            break
            
        all_assets.extend(assets)
        page += 1
        
        print(f"Fetched page {page}: {len(assets)} assets (Total: {len(all_assets)})")
        
        # Rate limiting
        time.sleep(0.1)
    
    return all_assets

def delete_asset(asset_id, asset_name):
    """Delete a single asset"""
    try:
        response = requests.delete(
            f'{SNIPE_IT_URL}/api/v1/hardware/{asset_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"✅ Deleted: {asset_name} (ID: {asset_id})")
            return True
        else:
            print(f"❌ Failed to delete {asset_name} (ID: {asset_id}): {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting {asset_name} (ID: {asset_id}): {str(e)}")
        return False

def main():
    print("=== SNIPE-IT DEVICE CLEANUP ===")
    print(f"Connecting to: {SNIPE_IT_URL}")
    print("⚠️  WARNING: This will delete ALL hardware assets!")
    print("This action cannot be undone.")
    
    # Get confirmation
    confirm = input("\nType 'DELETE ALL' to confirm: ")
    if confirm != 'DELETE ALL':
        print("Operation cancelled.")
        return
    
    print("\nFetching all assets...")
    assets = get_all_assets()
    
    if not assets:
        print("No assets found.")
        return
    
    print(f"\nFound {len(assets)} assets to delete.")
    print("Starting deletion...")
    
    deleted_count = 0
    failed_count = 0
    
    for i, asset in enumerate(assets, 1):
        asset_id = asset.get('id')
        asset_name = asset.get('name', 'Unknown')
        asset_tag = asset.get('asset_tag', 'No Tag')
        
        print(f"[{i}/{len(assets)}] Deleting {asset_name} ({asset_tag})...")
        
        if delete_asset(asset_id, asset_name):
            deleted_count += 1
        else:
            failed_count += 1
        
        # Rate limiting to avoid overwhelming the API
        time.sleep(0.2)
    
    print(f"\n=== CLEANUP COMPLETE ===")
    print(f"Successfully deleted: {deleted_count}")
    print(f"Failed to delete: {failed_count}")
    print(f"Total processed: {len(assets)}")

if __name__ == '__main__':
    main()
