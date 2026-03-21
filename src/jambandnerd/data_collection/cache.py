"""Disk-based HTTP response caching for data collectors."""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class HttpCache:
    """Disk-based HTTP response cache with TTL support.

    Caches HTTP responses on disk to reduce redundant API calls.
    Useful for repeated collection runs that may fetch the same data.
    """

    def __init__(
        self, cache_dir: Optional[str] = None, default_ttl_seconds: int = 3600
    ):
        """Initialize the HTTP cache.

        Args:
            cache_dir: Directory for cache files. If None, uses system temp directory.
            default_ttl_seconds: Default time-to-live for cached responses (1 hour).
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "jambandnerd_http_cache"

        self.default_ttl = default_ttl_seconds
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create cache directory {self.cache_dir}: {e}")
            self.cache_dir = Path(tempfile.gettempdir()) / "jambandnerd_http_cache"
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.error("Could not create cache directory, caching disabled")

    def _generate_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key from URL and parameters.

        Args:
            url: The request URL
            params: Optional query parameters

        Returns:
            A hex-encoded SHA-256 hash suitable for filenames
        """
        key_parts = [url]
        if params:
            sorted_params = json.dumps(params, sort_keys=True)
            key_parts.append(sorted_params)
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            key: The cache key (hash)

        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{key}.json"

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Retrieve a cached response if it exists and is not expired.

        Args:
            url: The request URL
            params: Optional query parameters

        Returns:
            Cached response data or None if not found/expired
        """
        key = self._generate_key(url, params)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            expires_at = datetime.fromisoformat(cached["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                cache_path.unlink(missing_ok=True)
                logger.debug(f"Cache expired for {url}")
                return None

            logger.debug(f"Cache hit for {url}")
            return cached["data"]

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to read cache for {url}: {e}")
            cache_path.unlink(missing_ok=True)
            return None

    def set(
        self,
        url: str,
        data: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Store a response in the cache.

        Args:
            url: The request URL
            data: The response data to cache
            params: Optional query parameters
            ttl_seconds: Time-to-live in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise
        """
        key = self._generate_key(url, params)
        cache_path = self._get_cache_path(key)

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        cached_entry = {
            "url": url,
            "params": params,
            "data": data,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        try:
            with open(cache_path, "w") as f:
                json.dump(cached_entry, f)
            logger.debug(f"Cached response for {url} (TTL: {ttl}s)")
            return True
        except OSError as e:
            logger.warning(f"Failed to write cache for {url}: {e}")
            return False

    def clear(self, band: Optional[str] = None) -> int:
        """Clear cached responses.

        Args:
            band: If provided, only clear cache for that band URL. If None, clear all.

        Returns:
            Number of cache entries cleared
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if band:
                    with open(cache_file, "r") as f:
                        cached = json.load(f)
                    if band.lower() not in cached.get("url", "").lower():
                        continue
                cache_file.unlink()
                count += 1
            except (json.JSONDecodeError, OSError):
                continue

        if count > 0:
            logger.info(f"Cleared {count} cache entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.cache_dir.exists():
            return {"total_entries": 0, "size_bytes": 0}

        total_size = 0
        expired_count = 0
        valid_count = 0
        now = datetime.now(timezone.utc)

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                total_size += cache_file.stat().st_size
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                expires_at = datetime.fromisoformat(cached["expires_at"])
                if now > expires_at:
                    expired_count += 1
                else:
                    valid_count += 1
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                expired_count += 1

        return {
            "total_entries": valid_count + expired_count,
            "valid_entries": valid_count,
            "expired_entries": expired_count,
            "size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
        }
