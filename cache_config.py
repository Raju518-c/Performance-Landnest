"""
Advanced Cache Configuration - Works with Redis or Django LocMemCache
Supports Redis clustering, connection pooling, and distributed caching
Falls back to Django's local memory cache when Redis is not available
"""

import redis
from redis.cluster import RedisCluster
from django.conf import settings
from django.core.cache import cache
import json
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages cache operations with Redis fallback to Django cache"""
    
    def __init__(self):
        self.redis_available = False
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection if available"""
        try:
            # Try single Redis instance
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True,
                max_connections=1000,
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Redis connected successfully")
        except Exception as e:
            self.redis_available = False
            logger.info(f"Redis not available, using Django cache: {e}")
    
    def get(self, key):
        """Get value from cache with Redis fallback to Django cache"""
        if self.redis_available:
            try:
                result = self.redis_client.get(key)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning(f"Redis get failed, falling back to Django cache: {e}")
                self.redis_available = False
        
        # Fallback to Django cache
        try:
            return cache.get(key)
        except Exception:
            return None
    
    def set(self, key, value, timeout=300):
        """Set value in cache with Redis fallback to Django cache"""
        if self.redis_available:
            try:
                return self.redis_client.setex(key, timeout, value)
            except Exception as e:
                logger.warning(f"Redis set failed, falling back to Django cache: {e}")
                self.redis_available = False
        
        # Fallback to Django cache
        try:
            return cache.set(key, value, timeout)
        except Exception:
            return False
    
    def delete(self, key):
        """Delete key from cache"""
        if self.redis_available:
            try:
                return self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed, falling back to Django cache: {e}")
                self.redis_available = False
        
        # Fallback to Django cache
        try:
            return cache.delete(key)
        except Exception:
            return False
    
    def get_many(self, keys):
        """Get multiple keys efficiently"""
        if self.redis_available:
            try:
                result = self.redis_client.mget(keys)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Redis mget failed, falling back to Django cache: {e}")
                self.redis_available = False
        
        # Fallback to Django cache
        try:
            return cache.get_many(keys)
        except Exception:
            return {}
    
    def set_many(self, mapping, timeout=300):
        """Set multiple keys efficiently"""
        if self.redis_available:
            try:
                pipe = self.redis_client.pipeline()
                for key, value in mapping.items():
                    pipe.setex(key, timeout, value)
                return pipe.execute()
            except Exception as e:
                logger.warning(f"Redis mset failed, falling back to Django cache: {e}")
                self.redis_available = False
        
        # Fallback to Django cache
        try:
            return cache.set_many(mapping, timeout)
        except Exception:
            return False
    
    def increment(self, key, amount=1):
        """Increment counter"""
        if self.redis_available:
            try:
                return self.redis_client.incrby(key, amount)
            except Exception as e:
                logger.warning(f"Redis increment failed, falling back to Django cache: {e}")
                self.redis_available = False
        
        # Fallback to Django cache (manual increment)
        try:
            current = cache.get(key) or 0
            new_value = current + amount
            cache.set(key, new_value)
            return new_value
        except Exception:
            return 0
    
    def exists(self, key):
        """Check if key exists"""
        if self.redis_available:
            try:
                return self.redis_client.exists(key)
            except Exception as e:
                logger.warning(f"Redis exists failed, falling back to Django cache: {e}")
                self.redis_available = False
        
        # Fallback to Django cache
        try:
            return cache.get(key) is not None
        except Exception:
            return False

# Global cache manager instance
cache_manager = CacheManager()
# Global variables for total users count by user_type (initialized on server start)
total_users_count = None
user_type_counts = {
    'Buyer': 0,
    'Tenant': 0,
    'Individual Owner/Builder': 0,
    'Landlord': 0,
    'Builder': 0,
    'Agent': 0,
    'Bank Auction': 0,
    'Old Users': 0  # For users with user_type=None
}

# Cache configuration
CACHE_CONFIG = {
    'default_timeout': 300,  # 5 minutes
    'user_list_timeout': 600,  # 10 minutes for user lists
    'statistics_timeout': 1800,  # 30 minutes for statistics
    'session_timeout': 3600,  # 1 hour for sessions
    'rate_limit_timeout': 60,  # 1 minute for rate limiting
}

class CacheKeyGenerator:
    """Generate optimized cache keys"""
    
    @staticmethod
    def user_list(page, page_size, search, user_type, status, sort_by, sort_order, progressive, offset, chunk_size):
        """Generate cache key for user list"""
        return f"users_list:{page}:{page_size}:{search}:{user_type}:{status}:{sort_by}:{sort_order}:{progressive}:{offset}:{chunk_size}"
    
    @staticmethod
    def user_statistics():
        """Generate cache key for user statistics"""
        return "users:statistics"
    
    @staticmethod
    def rate_limit(user_id, endpoint):
        """Generate cache key for rate limiting"""
        return f"rate_limit:{user_id}:{endpoint}"
    
    @staticmethod
    def session(user_id):
        """Generate cache key for user session"""
        return f"session:{user_id}"
    
    @staticmethod
    def search_results(query, page, page_size):
        """Generate cache key for search results"""
        return f"search:{query}:{page}:{page_size}"

# Advanced cache decorator
def cache_result(timeout=None, key_generator=None):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = f"cache:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                try:
                    return json.loads(cached_result)
                except (json.JSONDecodeError, TypeError):
                    pass  # Invalid cache data, continue with function execution
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_timeout = timeout or CACHE_CONFIG.get('default_timeout', 300)
            
            try:
                result_json = json.dumps(result, default=str)
                cache_manager.set(cache_key, result_json, cache_timeout)
            except Exception as e:
                logger.error(f"Cache serialization error: {e}")
            
            return result
        return wrapper
    return decorator

# Helper functions for user caching
def initialize_total_users_count():
    """Initialize global total users count on server start"""
    global total_users_count, user_type_counts
    try:
        from users.models import User
        total_users_count = User.objects.filter(role='1').count()
        logger.info(f"Initialized total_users_count: {total_users_count}")
        
        # Initialize user_type counts
        initialize_user_type_counts()
    except Exception as e:
        logger.error(f"Failed to initialize total_users_count: {e}")
        total_users_count = 0

def initialize_user_type_counts():
    """Initialize global user_type counts on server start"""
    global user_type_counts
    try:
        from users.models import User
        users = User.objects.filter(role='1')
        
        # Count by user_type
        for user_type in user_type_counts:
            if user_type == 'Old Users':
                user_type_counts[user_type] = users.filter(user_type=None).count()
            else:
                user_type_counts[user_type] = users.filter(user_type=user_type).count()
        
        logger.info(f"Initialized user_type_counts: {user_type_counts}")
    except Exception as e:
        logger.error(f"Failed to initialize user_type_counts: {e}")
        # Set all to 0 on error
        for key in user_type_counts:
            user_type_counts[key] = 0

def get_total_users_count():
    """Get total users count from global variable (fast)"""
    global total_users_count
    if total_users_count is None:
        # Initialize if not set
        initialize_total_users_count()
    return total_users_count or 0

def get_user_type_count(user_type):
    """Get user count for specific user_type from global variable (fast)"""
    global user_type_counts
    if user_type_counts.get(user_type) is None:
        # Initialize if not set
        initialize_user_type_counts()
    return user_type_counts.get(user_type, 0)

def update_total_users_count(increment=0):
    """Update global total users count (called on POST/DELETE)"""
    global total_users_count, user_type_counts
    if increment > 0:
        total_users_count = (total_users_count or 0) + increment
    else:
        # Recalculate from database
        try:
            from users.models import User
            total_users_count = User.objects.filter(role='1').count()
            initialize_user_type_counts()  # Recalculate user_type counts too
        except Exception:
            pass  # Keep existing count if query fails
    logger.info(f"Updated total_users_count: {total_users_count}")

def update_user_type_count(user_type, increment=0):
    """Update global user_type count (called on POST/DELETE)"""
    global user_type_counts
    if increment > 0:
        user_type_counts[user_type] = (user_type_counts.get(user_type, 0) + increment)
    else:
        # Recalculate from database
        try:
            from users.models import User
            users = User.objects.filter(role='1')
            if user_type == 'Old Users':
                user_type_counts[user_type] = users.filter(user_type=None).count()
            else:
                user_type_counts[user_type] = users.filter(user_type=user_type).count()
        except Exception:
            pass  # Keep existing count if query fails
    logger.info(f"Updated user_type_count for {user_type}: {user_type_counts.get(user_type, 0)}")

# Legacy function for backward compatibility
def get_cached_total_users_count():
    """Legacy function - now uses global variable for performance"""
    return get_total_users_count()
