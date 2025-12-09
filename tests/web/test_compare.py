"""Tests for the Compare Bands tab component."""

from __future__ import annotations

import pandas as pd
import pytest


class TestBandComparisonData:
    """Tests for band comparison data preparation."""

    def test_aggregates_across_bands(self):
        """Verify data can be aggregated across multiple bands."""
        # Sample multi-band accuracy data
        df = pd.DataFrame(
            {
                "band": ["wsp", "wsp", "goose", "goose", "phish"],
                "model_version": ["notebook_v1"] * 5,
                "top_50_hits": [15, 18, 20, 22, 14],
                "total_songs": [22, 24, 25, 26, 20],
            }
        )

        # Aggregate by band
        agg = (
            df.groupby("band")
            .agg(
                {
                    "top_50_hits": "mean",
                    "total_songs": "mean",
                }
            )
            .reset_index()
        )

        assert len(agg) == 3  # wsp, goose, phish
        assert "wsp" in agg["band"].values
        assert "goose" in agg["band"].values
        assert "phish" in agg["band"].values

    def test_calculates_hit_rate_per_band(self):
        """Verify hit rate is calculated correctly per band."""
        df = pd.DataFrame(
            {
                "band": ["wsp", "goose"],
                "top_50_hits": [15, 20],
                "total_songs": [25, 25],
            }
        )

        df["hit_rate"] = df["top_50_hits"] / df["total_songs"] * 100

        assert df.loc[df["band"] == "wsp", "hit_rate"].values[0] == 60.0
        assert df.loc[df["band"] == "goose", "hit_rate"].values[0] == 80.0


class TestCrossBandMetrics:
    """Tests for cross-band metric calculations."""

    def test_compares_model_performance(self):
        """Verify models can be compared across bands."""
        df = pd.DataFrame(
            {
                "band": ["wsp", "wsp", "goose", "goose"],
                "model_version": [
                    "notebook_v1",
                    "ckplus_v1",
                    "notebook_v1",
                    "ckplus_v1",
                ],
                "top_50_hits": [15, 18, 20, 19],
                "total_songs": [25, 25, 25, 25],
            }
        )

        # Pivot to compare models
        pivot = df.pivot_table(
            values="top_50_hits", index="band", columns="model_version", aggfunc="mean"
        )

        assert "notebook_v1" in pivot.columns
        assert "ckplus_v1" in pivot.columns
        assert pivot.loc["wsp", "ckplus_v1"] > pivot.loc["wsp", "notebook_v1"]


class TestBandConfiguration:
    """Tests for band configuration in comparisons."""

    def test_all_bands_have_display_names(self):
        """Verify all configured bands have display names."""
        from jambandnerd.web.config import BAND_CONFIG

        for band_key, config in BAND_CONFIG.items():
            assert "display_name" in config
            assert len(config["display_name"]) > 0

    def test_active_bands_are_valid(self):
        """Verify active bands are in configuration."""
        from jambandnerd.web.config import ACTIVE_BANDS, BAND_CONFIG

        for band in ACTIVE_BANDS:
            assert band in BAND_CONFIG, f"Active band '{band}' not in BAND_CONFIG"


class TestChartGeneration:
    """Tests for comparison chart data generation."""

    def test_bar_chart_data_structure(self):
        """Verify data structure suitable for bar charts."""
        df = pd.DataFrame(
            {
                "band": ["WSP", "Goose", "Phish"],
                "avg_hit_rate": [65.0, 72.0, 58.0],
            }
        )

        # Should be sortable for visualization
        sorted_df = df.sort_values("avg_hit_rate", ascending=False)

        assert sorted_df.iloc[0]["band"] == "Goose"
        assert sorted_df.iloc[-1]["band"] == "Phish"
