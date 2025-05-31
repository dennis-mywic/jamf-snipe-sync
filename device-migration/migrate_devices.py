import os
import requests
import json
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

# Kandji API Configuration
KANDJI_API_TOKEN=os.getenv('KANDJI_API_TOKEN')
KANDJI_BASE_URL=os.getenv('KANDJI_BASE_URL')

# Jamf API Configuration (Bearer Token)
JAMF_CLIENT_ID=os.getenv('JAMF_CLIENT_ID')
JAMF_CLIENT_SECRET=os.getenv('JAMF_CLIENT_SECRET')
JAMF_BASE_URL=os.getenv('JAMF_BASE_URL')

# Snipe-IT Configuration
SNIPE_API_TOKEN=os.getenv('SNIPE_API_TOKEN')
SNIPE_BASE_URL=os.getenv('SNIPE_BASE_URL')

class DeviceMigrator:
    def __init__(self):
        # Snipe-IT configuration
        self.snipe_token = SNIPE_API_TOKEN
        self.snipe_base_url = SNIPE_BASE_URL
        
        # Kandji configuration
        self.kandji_token = KANDJI_API_TOKEN
        self.kandji_base_url = KANDJI_BASE_URL
        
        # Jamf configuration (Bearer Token)
        self.jamf_client_id = JAMF_CLIENT_ID
        self.jamf_client_secret = JAMF_CLIENT_SECRET
        self.jamf_base_url = JAMF_BASE_URL
        self.jamf_token = None

    def get_jamf_token(self):
        url = f"{self.jamf_base_url}/api/oauth/token"
        data = {"grant_type": "client_credentials"}
        response = requests.post(
            url,
            data=data,
            auth=(self.jamf_client_id, self.jamf_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        self.jamf_token = response.json()["access_token"]
        return self.jamf_token

    def test_connections(self):
        """Test connections to all APIs"""
        results = {
            'kandji': self._test_kandji_connection(),
            'jamf': self._test_jamf_connection(),
            'snipe': self._test_snipe_connection()
        }
        return results

    def _test_kandji_connection(self):
        """Test connection to Kandji API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.kandji_token}',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                f'{self.kandji_base_url}/api/v1/devices',
                headers=headers
            )
            return {
                'success': response.status_code == 200,
                'message': 'Connected successfully' if response.status_code == 200 else f'Failed with status {response.status_code}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}'
            }

    def _test_jamf_connection(self):
        """Test connection to Jamf API"""
        try:
            token = self.get_jamf_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            response = requests.get(
                f"{self.jamf_base_url}/api/v1/computers-inventory",
                headers=headers
            )
            return {
                'success': response.status_code == 200,
                'message': 'Connected successfully' if response.status_code == 200 else f'Failed with status {response.status_code}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}'
            }

    def _test_snipe_connection(self):
        """Test connection to Snipe-IT API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.snipe_token}',
                'Accept': 'application/json'
            }
            response = requests.get(
                f'{self.snipe_base_url}/api/v1/hardware',
                headers=headers
            )
            return {
                'success': response.status_code == 200,
                'message': 'Connected successfully' if response.status_code == 200 else f'Failed with status {response.status_code}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}'
            }

    def get_kandji_devices(self):
        """Fetch devices from Kandji API"""
        headers = {
            'Authorization': f'Bearer {self.kandji_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'{self.kandji_base_url}/api/v1/devices',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch Kandji devices: {response.text}")

    def get_jamf_devices(self):
        """Fetch devices from Jamf API"""
        token = self.get_jamf_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        response = requests.get(
            f"{self.jamf_base_url}/api/v1/computers-inventory",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch Jamf devices: {response.text}")

    def create_snipe_asset(self, device_data, source='kandji'):
        """Create an asset in Snipe-IT"""
        headers = {
            'Authorization': f'Bearer {self.snipe_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Map device data to Snipe-IT fields
        if source == 'kandji':
            payload = {
                'name': device_data.get('device_name'),
                'serial': device_data.get('serial_number'),
                'model_id': self._get_snipe_model_id(device_data.get('model')),
                'status_id': 1,  # Ready to Deploy
                'notes': f'Migrated from Kandji on {datetime.now().isoformat()}'
            }
        else:  # jamf
            payload = {
                'name': device_data.get('general', {}).get('name'),
                'serial': device_data.get('general', {}).get('serialNumber'),
                'model_id': self._get_snipe_model_id(device_data.get('hardware', {}).get('model')),  # Adjust as needed
                'status_id': 1,  # Ready to Deploy
                'notes': f'Migrated from Jamf on {datetime.now().isoformat()}'
            }
        
        response = requests.post(
            f'{self.snipe_base_url}/api/v1/hardware',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to create Snipe-IT asset: {response.text}")

    def _get_snipe_model_id(self, model_name):
        """Get Snipe-IT model ID for a given model name"""
        # This is a placeholder - you'll need to implement the actual model mapping
        # or fetch the model ID from Snipe-IT's API
        return 1  # Default model ID

    def migrate_kandji_devices(self):
        """Migrate all devices from Kandji to Snipe-IT"""
        devices = self.get_kandji_devices()
        results = []
        
        for device in devices:
            try:
                result = self.create_snipe_asset(device, 'kandji')
                results.append({
                    'device_name': device.get('device_name'),
                    'status': 'success',
                    'message': 'Successfully migrated'
                })
            except Exception as e:
                results.append({
                    'device_name': device.get('device_name'),
                    'status': 'error',
                    'message': str(e)
                })
        
        return results

    def migrate_jamf_devices(self):
        """Migrate all devices from Jamf to Snipe-IT"""
        devices = self.get_jamf_devices()
        results = []
        
        for device in devices.get('results', []):
            try:
                result = self.create_snipe_asset(device, 'jamf')
                results.append({
                    'device_name': device.get('general', {}).get('name'),
                    'status': 'success',
                    'message': 'Successfully migrated'
                })
            except Exception as e:
                results.append({
                    'device_name': device.get('general', {}).get('name'),
                    'status': 'error',
                    'message': str(e)
                })
        
        return results

def main():
    migrator = DeviceMigrator()
    
    # Test connections first
    print("Testing API connections...")
    connection_results = migrator.test_connections()
    
    # Print connection results
    print("\nConnection Test Results:")
    print("-----------------------")
    for system, result in connection_results.items():
        status = "✅" if result['success'] else "❌"
        print(f"{status} {system.upper()}: {result['message']}")
    
    # Only proceed if all connections are successful
    if all(result['success'] for result in connection_results.values()):
        print("\nAll connections successful! Proceeding with migration...")
        
        # Migrate Kandji devices
        print("\nMigrating Kandji devices...")
        kandji_results = migrator.migrate_kandji_devices()
        
        # Migrate Jamf devices
        print("\nMigrating Jamf devices...")
        jamf_results = migrator.migrate_jamf_devices()
        
        # Save results to CSV
        all_results = kandji_results + jamf_results
        df = pd.DataFrame(all_results)
        df.to_csv('migration_results.csv', index=False)
        
        print(f"\nMigration complete. Results saved to migration_results.csv")
    else:
        print("\n❌ Some connections failed. Please check your API credentials and try again.")

if __name__ == "__main__":
    main() 