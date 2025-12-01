"""This module contains functions for creating and managing HTTP sessions."""

import logging
import random
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def create_enhanced_session() -> requests.Session:
    """Create a requests session with browser-like headers and retry logic."""
    session = requests.Session()

    # Comprehensive browser-like headers to avoid 403 Forbidden
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Pragma": "no-cache",
            "DNT": "1",
            "Sec-GPC": "1",
            "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Referer": "https://www.everydaycompanion.com/",
        }
    )

    # Configure retry strategy with exponential backoff
    # NOTE: 403 is NOT included - it's an access denial, not a transient error
    # Including 403 causes "too many 403 error responses" errors in urllib3
    retry_strategy = Retry(
        total=3,
        backoff_factor=3,  # Wait 1, 3, 9 seconds between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy, pool_connections=10, pool_maxsize=20
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


last_request_time = 0

# Detect if running in GitHub Actions and use more conservative rate limiting
# GitHub Actions IPs may be more aggressively rate-limited by websites
import os
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
rate_limit_delay = 6.0 if IS_GITHUB_ACTIONS else 2.0  # Base delay between requests


def enforce_rate_limit():
    """Enforce rate limiting between requests with random variation."""
    global last_request_time
    elapsed = time.time() - last_request_time
    # Add random variation to make requests less predictable
    # Use larger jitter in CI to appear more human-like
    jitter_range = 2.0 if IS_GITHUB_ACTIONS else 0.5
    delay_with_jitter = rate_limit_delay + random.uniform(0, jitter_range)
    if elapsed < delay_with_jitter:
        sleep_time = delay_with_jitter - elapsed
        logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s (CI={IS_GITHUB_ACTIONS})")
        time.sleep(sleep_time)
    last_request_time = time.time()


def make_request(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """Make a GET request with rate limiting and error handling."""
    enforce_rate_limit()

    try:
        logger.debug(f"Fetching: {url}")
        response = session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:  # Catch base RequestException
        if (
            isinstance(e, requests.exceptions.HTTPError)
            and e.response
            and e.response.status_code == 403
        ):
            logger.error(
                f"403 Forbidden for {url} - site may be blocking scrapers despite headers"
            )
        elif isinstance(e, requests.exceptions.ConnectionError):
            logger.error(f"Connection error for {url}: {e}")
        # Add other specific exception handling if needed
        raise  # Re-raise the original exception
