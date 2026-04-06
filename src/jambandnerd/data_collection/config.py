"""Configuration settings for data collectors."""

import os

from .base import CollectorConfig

CACHE_DIR = os.environ.get("JAMBN_CACHE_DIR", None)
DEFAULT_CACHE_TTL = int(os.environ.get("JAMBN_CACHE_TTL", "3600"))

JAMBANNERD_BOT_UA = "JamBandNerd-Bot/1.0 (+https://jambandnerd.com/data-use)"

# Default configurations for each band's data collection
COLLECTOR_CONFIGS = {
    "goose": CollectorConfig(
        base_url="https://elgoose.net/api",
        timeout=30,
        max_retries=3,
        backoff_factor=2.0,
        rate_limit_calls=50,  # Be conservative with elgoose.net
        rate_limit_window=60,
        user_agent=f"{JAMBANNERD_BOT_UA} (Goose Data Collection)",
        cache_enabled=True,
        cache_ttl_seconds=DEFAULT_CACHE_TTL,
        cache_dir=CACHE_DIR,
    ),
    "eggy": CollectorConfig(
        base_url="https://thecarton.net/api",
        timeout=30,
        max_retries=3,
        backoff_factor=2.0,
        rate_limit_calls=50,
        rate_limit_window=60,
        user_agent=f"{JAMBANNERD_BOT_UA} (Eggy Data Collection)",
        cache_enabled=True,
        cache_ttl_seconds=DEFAULT_CACHE_TTL,
        cache_dir=CACHE_DIR,
    ),
    "phish": CollectorConfig(
        base_url="https://api.phish.net/v5",
        timeout=120,  # Phish API can be slow with large datasets
        max_retries=5,
        backoff_factor=3.0,  # More aggressive backoff for phish.net
        rate_limit_calls=95,  # Increased from 80 to reduce wait time (still under 1000/day limit)
        rate_limit_window=60,
        user_agent=f"{JAMBANNERD_BOT_UA} (Phish Data Collection)",
        cache_enabled=True,
        cache_ttl_seconds=DEFAULT_CACHE_TTL,
        cache_dir=CACHE_DIR,
    ),
    "wsp": CollectorConfig(
        base_url="http://www.everydaycompanion.com",
        timeout=60,
        max_retries=5,
        backoff_factor=2.0,
        rate_limit_calls=60,
        rate_limit_window=60,
        user_agent=f"{JAMBANNERD_BOT_UA} (Widespread Panic Data Collection)",
        cache_enabled=True,
        cache_ttl_seconds=DEFAULT_CACHE_TTL,
        cache_dir=CACHE_DIR,
    ),
    "billy": CollectorConfig(
        base_url="https://bmfsdb.com",
        timeout=120,
        max_retries=4,
        backoff_factor=2.0,
        rate_limit_calls=45,
        rate_limit_window=60,
        user_agent=f"{JAMBANNERD_BOT_UA} (Billy Strings Data Collection)",
        cache_enabled=True,
        cache_ttl_seconds=DEFAULT_CACHE_TTL,
        cache_dir=CACHE_DIR,
    ),
    "um": CollectorConfig(
        base_url="https://allthings.umphreys.com",
        timeout=60,
        max_retries=5,
        backoff_factor=2.0,
        rate_limit_calls=45,
        rate_limit_window=60,
        user_agent=f"{JAMBANNERD_BOT_UA} (Umphrey's McGee Data Collection)",
        cache_enabled=True,
        cache_ttl_seconds=DEFAULT_CACHE_TTL,
        cache_dir=CACHE_DIR,
    ),
}


def get_collector_config(band: str) -> CollectorConfig:
    """Get configuration for a specific band collector.

    Args:
        band: The band name ('goose', 'phish', etc.)

    Returns:
        CollectorConfig: Configuration for the specified band

    Raises:
        ValueError: If band is not supported
    """
    if band not in COLLECTOR_CONFIGS:
        supported = ", ".join(COLLECTOR_CONFIGS.keys())
        raise ValueError(f"Unsupported band '{band}'. Supported bands: {supported}")

    return COLLECTOR_CONFIGS[band]
