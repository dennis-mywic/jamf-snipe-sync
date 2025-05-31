from migrate_devices import DeviceMigrator

def main():
    print("Testing API Connections")
    print("======================")
    
    migrator = DeviceMigrator()
    results = migrator.test_connections()
    
    for system, result in results.items():
        status = "✅" if result['success'] else "❌"
        print(f"\n{status} {system.upper()}:")
        print(f"   {result['message']}")

if __name__ == "__main__":
    main() 