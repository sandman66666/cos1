"""
Strategic Intelligence Cache

Caches Strategic Intelligence results to prevent expensive regeneration
on every tab switch or API call.
"""

import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class StrategicIntelligenceCache:
    """Thread-safe cache for Strategic Intelligence results"""
    
    def __init__(self, default_ttl_minutes: int = 30):
        """
        Initialize cache with default TTL (time-to-live)
        
        Args:
            default_ttl_minutes: Default cache expiration in minutes
        """
        self.cache = {}
        self.default_ttl = default_ttl_minutes * 60  # Convert to seconds
        self.lock = threading.RLock()
        
    def get(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Get cached Strategic Intelligence for user
        
        Args:
            user_email: User's email address
            
        Returns:
            Cached intelligence result or None if expired/missing
        """
        with self.lock:
            if user_email not in self.cache:
                return None
            
            cache_entry = self.cache[user_email]
            
            # Check if cache is expired
            if time.time() > cache_entry['expires_at']:
                logger.info(f"Strategic Intelligence cache expired for {user_email}")
                del self.cache[user_email]
                return None
            
            logger.info(f"Strategic Intelligence cache HIT for {user_email}")
            return cache_entry['data']
    
    def set(self, user_email: str, intelligence_data: Dict[str, Any], ttl_minutes: Optional[int] = None) -> None:
        """
        Cache Strategic Intelligence result for user
        
        Args:
            user_email: User's email address
            intelligence_data: Strategic Intelligence result to cache
            ttl_minutes: Custom TTL in minutes (uses default if None)
        """
        ttl_seconds = (ttl_minutes * 60) if ttl_minutes else self.default_ttl
        expires_at = time.time() + ttl_seconds
        
        with self.lock:
            self.cache[user_email] = {
                'data': intelligence_data,
                'cached_at': time.time(),
                'expires_at': expires_at,
                'cached_datetime': datetime.now().isoformat()
            }
            
        logger.info(f"Strategic Intelligence cached for {user_email} (TTL: {ttl_seconds//60} minutes)")
    
    def invalidate(self, user_email: str) -> bool:
        """
        Invalidate cache for specific user
        
        Args:
            user_email: User's email address
            
        Returns:
            True if cache was invalidated, False if no cache existed
        """
        with self.lock:
            if user_email in self.cache:
                del self.cache[user_email]
                logger.info(f"Strategic Intelligence cache invalidated for {user_email}")
                return True
            return False
    
    def clear_all(self) -> int:
        """
        Clear all cached Strategic Intelligence
        
        Returns:
            Number of cache entries cleared
        """
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Strategic Intelligence cache cleared ({count} entries)")
            return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        with self.lock:
            current_time = time.time()
            active_entries = 0
            expired_entries = 0
            
            for user_email, cache_entry in self.cache.items():
                if current_time <= cache_entry['expires_at']:
                    active_entries += 1
                else:
                    expired_entries += 1
            
            return {
                'total_entries': len(self.cache),
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'default_ttl_minutes': self.default_ttl // 60,
                'cache_users': list(self.cache.keys())
            }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries
        
        Returns:
            Number of expired entries removed
        """
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for user_email, cache_entry in self.cache.items():
                if current_time > cache_entry['expires_at']:
                    expired_keys.append(user_email)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)

# Global cache instance
strategic_intelligence_cache = StrategicIntelligenceCache(default_ttl_minutes=30) 