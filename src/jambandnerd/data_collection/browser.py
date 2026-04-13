"""Shared Playwright-based browser automation for bypassing Cloudflare challenges.

Provides a singleton browser instance that collectors can use when standard
HTTP requests are blocked by bot protection (403 with Cloudflare challenge).

Usage from a collector:
    from jambandnerd.data_collection.browser import CloudflareBypass

    # On 403, fall back to Playwright
    response = CloudflareBypass.make_request(url)
    data = response.json()
    ...
    CloudflareBypass.cleanup()
"""

from __future__ import annotations

import logging
import random
import time
from typing import Dict, Optional

import requests
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

logger = logging.getLogger(__name__)

_rate_limit_delay = 4.0
_last_request_time: float = 0.0

_pw: Optional[Playwright] = None
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None


def _get_browser() -> Browser:
    global _pw, _browser, _context

    if _browser is None:
        logger.info("Launching Playwright (Firefox) for Cloudflare bypass")
        _pw = sync_playwright().start()
        _browser = _pw.firefox.launch(headless=True, args=[])
        _context = _browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) "
                "Gecko/20100101 Firefox/138.0"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Priority": "u=1",
            },
        )
        _context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

    return _browser


def _enforce_rate_limit() -> None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    delay = _rate_limit_delay + random.uniform(0, 2.0)
    if elapsed < delay:
        sleep_time = delay - elapsed
        logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
        time.sleep(sleep_time)
    _last_request_time = time.time()


class CloudflareBypass:
    """Make requests through a headless browser to bypass Cloudflare challenges."""

    @staticmethod
    def make_request(
        url: str,
        *,
        extra_headers: Optional[Dict[str, str]] = None,
        timeout_ms: int = 60000,
    ) -> requests.Response:
        """Navigate to *url* with Playwright and return a ``requests.Response``.

        The browser waits for the page ``load`` event and then an additional
        settling period to allow Cloudflare JS challenges to resolve.

        Args:
            url: Full URL to fetch.
            extra_headers: Optional headers merged into the context for this
                request only (not persisted).
            timeout_ms: Navigation timeout in milliseconds.

        Returns:
            A ``requests.Response`` object with ``status_code``, ``_content``,
            ``url``, ``headers``, and ``encoding`` populated from the browser.
        """
        _enforce_rate_limit()
        _get_browser()

        page: Page = _context.new_page()
        if extra_headers:
            page.set_extra_http_headers(extra_headers)

        try:
            logger.debug("Playwright fetching: %s", url)
            pw_response = page.goto(url, wait_until="load", timeout=timeout_ms)

            if pw_response is None:
                raise requests.exceptions.RequestException(
                    f"Playwright returned no response for {url}"
                )

            page.wait_for_timeout(1500)

            status_code = pw_response.status
            content = page.content()

            mock = requests.Response()
            mock.status_code = status_code
            mock.url = url
            mock._content = content.encode("utf-8")
            mock.headers = dict(pw_response.headers)
            mock.encoding = "utf-8"

            if status_code >= 400:
                logger.error("Playwright received %s for %s", status_code, url)

            return mock

        except Exception:
            logger.error("Playwright request failed for %s", url)
            raise
        finally:
            page.close()

    @staticmethod
    def cleanup() -> None:
        """Close the shared browser and context. Call at end of collection."""
        global _pw, _browser, _context

        if _context is not None:
            _context.close()
            _context = None

        if _browser is not None:
            _browser.close()
            _browser = None

        if _pw is not None:
            _pw.stop()
            _pw = None
            logger.info("Playwright browser cleaned up")
