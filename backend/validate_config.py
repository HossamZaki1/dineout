#!/usr/bin/env python3
"""
Validate configuration for the multi-agent system
"""

import os
from dotenv import load_dotenv

def validate_config():
    """Validate all required configuration"""
    print("🔍 Validating configuration...")
    
    # Load environment variables
    load_dotenv()
    
    # Required configurations
    config_checks = [
        {
            'name': 'Google API Key',
            'var': 'GOOGLE_API_KEY',
            'required': True,
            'description': 'Required for Gemini and Google Maps Platform'
        },
        {
            'name': 'Server Host',
            'var': 'HOST',
            'required': False,
            'default': '0.0.0.0',
            'description': 'FastAPI server host'
        },
        {
            'name': 'Server Port',
            'var': 'PORT',
            'required': False,
            'default': '8000',
            'description': 'FastAPI server port'
        }
    ]
    
    all_valid = True
    
    for check in config_checks:
        value = os.getenv(check['var'])
        
        if check['required'] and not value:
            print(f"❌ {check['name']} ({check['var']}): MISSING - {check['description']}")
            all_valid = False
        elif check['required'] and value:
            # Mask sensitive values
            display_value = value[:8] + "..." if len(value) > 8 else value
            if 'API_KEY' in check['var']:
                display_value = f"{value[:8]}{'*' * (len(value) - 8)}"
            print(f"✅ {check['name']} ({check['var']}): {display_value}")
        elif not check['required']:
            actual_value = value or check.get('default', 'Not set')
            print(f"🔧 {check['name']} ({check['var']}): {actual_value}")
    
    print(f"\n📊 Configuration Status: {'✅ VALID' if all_valid else '❌ INVALID'}")
    
    if not all_valid:
        print("\n💡 To fix missing configuration:")
        print("1. Check your .env file in the backend directory")
        print("2. Ensure GOOGLE_API_KEY is set")
        
    return all_valid

if __name__ == "__main__":
    validate_config()
