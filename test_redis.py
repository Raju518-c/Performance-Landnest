#!/usr/bin/env python
"""
Test script to verify Redis cache configuration
"""
import os
import django

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landnest.settings')
django.setup()

from django.core.cache import cache

def test_redis_connection():
    """Test Redis cache connection"""
    try:
        # Test set and get
        cache.set('test_key', 'test_value', 60)
        value = cache.get('test_key')
        
        if value == 'test_value':
            print("✅ Redis cache is working correctly!")
            print(f"✅ Successfully stored and retrieved: {value}")
            
            # Clean up
            cache.delete('test_key')
            print("✅ Test key cleaned up")
            return True
        else:
            print("❌ Redis cache test failed - value mismatch")
            return False
            
    except Exception as e:
        print(f"❌ Redis cache connection failed: {e}")
        print("📝 Make sure Redis server is running on localhost:6379")
        return False

if __name__ == "__main__":
    print("Testing Redis cache configuration...")
    test_redis_connection()
