#!/usr/bin/env python3
"""
Fix Apple models incorrectly assigned to Lenovo manufacturer
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SNIPE_IT_URL = os.getenv('SNIPE_IT_URL')
SNIPE_IT_API_TOKEN = os.getenv('SNIPE_IT_API_TOKEN')

def fix_apple_model_manufacturers():
    """Fix Apple models incorrectly assigned to Lenovo manufacturer"""
    
    snipe_headers = {
        'Authorization': f'Bearer {SNIPE_IT_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    print("🔧 FIXING APPLE MODEL MANUFACTURER ASSIGNMENTS")
    print("=" * 50)
    
    # Get all models
    response = requests.get(
        f'{SNIPE_IT_URL}/api/v1/models',
        headers=snipe_headers,
        params={'limit': 500}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get models: {response.status_code}")
        return
    
    models = response.json().get('rows', [])
    
    # Find Apple models with wrong manufacturer
    apple_models_to_fix = []
    
    for model in models:
        manufacturer = model.get('manufacturer', {})
        manufacturer_name = manufacturer.get('name', '') if manufacturer else ''
        manufacturer_id = manufacturer.get('id') if manufacturer else None
        
        model_name = model.get('name', '')
        
        # Check if this is an Apple model with wrong manufacturer
        is_apple_model = any(apple_term in model_name.lower() for apple_term in [
            'ipad', 'macbook', 'imac', 'mac mini', 'mac studio', 'apple tv'
        ])
        
        if is_apple_model and manufacturer_id == 1:  # Lenovo manufacturer ID
            apple_models_to_fix.append({
                'id': model.get('id'),
                'name': model_name,
                'current_manufacturer': manufacturer_name,
                'current_manufacturer_id': manufacturer_id
            })
    
    print(f"Found {len(apple_models_to_fix)} Apple models with incorrect manufacturer")
    
    if not apple_models_to_fix:
        print("✅ No models need fixing!")
        return
    
    # Show models to fix
    print("\n🔍 MODELS TO FIX:")
    for i, model in enumerate(apple_models_to_fix, 1):
        print(f"{i:2d}. {model['name']} (ID: {model['id']})")
    
    # Ask for confirmation
    confirm = input(f"\n❓ Fix manufacturer for {len(apple_models_to_fix)} models? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Cancelled")
        return
    
    # Fix each model
    success_count = 0
    failed_count = 0
    
    for model in apple_models_to_fix:
        model_id = model['id']
        
        # Update model to use Apple manufacturer (ID: 9)
        update_data = {
            'manufacturer_id': 9  # Apple manufacturer ID
        }
        
        try:
            update_response = requests.patch(
                f'{SNIPE_IT_URL}/api/v1/models/{model_id}',
                headers=snipe_headers,
                json=update_data,
                timeout=30
            )
            
            if update_response.status_code == 200:
                print(f"✅ Fixed: {model['name']}")
                success_count += 1
            else:
                print(f"❌ Failed: {model['name']} - {update_response.status_code}")
                print(f"   Response: {update_response.text[:200]}")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ Error fixing {model['name']}: {str(e)}")
            failed_count += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 MODEL MANUFACTURER FIX COMPLETE")
    print(f"✅ Successfully fixed: {success_count} models")
    print(f"❌ Failed to fix: {failed_count} models")
    
    if success_count > 0:
        print(f"\n🎉 All Apple models should now show 'Apple' as manufacturer!")
        print(f"   This will automatically fix all devices using these models.")

if __name__ == '__main__':
    fix_apple_model_manufacturers()
