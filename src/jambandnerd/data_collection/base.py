"""Abstract base classes for data collection."""
from __future__ import annotations

import time
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from datetime import date, datetime

import requests
from requests.adapters import HTTPAdapter
from requests.models import Response
from urllib3.util.retry import Retry

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
                logger.info(f"Rate limit reached ({self.calls}/{self.max_calls}), sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self.calls = 0
                self.window_start = time.time()
                
    def record_call(self) -> None:
        """Record an API call."""
        self.calls += 1


class BandCollector(ABC):
    """Abstract base class for band-specific data collectors with enhanced error handling."""
    
    def __init__(self, config: CollectorConfig):
        self.config = config
        self.rate_limiter = RateLimiter(
            max_calls=config.rate_limit_calls,
            window_seconds=config.rate_limit_window
        )
        
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
        self.session.headers.update({
            'User-Agent': config.user_agent,
            # Accept both JSON and HTML since some collectors scrape pages
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
        })
    
    def _fetch_from_endpoint(self, endpoint: str, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data from an API endpoint with retry logic and rate limiting."""
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Set default timeout if not provided
        kwargs.setdefault('timeout', self.config.timeout)
        
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
                if isinstance(data, dict) and data.get('error'):
                    error_msg = data.get('error_message', data.get('message', 'Unknown API error'))
                    raise requests.exceptions.RequestException(f"API Error: {error_msg}")
                
                # Extract data array if wrapped
                if isinstance(data, dict) and 'data' in data:
                    return data['data'] or []
                elif isinstance(data, list):
                    return data
                else:
                    logger.warning(f"Unexpected response format from {url}, returning empty list")
                    return []
                    
            except ValueError as e:
                logger.error(f"Failed to parse JSON response from {url}: {e}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout ({self.config.timeout}s) for {url}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {url}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise

    @abstractmethod
    def collect_shows(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Collect show data for a given date range."""
        pass

    @abstractmethod
    def collect_setlists(self, show_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collect setlist data for a list of show IDs."""
        pass

    @abstractmethod
    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collect the entire song catalog for the band."""
        pass

    @abstractmethod
    def collect_venues(self) -> List[Dict[str, Any]]:
        """Collect the entire venue catalog for the band."""
        pass
