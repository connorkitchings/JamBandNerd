"""This module contains functions for creating and managing HTTP sessions."""

import logging
import os
import random
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jambandnerd.data_collection.browser import CloudflareBypass
from jambandnerd.data_collection.config import JAMBANNERD_BOT_UA

logger = logging.getLogger(__name__)

IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

EC_ENCODING = "windows-1252"


def decode_ec_response(response: requests.Response) -> str:
    """Decode response from EverydayCompanion with correct encoding."""
    if response.encoding == "utf-8":
        return response.text

    response.encoding = EC_ENCODING
    return response.text


def make_simple_request(
    session: requests.Session, url: str, **kwargs
) -> requests.Response:
    """Make a simple GET request without rate limiting."""
    if IS_GITHUB_ACTIONS:
        return CloudflareBypass.make_request(url)

    try:
        logger.debug(f"Fetching (no rate limit): {url}")
        response = session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
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
        raise


def create_enhanced_session() -> requests.Session:
    """Create a requests session with browser-like headers and retry logic."""
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": JAMBANNERD_BOT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
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
            "Sec-CH-UA-Mobile": '"?0"',
            "Sec-CH-UA-Platform": '"Windows"',
            "Referer": "https://www.everydaycompanion.com/",
        }
    )

    retry_strategy = Retry(
        total=3,
        backoff_factor=3,
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

rate_limit_delay = 6.0 if IS_GITHUB_ACTIONS else 2.0


def enforce_rate_limit():
    """Enforce rate limiting between requests with random variation."""
    global last_request_time
    elapsed = time.time() - last_request_time
    jitter_range = 2.0 if IS_GITHUB_ACTIONS else 0.5
    delay_with_jitter = rate_limit_delay + random.uniform(0, jitter_range)
    if elapsed < delay_with_jitter:
        sleep_time = delay_with_jitter - elapsed
        logger.debug(
            f"Rate limiting: sleeping for {sleep_time:.2f}s (CI={IS_GITHUB_ACTIONS})"
        )
        time.sleep(sleep_time)
    last_request_time = time.time()


def make_request(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """Make a GET request with rate limiting and error handling.

    In GitHub Actions, automatically uses Playwright headless browser to bypass bot detection.
    In local environments, uses standard requests library.
    """
    if IS_GITHUB_ACTIONS:
        enforce_rate_limit()
        return CloudflareBypass.make_request(url)
    else:
        enforce_rate_limit()

        try:
            logger.debug(f"Fetching: {url}")
            response = session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
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
            raise


def cleanup_playwright():
    """Clean up Playwright browser instance. Call this at the end of collection."""
    CloudflareBypass.cleanup()
