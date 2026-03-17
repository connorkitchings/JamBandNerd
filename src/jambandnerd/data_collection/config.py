"""Configuration settings for data collectors."""

from .base import CollectorConfig

# Default configurations for each band's data collection
COLLECTOR_CONFIGS = {
    "goose": CollectorConfig(
        base_url="https://elgoose.net/api",
        timeout=30,
        max_retries=3,
        backoff_factor=2.0,
        rate_limit_calls=50,  # Be conservative with elgoose.net
        rate_limit_window=60,
        user_agent="JamBandNerd/1.0 (Goose Data Collection)",
    ),
    "eggy": CollectorConfig(
        base_url="https://thecarton.net/api",
        timeout=30,
        max_retries=3,
        backoff_factor=2.0,
        rate_limit_calls=50,
        rate_limit_window=60,
        user_agent="JamBandNerd/1.0 (Eggy Data Collection)",
    ),
    "phish": CollectorConfig(
        base_url="https://api.phish.net/v5",
        timeout=120,  # Phish API can be slow with large datasets
        max_retries=5,
        backoff_factor=3.0,  # More aggressive backoff for phish.net
        rate_limit_calls=95,  # Increased from 80 to reduce wait time (still under 1000/day limit)
        rate_limit_window=60,
        user_agent="JamBandNerd/1.0 (Phish Data Collection)",
    ),
    "wsp": CollectorConfig(
        base_url="http://www.everydaycompanion.com",
        timeout=60,
        max_retries=5,
        backoff_factor=2.0,
        rate_limit_calls=60,
        rate_limit_window=60,
        user_agent="JamBandNerd/1.0 (Widespread Panic Data Collection)",
    ),
    "billy": CollectorConfig(
        base_url="https://bmfsdb.com",
        timeout=120,
        max_retries=4,
        backoff_factor=2.0,
        rate_limit_calls=45,
        rate_limit_window=60,
        user_agent="JamBandNerd/1.0 (Billy Strings Data Collection)",
    ),
    "um": CollectorConfig(
        base_url="https://allthings.umphreys.com",
        timeout=60,
        max_retries=5,
        backoff_factor=2.0,
        rate_limit_calls=45,
        rate_limit_window=60,
        user_agent="JamBandNerd/1.0 (Umphrey's McGee Data Collection)",
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
