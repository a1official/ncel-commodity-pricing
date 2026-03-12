"""
Redis Cache Service for Commodity Data
Provides caching layer for API responses and database queries.
"""

import json
import logging
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta
import redis
from ..core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for commodity data."""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = settings.REDIS_CACHE_ENABLED
        
        if self.enabled and settings.REDIS_URL:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.enabled = False
                self.redis_client = None
        else:
            logger.info("Redis cache disabled or not configured")
    
    def _make_key(self, prefix: str, *args) -> str:
        """Create a cache key from prefix and arguments."""
        key_parts = [prefix] + [str(arg) for arg in args if arg is not None]
        return ":".join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                return self.redis_client.setex(key, ttl, serialized)
            else:
                return self.redis_client.set(key, serialized)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.enabled or not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    # Marine-specific cache methods
    def get_marine_states(self) -> Optional[List[str]]:
        """Get cached marine states."""
        key = self._make_key("marine", "states")
        return self.get(key)
    
    def set_marine_states(self, states: List[str]) -> bool:
        """Cache marine states."""
        key = self._make_key("marine", "states")
        return self.set(key, states, settings.CACHE_TTL_MARKETS)
    
    def get_marine_summary(self) -> Optional[List[Dict]]:
        """Get cached marine summary."""
        key = self._make_key("marine", "summary")
        return self.get(key)
    
    def set_marine_summary(self, summary: List[Dict]) -> bool:
        """Cache marine summary."""
        key = self._make_key("marine", "summary")
        return self.set(key, summary, settings.CACHE_TTL_PRICES)
    
    def get_commodity_prices(self, commodity_id: int, state: str = None) -> Optional[List[Dict]]:
        """Get cached commodity prices."""
        key = self._make_key("prices", commodity_id, state or "all")
        return self.get(key)
    
    def set_commodity_prices(self, commodity_id: int, prices: List[Dict], state: str = None) -> bool:
        """Cache commodity prices."""
        key = self._make_key("prices", commodity_id, state or "all")
        return self.set(key, prices, settings.CACHE_TTL_PRICES)
    
    def invalidate_marine_cache(self) -> int:
        """Invalidate all marine-related cache."""
        return self.clear_pattern("marine:*")
    
    def invalidate_commodity_cache(self, commodity_id: int = None) -> int:
        """Invalidate commodity price cache."""
        if commodity_id:
            return self.clear_pattern(f"prices:{commodity_id}:*")
        else:
            return self.clear_pattern("prices:*")


# Global cache instance
cache = CacheService()


def get_cache() -> CacheService:
    """Get the global cache instance."""
    return cache