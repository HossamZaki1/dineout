#!/usr/bin/env python3
"""
Test script to verify ChromaDB Cloud connection
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.storage.chroma_storage import ChromaStorage

async def test_chroma_connection():
    """Test ChromaDB Cloud connection"""
    print("Testing ChromaDB Cloud connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = ['CHROMA_API_KEY', 'CHROMA_TENANT', 'CHROMA_DATABASE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    try:
        # Initialize storage
        storage = ChromaStorage()
        await storage.initialize()
        
        print("✅ Successfully connected to ChromaDB Cloud")
        print(f"   Collection: {storage.collection_name}")
        print(f"   Tenant: {os.getenv('CHROMA_TENANT')}")
        print(f"   Database: {os.getenv('CHROMA_DATABASE')}")
        
        # Test basic operations
        print("\nTesting basic operations...")
        
        # Test storing a sample analysis
        sample_analysis = {
            "summary": "Test analysis for connection verification",
            "confidence_score": 0.9,
            "alternatives": [],
            "risk_level": "low"
        }
        
        await storage.store_action_analysis(
            "Test action",
            "Test situation", 
            sample_analysis,
            "test-session-123"
        )
        print("✅ Successfully stored test analysis")
        
        # Test finding similar actions
        similar = await storage.find_similar_actions(
            "Test action",
            "Test situation",
            limit=3
        )
        print(f"✅ Successfully retrieved {len(similar)} similar actions")
        
        # Test analytics
        analytics = await storage.get_analytics()
        print(f"✅ Successfully retrieved analytics: {analytics.get('total_actions', 0)} total actions")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to ChromaDB Cloud: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_chroma_connection())
    if success:
        print("\n🎉 ChromaDB Cloud connection test passed!")
        sys.exit(0)
    else:
        print("\n💥 ChromaDB Cloud connection test failed!")
        sys.exit(1)
