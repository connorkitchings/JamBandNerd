"""This module contains functions for creating and managing HTTP sessions."""

import logging
import os
import random
import time
from typing import Optional

import requests
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Detect if running in GitHub Actions
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

# EverydayCompanion.com uses Windows-1252 encoding (common for older ASP sites)
EC_ENCODING = "windows-1252"


def decode_ec_response(response: requests.Response) -> str:
    """Decode response from EverydayCompanion with correct encoding.

    EverydayCompanion.com uses Windows-1252 encoding, but may return gzip-compressed content.
    The requests library auto-decompresses via response.text, but may misdetect encoding.
    We force it to use Windows-1252 for correct character handling.
    """
    # If the response is already UTF-8 (e.g., from Playwright mock), respect it
    if response.encoding == "utf-8":
        return response.text

    # Set encoding before accessing .text to force Windows-1252 decoding
    response.encoding = EC_ENCODING
    return response.text


def make_simple_request(
    session: requests.Session, url: str, **kwargs
) -> requests.Response:
    """Make a simple GET request without rate limiting.

    Use for index/tour pages that don't need aggressive rate limiting.
    Individual setlist pages should still use make_request().
    """
    if IS_GITHUB_ACTIONS:
        return make_playwright_request(url)

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

    # Comprehensive browser-like headers to avoid 403 Forbidden
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            # NOTE: Don't set Accept-Encoding manually - let requests handle it automatically
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

# Use more conservative rate limiting in GitHub Actions
rate_limit_delay = 6.0 if IS_GITHUB_ACTIONS else 2.0  # Base delay between requests

# Global Playwright browser instance for reuse across requests
_playwright_browser: Optional[Browser] = None
_playwright_context: Optional[BrowserContext] = None


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
        # Use Playwright in CI to bypass bot detection
        return make_playwright_request(url)
    else:
        # Use standard requests locally
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


def _get_playwright_browser() -> Browser:
    """Get or create a persistent Playwright browser instance."""
    global _playwright_browser, _playwright_context

    if _playwright_browser is None:
        logger.info(
            "Initializing Playwright browser (Firefox) for GitHub Actions environment"
        )
        playwright = sync_playwright().start()
        # Use Firefox instead of Chromium as it often bypasses Cloudflare/WAF checks better in headless mode
        _playwright_browser = playwright.firefox.launch(
            headless=True,
            # Firefox doesn't use the same args as Chrome, fewer needed
            args=[],
        )
        _playwright_context = _playwright_browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "DNT": "1",
                "Connection": "keep-alive",
                "Referer": "https://www.everydaycompanion.com/",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Priority": "u=1",
            },
        )
        # Mask automation indicators
        _playwright_context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

    return _playwright_browser


def make_playwright_request(url: str) -> requests.Response:
    """Make a request using Playwright headless browser.

    This bypasses bot detection by using a real browser instance.
    Returns a requests.Response-compatible object for backward compatibility.
    """
    enforce_rate_limit()

    _get_playwright_browser()
    page: Page = _playwright_context.new_page()

    try:
        logger.debug(f"Fetching with Playwright: {url}")

        # Navigate to the URL with extended timeout
        # Use 'load' instead of 'networkidle' - some pages never fully idle
        # Increase timeout to 60s to handle slow CI network
        response = page.goto(url, wait_until="load", timeout=60000)

        if response is None:
            raise requests.exceptions.RequestException(f"Failed to load {url}")

        # Wait a moment for any dynamic content to load
        page.wait_for_timeout(1000)

        # Check for HTTP errors
        status_code = response.status
        if status_code >= 400:
            # Wait a bit before getting content to ensure page is stable
            page.wait_for_timeout(500)

            # Create a mock response object for error handling
            mock_response = requests.Response()
            mock_response.status_code = status_code
            mock_response.url = url
            mock_response._content = page.content().encode("utf-8")

            if status_code == 403:
                logger.error(f"403 Forbidden for {url} even with Playwright browser")

            # Raise HTTPError for consistency with requests library
            error = requests.exceptions.HTTPError(
                f"{status_code} Error: {response.status_text} for url: {url}"
            )
            error.response = mock_response
            raise error

        # Get page content
        content = page.content()

        # Create a mock Response object compatible with requests library
        mock_response = requests.Response()
        mock_response.status_code = status_code
        mock_response._content = content.encode("utf-8")
        mock_response.url = url
        mock_response.headers = dict(response.headers)
        mock_response.encoding = "utf-8"

        logger.debug(
            f"Successfully fetched {url} with Playwright (status: {status_code})"
        )
        return mock_response

    except Exception as e:
        logger.error(f"Playwright request failed for {url}: {e}")
        raise
    finally:
        # Close the page to free resources
        page.close()


def cleanup_playwright():
    """Clean up Playwright browser instance. Call this at the end of collection."""
    global _playwright_browser, _playwright_context

    if _playwright_context is not None:
        _playwright_context.close()
        _playwright_context = None

    if _playwright_browser is not None:
        _playwright_browser.close()
        _playwright_browser = None
        logger.info("Playwright browser cleaned up")
