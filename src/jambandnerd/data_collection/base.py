"""Abstract base classes for data collection."""

from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import HttpCache

logger = logging.getLogger(__name__)


@dataclass
class CollectorConfig:
    """Configuration for data collectors."""

    base_url: str
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 2.0
    rate_limit_calls: int = 100
    rate_limit_window: int = 60  # seconds
    user_agent: str = "JamBandNerd/1.0"
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour default
    cache_dir: Optional[str] = None


@dataclass
class RateLimiter:
    """Simple rate limiter for API calls."""

    max_calls: int
    window_seconds: int
    calls: int = 0
    window_start: float = 0

    def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded."""
        now = time.time()

        # Reset window if expired
        if now - self.window_start > self.window_seconds:
            self.calls = 0
            self.window_start = now

        # Wait if limit exceeded
        if self.calls >= self.max_calls:
            sleep_time = self.window_seconds - (now - self.window_start)
            if sleep_time > 0:
                logger.info(
                    f"Rate limit reached ({self.calls}/{self.max_calls}), sleeping for {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
                self.calls = 0
                self.window_start = time.time()

    def record_call(self) -> None:
        """Record an API call."""
        self.calls += 1


@dataclass
class CollectionMetrics:
    """Metrics tracking for data collection runs."""

    band: str
    shows_collected: int = 0
    setlists_collected: int = 0
    songs_collected: int = 0
    venues_collected: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    http_errors: Dict[int, int] = field(default_factory=dict)
    consecutive_failures: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get the duration of the collection run."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    def record_error(self, error: str) -> None:
        """Record an error message."""
        self.errors.append(error)
        self.consecutive_failures += 1

    def record_warning(self, warning: str) -> None:
        """Record a warning message."""
        self.warnings.append(warning)

    def record_http_error(self, status_code: int) -> None:
        """Record an HTTP error by status code."""
        self.http_errors[status_code] = self.http_errors.get(status_code, 0) + 1

    def record_success(self) -> None:
        """Record a successful operation."""
        self.consecutive_failures = 0

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses += 1

    @property
    def is_healthy(self) -> bool:
        """Check if the collection run is considered healthy."""
        return self.consecutive_failures < 5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "band": self.band,
            "shows_collected": self.shows_collected,
            "setlists_collected": self.setlists_collected,
            "songs_collected": self.songs_collected,
            "venues_collected": self.venues_collected,
            "errors": self.errors[-10:],  # Last 10 errors
            "warnings": self.warnings[-10:],  # Last 10 warnings
            "http_errors": self.http_errors,
            "consecutive_failures": self.consecutive_failures,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "duration_seconds": self.duration_seconds,
        }


class BandCollector(ABC):
    """Abstract base class for band-specific data collectors with enhanced error handling."""

    def __init__(self, config: CollectorConfig):
        self.config = config
        self.rate_limiter = RateLimiter(
            max_calls=config.rate_limit_calls, window_seconds=config.rate_limit_window
        )

        self.cache: Optional[HttpCache] = None
        if config.cache_enabled:
            self.cache = HttpCache(
                cache_dir=config.cache_dir,
                default_ttl_seconds=config.cache_ttl_seconds,
            )

        self._consecutive_failures = 0
        self._circuit_open = False

        # Create session with connection pooling and retry strategy
        self.session = requests.Session()

        # Configure retry strategy for connection-related errors
        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["GET"],  # Only retry GET requests
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                # Accept both JSON and HTML since some collectors scrape pages
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            }
        )

    @property
    def is_healthy(self) -> bool:
        """Check if the collector circuit breaker is closed."""
        return not self._circuit_open

    def reset_circuit(self) -> None:
        """Reset the circuit breaker after successful requests."""
        self._consecutive_failures = 0
        self._circuit_open = False
        logger.info(f"Circuit breaker reset for {self.__class__.__name__}")

    def trip_circuit(self) -> None:
        """Trip the circuit breaker after consecutive failures."""
        self._circuit_open = True
        logger.warning(
            f"Circuit breaker OPEN for {self.__class__.__name__} "
            f"({self._consecutive_failures} consecutive failures)"
        )

    def record_success(self) -> None:
        """Record a successful request."""
        if self._consecutive_failures > 0:
            self._consecutive_failures = 0
            logger.debug(f"Recovery after failure for {self.__class__.__name__}")

    def record_failure(self) -> bool:
        """Record a failed request and check circuit breaker.

        Returns:
            True if circuit breaker should be tripped
        """
        self._consecutive_failures += 1
        failure_threshold = 5
        if self._consecutive_failures >= failure_threshold:
            self.trip_circuit()
            return True
        return False

    def _fetch_from_endpoint(
        self,
        endpoint: str,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Fetch data from an API endpoint with retry logic, rate limiting, and caching.

        Args:
            endpoint: API endpoint path
            use_cache: Whether to use caching (default True)
            cache_ttl: Custom TTL for this specific request (uses config default if None)
            **kwargs: Additional arguments passed to requests.get()

        Returns:
            List of dictionaries from the API response
        """
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        # Check circuit breaker
        if self._circuit_open:
            logger.warning(
                f"Circuit breaker is OPEN for {self.__class__.__name__}, "
                "skipping request to {url}"
            )
            return []

        # Check cache first
        params = kwargs.get("params")
        if use_cache and self.cache:
            cached_data = self.cache.get(url, params)
            if cached_data is not None:
                self.record_success()
                return cached_data

        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Set default timeout if not provided
        kwargs.setdefault("timeout", self.config.timeout)

        # Redact API key from URL for logging
        log_url = re.sub(r"apikey=[^&]*", "apikey=REDACTED", url)
        logger.info(f"Fetching data from {log_url}")

        try:
            self.rate_limiter.record_call()
            response = self.session.get(url, **kwargs)
            response.raise_for_status()

            # Handle different response formats
            try:
                data = response.json()

                # Handle API error responses
                if isinstance(data, dict) and data.get("error"):
                    error_msg = data.get(
                        "error_message", data.get("message", "Unknown API error")
                    )
                    raise requests.exceptions.RequestException(
                        f"API Error: {error_msg}"
                    )

                # Extract data array if wrapped
                if isinstance(data, dict) and "data" in data:
                    result = data["data"] or []
                elif isinstance(data, list):
                    result = data
                else:
                    logger.warning(
                        f"Unexpected response format from {url}, returning empty list"
                    )
                    result = []

                # Cache successful response
                if use_cache and self.cache and result:
                    self.cache.set(url, result, params, cache_ttl)

                self.record_success()
                return result

            except ValueError as e:
                logger.error(f"Failed to parse JSON response from {url}: {e}")
                self.record_failure()
                return []

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout ({self.config.timeout}s) for {url}")
            self.record_failure()
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {url}")
            self.record_failure()
            raise
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            logger.error(f"HTTP error {status} for {url}: {e}")
            self.record_failure()
            if e.response is not None and e.response.status_code == 403:
                logger.warning(
                    f"Access denied (403) for {url} — upstream API may be blocking requests"
                )
                self._check_circuit_breaker()
                return []
            if status in (502, 503, 504):
                retries = getattr(self, "_outer_fetch_retries", 0)
                if retries < 2:
                    self._outer_fetch_retries = retries + 1
                    delay = 60 * self._outer_fetch_retries
                    logger.warning(
                        "Upstream %s for %s — retrying in %ds (attempt %d/2)",
                        status,
                        url,
                        delay,
                        self._outer_fetch_retries,
                    )
                    time.sleep(delay)
                    return self._fetch_from_endpoint(
                        endpoint, use_cache=False, cache_ttl=cache_ttl, **kwargs
                    )
                self._outer_fetch_retries = 0
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            self.record_failure()
            raise

    @abstractmethod
    def collect_shows(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Collect show data for a given date range."""
        pass

    def _is_target_artist(
        self,
        item: Dict[str, Any],
        *,
        artist_id: Optional[int] = None,
        artist_name: Optional[str] = None,
    ) -> bool:
        """Return whether an API row belongs to the target artist.

        Checks ``artist_id`` first when provided, then falls back to
        case-insensitive ``artist_name`` match.
        """
        if artist_id is not None:
            item_id = item.get("artist_id")
            if item_id is not None:
                try:
                    return int(item_id) == artist_id
                except (TypeError, ValueError):
                    return False

        if artist_name is not None:
            item_artist = str(item.get("artist", "")).strip().lower()
            return item_artist == artist_name.strip().lower()

        return True  # no filter configured — accept all

    @abstractmethod
    def collect_setlists(
        self, shows_to_process: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Collect setlist data for the given shows (each dict must contain at least show_id)."""
        pass

    @abstractmethod
    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collect the entire song catalog for the band."""
        pass

    @abstractmethod
    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collect the entire venue catalog for the band."""
        pass
