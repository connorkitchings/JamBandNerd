"""Tests for band data collector structure and configuration.

These tests verify that every supported band has a valid collector config
and that collector modules expose the expected interface, without requiring
live API credentials or network access.
"""

from __future__ import annotations

import pytest

from jambandnerd.config.bands import SUPPORTED_BANDS
from jambandnerd.data_collection.config import COLLECTOR_CONFIGS, get_collector_config


class TestCollectorConfig:
    """Tests for the collector configuration registry."""

    def test_every_supported_band_has_config(self):
        """Every band in SUPPORTED_BANDS must have a matching collector config."""
        for band in SUPPORTED_BANDS:
            config = get_collector_config(band)
            assert config is not None, f"Missing collector config for {band}"

    def test_unsupported_band_raises(self):
        """Requesting config for a non-existent band raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported band"):
            get_collector_config("non_existent_band")

    def test_configs_have_required_fields(self):
        """All configs must have a base_url and positive timeout."""
        for band, config in COLLECTOR_CONFIGS.items():
            assert config.base_url, f"{band} config missing base_url"
            assert config.timeout > 0, f"{band} config has non-positive timeout"
            assert config.max_retries >= 0, f"{band} config has negative retries"
            assert config.rate_limit_calls > 0, f"{band} config has non-positive rate limit"

    def test_user_agent_is_set(self):
        """All configs should have a JamBandNerd user-agent string."""
        for band, config in COLLECTOR_CONFIGS.items():
            assert "JamBandNerd" in (config.user_agent or ""), (
                f"{band} config missing JamBandNerd user-agent"
            )
