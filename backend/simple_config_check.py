#!/usr/bin/env python3
"""
Simple configuration check without external dependencies
"""

import os

def check_env_file():
    """Check if .env file exists and contains required variables"""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("❌ .env file not found")
        return False
    
    print("✅ .env file found")
    
    # Read the file and check for required variables
    required_vars = [
        'OPENAI_API_KEY',
        'CHROMA_API_KEY', 
        'CHROMA_TENANT',
        'CHROMA_DATABASE'
    ]
    
    found_vars = {}
    
    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                found_vars[key] = value
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False
    
    print("\n🔍 Configuration Status:")
    all_good = True
    
    for var in required_vars:
        if var in found_vars and found_vars[var]:
            if var in ['OPENAI_API_KEY', 'CHROMA_API_KEY']:
                masked_value = found_vars[var][:8] + "*" * (len(found_vars[var]) - 8)
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {found_vars[var]}")
        else:
            print(f"❌ {var}: MISSING")
            all_good = False
    
    # Show ChromaDB Cloud settings
    print(f"\n📡 ChromaDB Cloud Configuration:")
    print(f"   Host: {found_vars.get('CHROMA_HOST', 'api.trychroma.com')}")
    print(f"   Port: {found_vars.get('CHROMA_PORT', '443')}")
    print(f"   SSL: {found_vars.get('CHROMA_SSL', 'true')}")
    
    if all_good:
        print(f"\n🎉 Configuration looks good! You're ready to use ChromaDB Cloud.")
    else:
        print(f"\n💥 Configuration incomplete. Please check your .env file.")
        
    return all_good

if __name__ == "__main__":
    check_env_file()
