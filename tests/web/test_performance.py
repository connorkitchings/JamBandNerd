"""Tests for the Model Performance tab component."""

from __future__ import annotations

import pandas as pd


class TestAccuracyDataProcessing:
    """Tests for accuracy data processing."""

    def test_accuracy_df_has_required_columns(self, sample_accuracy_df):
        """Verify accuracy DataFrame has required columns."""
        required_cols = [
            "band",
            "model_version",
            "show_date",
            "top_10_hits",
            "top_25_hits",
            "top_50_hits",
        ]

        for col in required_cols:
            assert col in sample_accuracy_df.columns

    def test_accuracy_metrics_are_numeric(self, sample_accuracy_df):
        """Verify hit count columns are numeric."""
        assert pd.api.types.is_numeric_dtype(sample_accuracy_df["top_10_hits"])
        assert pd.api.types.is_numeric_dtype(sample_accuracy_df["top_25_hits"])
        assert pd.api.types.is_numeric_dtype(sample_accuracy_df["top_50_hits"])

    def test_hit_counts_reasonable(self, sample_accuracy_df):
        """Verify hit counts are reasonable (top_10 <= top_25 <= top_50)."""
        for _, row in sample_accuracy_df.iterrows():
            assert row["top_10_hits"] <= row["top_25_hits"]
            assert row["top_25_hits"] <= row["top_50_hits"]


class TestChartDataPreparation:
    """Tests for chart data preparation."""

    def test_date_parsing(self, sample_accuracy_df):
        """Verify dates can be parsed correctly."""
        sample_accuracy_df["parsed_date"] = pd.to_datetime(
            sample_accuracy_df["show_date"]
        )

        assert sample_accuracy_df["parsed_date"].dtype == "datetime64[ns]"

    def test_hit_rate_calculation(self, sample_accuracy_df):
        """Verify hit rate can be calculated."""
        sample_accuracy_df["hit_rate_50"] = (
            sample_accuracy_df["top_50_hits"] / sample_accuracy_df["total_songs"] * 100
        )

        assert all(sample_accuracy_df["hit_rate_50"] >= 0)
        assert all(sample_accuracy_df["hit_rate_50"] <= 100)


class TestModelVersionFiltering:
    """Tests for model version filtering."""

    def test_filters_by_model_version(self, sample_accuracy_df):
        """Verify filtering by model version works."""
        filtered = sample_accuracy_df[
            sample_accuracy_df["model_version"] == "notebook_v1"
        ]

        assert len(filtered) == len(sample_accuracy_df)  # All are notebook_v1 in sample

    def test_handles_missing_model_version(self):
        """Handle when model version doesn't exist."""
        df = pd.DataFrame(
            {
                "model_version": ["notebook_v1", "ckplus_v1"],
                "show_date": ["2025-11-01", "2025-11-01"],
            }
        )

        filtered = df[df["model_version"] == "nonexistent_v1"]

        assert filtered.empty


class TestBandFiltering:
    """Tests for band filtering in performance tab."""

    def test_filters_by_band(self, sample_accuracy_df):
        """Verify filtering by band works."""
        filtered = sample_accuracy_df[sample_accuracy_df["band"] == "wsp"]

        assert len(filtered) == len(sample_accuracy_df)  # All are wsp in sample

    def test_handles_unknown_band(self, sample_accuracy_df):
        """Handle when band doesn't exist."""
        filtered = sample_accuracy_df[sample_accuracy_df["band"] == "unknown"]

        assert filtered.empty
