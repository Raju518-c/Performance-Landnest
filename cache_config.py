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
import re

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

# Global variables for total property requests count by looking_for type (initialized on server start)
total_property_requests_count = None
looking_for_counts = {
    'purchase': 0,
    'rent': 0,
    'lease': 0,
    'jv/jd': 0,
    'build to suit': 0,
    'all': 0  # For all requests
}

# Global variables for total bank auction properties count (initialized on server start)
total_bank_auction_properties_count = None

# Global variables for total properties count (initialized on server start)
total_properties_count = None

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

# Helper functions for property request caching
def initialize_total_property_requests_count():
    """Initialize global total property requests count on server start"""
    global total_property_requests_count, looking_for_counts
    try:
        from property.models import PropertyRequest
        total_property_requests_count = PropertyRequest.objects.count()
        logger.info(f"Initialized total_property_requests_count: {total_property_requests_count}")
        
        # Initialize looking_for counts
        initialize_looking_for_counts()
    except Exception as e:
        logger.error(f"Failed to initialize total_property_requests_count: {e}")
        total_property_requests_count = 0

def initialize_looking_for_counts():
    """Initialize global looking_for counts on server start"""
    global looking_for_counts
    try:
        from property.models import PropertyRequest
        requests = PropertyRequest.objects.all()
        
        # Count by looking_for type
        for looking_for in looking_for_counts:
            if looking_for == 'all':
                looking_for_counts[looking_for] = requests.count()
            else:
                looking_for_counts[looking_for] = requests.filter(looking_for=looking_for).count()
        
        logger.info(f"Initialized looking_for_counts: {looking_for_counts}")
    except Exception as e:
        logger.error(f"Failed to initialize looking_for_counts: {e}")
        # Set all to 0 on error
        for key in looking_for_counts:
            looking_for_counts[key] = 0

def get_total_property_requests_count():
    """Get total property requests count from global variable (fast)"""
    global total_property_requests_count
    if total_property_requests_count is None:
        # Initialize if not set
        initialize_total_property_requests_count()
    return total_property_requests_count or 0

def get_looking_for_count(looking_for):
    """Get property request count for specific looking_for type from global variable (fast)"""
    global looking_for_counts
    if looking_for_counts.get(looking_for) is None:
        # Initialize if not set
        initialize_looking_for_counts()
    return looking_for_counts.get(looking_for, 0)

def update_total_property_requests_count(increment=0):
    """Update global total property requests count (called on POST/DELETE)"""
    global total_property_requests_count, looking_for_counts
    if increment > 0:
        total_property_requests_count = (total_property_requests_count or 0) + increment
    else:
        # Recalculate from database
        try:
            from property.models import PropertyRequest
            total_property_requests_count = PropertyRequest.objects.count()
            initialize_looking_for_counts()  # Recalculate looking_for counts too
        except Exception:
            pass  # Keep existing count if query fails
    logger.info(f"Updated total_property_requests_count: {total_property_requests_count}")


# Helper functions for bank auction property caching
def initialize_total_bank_auction_properties_count():
    """Initialize global total bank auction properties count on server start"""
    global total_bank_auction_properties_count
    try:
        from property.models import BankAuctionProperty
        total_bank_auction_properties_count = BankAuctionProperty.objects.count()
        logger.info(f"Initialized total_bank_auction_properties_count: {total_bank_auction_properties_count}")
    except Exception as e:
        logger.error(f"Failed to initialize total_bank_auction_properties_count: {e}")
        total_bank_auction_properties_count = 0

def get_total_bank_auction_properties_count():
    """Get total bank auction properties count from global variable (fast)"""
    global total_bank_auction_properties_count
    if total_bank_auction_properties_count is None:
        initialize_total_bank_auction_properties_count()
    return total_bank_auction_properties_count or 0

def update_total_bank_auction_properties_count(increment=0):
    """Update global total bank auction properties count (called on POST/DELETE)"""
    global total_bank_auction_properties_count
    if increment != 0:
        total_bank_auction_properties_count = (total_bank_auction_properties_count or 0) + increment
    else:
        try:
            from property.models import BankAuctionProperty
            total_bank_auction_properties_count = BankAuctionProperty.objects.count()
        except Exception:
            pass
    logger.info(f"Updated total_bank_auction_properties_count: {total_bank_auction_properties_count}")


# Helper functions for property caching
def initialize_total_properties_count():
    """Initialize global total properties count on server start (using fast estimation)"""
    global total_properties_count, property_type_counts, type_counts
    try:
        from property.models import Property
        from django.db import connection
        
        # Try to get fast estimate from Postgres/MySQL metadata first
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute("SELECT reltuples FROM pg_class WHERE relname = 'property_property'")
                row = cursor.fetchone()
                if row:
                    total_properties_count = int(row[0])
        elif connection.vendor == 'mysql':
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLE STATUS LIKE 'property_property'")
                row = cursor.fetchone()
                if row:
                    # Index 4 is 'Rows' in MySQL SHOW TABLE STATUS
                    total_properties_count = row[4]
        
        # Fallback to standard count only if estimate failed and table isn't too huge
        if total_properties_count is None or total_properties_count < 0:
            total_properties_count = Property.objects.count()
            
        logger.info(f"Initialized total_properties_count: {total_properties_count}")
        
        # Also initialize category/type counts if needed
        # These are usually smaller and can be counted directly or estimated
    except Exception as e:
        logger.error(f"Failed to initialize total_properties_count: {e}")
        total_properties_count = 800000 # Safety estimate

def get_total_properties_count_fast():
    """Get total properties count from global variable (fast)"""
    global total_properties_count
    if total_properties_count is None:
        initialize_total_properties_count()
    return total_properties_count or 0

def get_property_type_count_fast(property_type):
    """Get count for specific property_type with caching"""
    cache_key = f"total_count_property_type_{re.sub(r'[^A-Za-z0-9]+', '_', property_type.lower())}"
    cached_count = cache_manager.get(cache_key)
    if cached_count is not None:
        return int(cached_count)
    
    try:
        from property.models import Property
        count = Property.objects.filter(property_type__iexact=property_type).count()
        cache_manager.set(cache_key, count, 3600) # Cache for 1 hour
        return count
    except Exception:
        return 0

def get_type_count_fast(type_val):
    """Get count for specific type (rent/sell/lease) with caching"""
    cache_key = f"total_count_type_{type_val.lower()}"
    cached_count = cache_manager.get(cache_key)
    if cached_count is not None:
        return int(cached_count)
    
    try:
        from property.models import Property
        count = Property.objects.filter(type__iexact=type_val).count()
        cache_manager.set(cache_key, count, 3600) # Cache for 1 hour
        return count
    except Exception:
        return 0

def get_property_filter_count_fast(property_type, type_val):
    """Get count for combined filters with caching"""
    cache_key = f"total_count_combined_{re.sub(r'[^A-Za-z0-9]+', '_', property_type.lower())}_{type_val.lower()}"
    cached_count = cache_manager.get(cache_key)
    if cached_count is not None:
        return int(cached_count)
    
    try:
        from property.models import Property
        count = Property.objects.filter(property_type__iexact=property_type, type__iexact=type_val).count()
        cache_manager.set(cache_key, count, 3600) # Cache for 1 hour
        return count
    except Exception:
        return 0

def update_total_properties_count(increment=0):
    """Update global total properties count (called on POST/DELETE)"""
    global total_properties_count
    if increment != 0:
        total_properties_count = (total_properties_count or 0) + increment
    else:
        try:
            from property.models import Property
            total_properties_count = Property.objects.count()
        except Exception:
            pass
    logger.info(f"Updated total_properties_count: {total_properties_count}")

def update_looking_for_count(looking_for, increment=0):
    """Update global looking_for count (called on POST/DELETE)"""
    global looking_for_counts
    if increment > 0:
        looking_for_counts[looking_for] = (looking_for_counts.get(looking_for, 0) + increment)
        looking_for_counts['all'] = (looking_for_counts.get('all', 0) + increment)
    else:
        # Recalculate from database
        try:
            from property.models import PropertyRequest
            requests = PropertyRequest.objects.all()
            looking_for_counts[looking_for] = requests.filter(looking_for=looking_for).count()
            looking_for_counts['all'] = requests.count()
        except Exception:
            pass  # Keep existing count if query fails
    logger.info(f"Updated looking_for_count for {looking_for}: {looking_for_counts.get(looking_for, 0)}")



def update_total_property_requests_count(increment=0):
    """Update global total property requests count (called on POST/DELETE)"""
    global total_property_requests_count, looking_for_counts
    if increment > 0:
        total_property_requests_count = (total_property_requests_count or 0) + increment
    else:
        # Recalculate from database

        try:
            from property.models import PropertyRequest

            total_property_requests_count = PropertyRequest.objects.count()

            # Optional: refresh looking_for counts also
            looking_for_counts['all'] = total_property_requests_count

        except Exception:
            pass

    logger.info(f"Updated total_property_requests_count: {total_property_requests_count}")