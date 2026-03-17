"""Tests for the Predictions tab component."""

from __future__ import annotations

import pandas as pd


class TestFormatPredictionsDf:
    """Tests for format_predictions_df function."""

    def test_notebook_columns_selected(self, sample_predictions_notebook):
        """Verify correct columns are selected for Notebook model."""
        from jambandnerd.web.components.tabs.predictions import format_predictions_df

        result = format_predictions_df(sample_predictions_notebook, "notebook")

        assert not result.empty
        # Check renamed columns exist
        assert "Song" in result.columns or "song_name" in result.columns
        assert "Rank" in result.columns or "rank" in result.columns

    def test_ckplus_columns_selected(self, sample_predictions_ckplus):
        """Verify correct columns are selected for CK+ model."""
        from jambandnerd.web.components.tabs.predictions import format_predictions_df

        result = format_predictions_df(sample_predictions_ckplus, "ckplus")

        assert not result.empty
        # CK+ should include gap metrics
        expected_cols = ["Song", "Rank", "Gap Ratio", "CK+ Score"]
        for col in expected_cols:
            # Check either original or renamed version exists
            assert (
                col in result.columns or col.lower().replace(" ", "_") in result.columns
            )

    def test_handles_empty_dataframe(self):
        """Verify empty DataFrame is handled gracefully."""
        from jambandnerd.web.components.tabs.predictions import format_predictions_df

        result = format_predictions_df(pd.DataFrame(), "notebook")

        assert result.empty

    def test_handles_unknown_model(self, sample_predictions_notebook):
        """Verify unknown model returns empty DataFrame."""
        from jambandnerd.web.components.tabs.predictions import format_predictions_df

        result = format_predictions_df(sample_predictions_notebook, "unknown_model")

        assert result.empty

    def test_missing_columns_handled(self):
        """Verify missing columns don't cause errors."""
        from jambandnerd.web.components.tabs.predictions import format_predictions_df

        # DataFrame missing some expected columns
        df = pd.DataFrame(
            {
                "song_name": ["Song A", "Song B"],
                "rank": [1, 2],
                # Missing: plays_past_year, current_gap, LTP
            }
        )

        result = format_predictions_df(df, "notebook")

        # Should not raise, but may have limited columns
        assert "Song" in result.columns or "song_name" in result.columns


class TestModelConfig:
    """Tests for MODEL_CONFIG validation."""

    def test_notebook_config_exists(self):
        """Verify Notebook model config is defined."""
        from jambandnerd.web.components.tabs.predictions import MODEL_CONFIG

        assert "notebook" in MODEL_CONFIG
        assert "display_name" in MODEL_CONFIG["notebook"]
        assert "columns" in MODEL_CONFIG["notebook"]

    def test_ckplus_config_exists(self):
        """Verify CK+ model config is defined."""
        from jambandnerd.web.components.tabs.predictions import MODEL_CONFIG

        assert "ckplus" in MODEL_CONFIG
        assert "display_name" in MODEL_CONFIG["ckplus"]
        assert "columns" in MODEL_CONFIG["ckplus"]

    def test_model_explanations_present(self):
        """Verify model explanations are provided."""
        from jambandnerd.web.components.tabs.predictions import MODEL_CONFIG

        for model_key in ["notebook", "ckplus"]:
            assert "explanation" in MODEL_CONFIG[model_key]
            assert (
                len(MODEL_CONFIG[model_key]["explanation"]) > 50
            )  # Non-trivial explanation
