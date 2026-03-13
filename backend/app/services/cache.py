import json
import logging
from typing import Any, Optional, List, Dict
from app.core.config_enhanced import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.enabled = getattr(settings, "REDIS_CACHE_ENABLED", False)
        self.redis = None
        if self.enabled and getattr(settings, "REDIS_URL", None):
            try:
                import redis
                self.redis = redis.from_url(settings.REDIS_URL)
                self.redis.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.enabled = False

    def _make_key(self, *args) -> str:
        return ":".join(str(arg) for arg in args)

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled or not self.redis:
            return None
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        if not self.enabled or not self.redis:
            return False
        try:
            self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        if not self.enabled or not self.redis:
            return 0
        try:
            keys = list(self.redis.scan_iter(match=pattern))
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def get_marine_states(self) -> Optional[List[str]]:
        """Get cached marine states."""
        key = self._make_key("marine", "states")
        return self.get(key)

    def set_marine_states(self, states: List[str]) -> bool:
        """Cache marine states."""
        key = self._make_key("marine", "states")
        return self.set(key, states, getattr(settings, "CACHE_TTL_MARKETS", 86400))

    def get_marine_summary(self) -> Optional[List[Dict]]:
        """Get cached marine summary."""
        key = self._make_key("marine", "summary")
        return self.get(key)

    def set_marine_summary(self, summary: List[Dict]) -> bool:
        """Cache marine summary."""
        key = self._make_key("marine", "summary")
        return self.set(key, summary, getattr(settings, "CACHE_TTL_PRICES", 3600))

    def invalidate_marine_cache(self) -> int:
        """Invalidate all marine-related cache."""
        return self.clear_pattern("marine:*")

_cache_service = None

def get_cache() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
