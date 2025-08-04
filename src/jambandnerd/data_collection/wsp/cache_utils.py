"""
Cache utilities for WSP data ingestion optimization.

Manages timestamps and metadata to minimize unnecessary scraping operations.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

from .utils import get_logger

logger = get_logger(__name__)

# Cache file locations
CACHE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "data", "cache", "wsp"
)
SHOWS_CACHE_FILE = os.path.join(CACHE_DIR, "shows_last_scraped.json")
SONGS_CACHE_FILE = os.path.join(CACHE_DIR, "songs_last_scraped.json")


def ensure_cache_dir():
    """Ensure the cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def get_last_scrape_timestamp(cache_file: str) -> Optional[datetime]:
    """
    Get the last scrape timestamp from a cache file.

    Args:
        cache_file: Path to the cache file

    Returns:
        datetime of last scrape, or None if no cache exists
    """
    try:
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                data = json.load(f)
                timestamp_str = data.get("last_scraped")
                if timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
    except Exception as e:
        logger.warning("Error reading cache file %s: %s", cache_file, e)

    return None


def update_scrape_timestamp(cache_file: str, metadata: Optional[dict] = None):
    """
    Update the last scrape timestamp in a cache file.

    Args:
        cache_file: Path to the cache file
        metadata: Optional additional metadata to store
    """
    ensure_cache_dir()

    data = {"last_scraped": datetime.now().isoformat(), "metadata": metadata or {}}

    try:
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Updated cache timestamp: %s", cache_file)
    except Exception as e:
        logger.error("Error updating cache file %s: %s", cache_file, e)


def should_scrape_shows(force_scrape: bool = False, max_age_days: int = 7) -> bool:
    """
    Determine if shows should be scraped based on cache age.

    Args:
        force_scrape: If True, always scrape regardless of cache
        max_age_days: Maximum age in days before re-scraping

    Returns:
        True if shows should be scraped
    """
    if force_scrape:
        logger.info("Force scrape enabled for shows")
        return True

    last_scraped = get_last_scrape_timestamp(SHOWS_CACHE_FILE)
    if last_scraped is None:
        logger.info("No shows cache found, scraping required")
        return True

    age = datetime.now() - last_scraped
    should_scrape = age.days >= max_age_days

    logger.info(
        "Shows last scraped %d days ago. Should scrape: %s", age.days, should_scrape
    )
    return should_scrape


def should_scrape_songs(force_scrape: bool = False, max_age_days: int = 7) -> bool:
    """
    Determine if songs should be scraped based on cache age.

    Args:
        force_scrape: If True, always scrape regardless of cache
        max_age_days: Maximum age in days before re-scraping

    Returns:
        True if songs should be scraped
    """
    if force_scrape:
        logger.info("Force scrape enabled for songs")
        return True

    last_scraped = get_last_scrape_timestamp(SONGS_CACHE_FILE)
    if last_scraped is None:
        logger.info("No songs cache found, scraping required")
        return True

    age = datetime.now() - last_scraped
    should_scrape = age.days >= max_age_days

    logger.info(
        "Songs last scraped %d days ago. Should scrape: %s", age.days, should_scrape
    )
    return should_scrape


def update_shows_cache(show_count: int):
    """Update the shows cache with scrape metadata."""
    metadata = {"show_count": show_count, "scrape_type": "full"}
    update_scrape_timestamp(SHOWS_CACHE_FILE, metadata)


def update_songs_cache(song_count: int):
    """Update the songs cache with scrape metadata."""
    metadata = {"song_count": song_count, "scrape_type": "full"}
    update_scrape_timestamp(SONGS_CACHE_FILE, metadata)


def get_date_filter_cutoff(months_back: int = 3) -> datetime:
    """
    Get the cutoff date for filtering recent shows.

    Args:
        months_back: Number of months to look back

    Returns:
        datetime cutoff for filtering
    """
    cutoff = datetime.now() - timedelta(days=months_back * 30)  # Approximate months
    logger.info(
        "Using date filter cutoff: %s (%d months back)",
        cutoff.strftime("%Y-%m-%d"),
        months_back,
    )
    return cutoff


def get_supabase_date_filter(years_back: int = 3) -> str:
    """
    Get the date filter for Supabase queries.

    Args:
        years_back: Number of years to look back

    Returns:
        ISO date string for Supabase filtering
    """
    cutoff = datetime.now() - timedelta(days=years_back * 365)
    date_str = cutoff.strftime("%Y-%m-%d")
    logger.info("Using Supabase date filter: %s (%d years back)", date_str, years_back)
    return date_str
