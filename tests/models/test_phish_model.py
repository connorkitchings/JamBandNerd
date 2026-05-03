"""Tests for PhishFastPredictor."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from jambandnerd.models.phish.fast_predictor import (
    PHISH_FAST_DIAGNOSTIC_FEATURE_COLS,
    PHISH_FAST_FEATURE_COLS,
    PhishFastPredictor,
    PhishPrediction,
    _build_gap_matrix,
    _build_presence,
    _clean_plays,
    _get_candidate_songs,
    _run_position,
    _tour_position,
    _window_plays,
    _window_plays_by_days,
)
from jambandnerd.transformations.gaps import ModelData


class TestPhishFastPredictor:
    """Test suite for PhishFastPredictor."""

    def test_init_defaults(self):
        """Test predictor initialization with defaults."""
        predictor = PhishFastPredictor()
        assert predictor.band == "phish"
        assert predictor.MODEL_VERSION == "phish_fast_gbm_v1"
        assert predictor._model is None
        assert predictor._FEATURE_COLS == PHISH_FAST_FEATURE_COLS

    def test_init_wrong_band_raises(self):
        """Test that wrong band raises ValueError."""
        with pytest.raises(ValueError, match="only supports band='phish'"):
            PhishFastPredictor(band="goose")

    def test_model_version_property(self):
        """Test MODEL_VERSION is accessible as property."""
        predictor = PhishFastPredictor()
        assert predictor.MODEL_VERSION == "phish_fast_gbm_v1"

    def test_diagnostic_feature_columns(self):
        """Test diagnostic columns include all features."""
        predictor = PhishFastPredictor()
        assert "gap_shows" in predictor.diagnostic_feature_columns
        assert "plays_past_2yr" in predictor.diagnostic_feature_columns
        assert "tour_position" in predictor.diagnostic_feature_columns


class TestHelperFunctions:
    """Test helper functions."""

    def test_clean_plays_basic(self):
        """Test basic play cleaning."""
        plays = pd.DataFrame({
            "song_name": ["Song A", "Song B"],
            "show_index": [1, 1],
            "show_date": ["2024-01-01", "2024-01-01"],
        })
        cleaned = _clean_plays(plays)
        assert len(cleaned) == 2
        assert cleaned["show_index"].dtype == int

    def test_build_presence(self):
        """Test presence matrix building."""
        plays = pd.DataFrame({
            "song_name": ["Song A", "Song A", "Song B"],
            "show_index": [1, 2, 1],
            "show_date": ["2024-01-01", "2024-01-02", "2024-01-01"],
        })
        plays["show_date"] = pd.to_datetime(plays["show_date"])
        presence, show_cols = _build_presence(plays)
        assert presence.shape == (2, 2)  # 2 songs, 2 shows
        assert presence.loc["Song A", 1] == True
        assert presence.loc["Song A", 2] == True
        assert presence.loc["Song B", 2] == False

    def test_build_gap_matrix(self):
        """Test gap matrix building."""
        plays = pd.DataFrame({
            "song_name": ["Song A", "Song A", "Song A"],
            "show_index": [1, 2, 4],
            "show_date": ["2024-01-01", "2024-01-02", "2024-01-04"],
        })
        plays["show_date"] = pd.to_datetime(plays["show_date"])
        presence, _ = _build_presence(plays)
        gap_mat = _build_gap_matrix(presence)
        # At column 4 (show 4), gap since last play (show 2) should be 2
        assert gap_mat.loc["Song A", 4] == 2.0

    def test_window_plays(self):
        """Test window play counting."""
        plays = pd.DataFrame({
            "song_name": ["Song A"] * 5,
            "show_index": [1, 2, 3, 4, 5],
            "show_date": pd.date_range("2024-01-01", periods=5),
        })
        presence, _ = _build_presence(plays)
        cum = presence.astype(float).cumsum(axis=1)
        # At show 5, plays in last 2 shows (shows 3-4)
        window_plays = _window_plays(cum, 5, 2)
        assert window_plays.loc["Song A"] == 2.0

    def test_run_position(self):
        """Test run position calculation."""
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 3),
        ]
        target = date(2024, 1, 4)
        # Consecutive days, so position should be 4 (4th in run)
        assert _run_position(dates, target, gap_days=1) == 4

    def test_tour_position(self):
        """Test tour position calculation."""
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 10),
            date(2024, 1, 20),
        ]
        target = date(2024, 1, 25)
        # Within 14 days of last show, so position should be 4
        assert _tour_position(dates, target, tour_gap_days=14) == 4


class TestCandidatePruning:
    """Test candidate song pruning functionality."""

    def test_get_candidate_songs_basic(self):
        """Test candidate selection with recent + top career."""
        # Create presence matrix with 200 shows
        songs = [f"Song {i}" for i in range(10)]
        show_indices = list(range(1, 201))
        
        # Song 0: played in last 50 shows only
        # Song 1: played early only (career high)
        # Song 2: played throughout
        data = []
        for show_idx in show_indices:
            if show_idx > 150:  # Recent shows
                data.append({"song_name": "Song 0", "show_index": show_idx})
                data.append({"song_name": "Song 2", "show_index": show_idx})
            if show_idx <= 50:  # Early shows
                data.append({"song_name": "Song 1", "show_index": show_idx})
                data.append({"song_name": "Song 2", "show_index": show_idx})
        
        plays = pd.DataFrame(data)
        plays["show_date"] = pd.date_range("2020-01-01", periods=len(data))
        presence, _ = _build_presence(plays)
        cum = presence.astype(float).cumsum(axis=1)
        
        # Get candidates at show 200
        candidates = _get_candidate_songs(
            presence, cum, ref_col=199, recent_shows=50, top_career=5
        )
        
        # Should include Song 0 (recent) and Song 1 (top career) and Song 2 (both)
        assert "Song 0" in candidates
        assert "Song 1" in candidates
        assert "Song 2" in candidates


class TestPredictionResult:
    """Test prediction result dataclass."""

    def test_phish_prediction_creation(self):
        """Test PhishPrediction dataclass."""
        pred = PhishPrediction(
            song_name="Tweezer",
            probability=0.85,
            gap_shows=5,
        )
        assert pred.song_name == "Tweezer"
        assert pred.probability == 0.85
        assert pred.gap_shows == 5


class TestIntegration:
    """Integration tests with sample data."""

    def test_predict_without_train_returns_empty(self):
        """Test that predict without training returns empty list."""
        predictor = PhishFastPredictor()
        # Create minimal ModelData
        plays = pd.DataFrame({
            "song_name": ["Song A"],
            "show_index": [1],
            "show_date": pd.to_datetime(["2024-01-01"]),
        })
        model_data = ModelData(
            historical_plays=plays,
            reference_date=date(2024, 1, 2),
        )
        predictions = predictor.predict(model_data, top_k=10)
        assert predictions == []

    def test_train_with_empty_plays(self):
        """Test training with empty plays doesn't crash."""
        predictor = PhishFastPredictor()
        plays = pd.DataFrame({
            "song_name": [],
            "show_index": [],
            "show_date": [],
        })
        model_data = ModelData(
            historical_plays=plays,
            reference_date=date(2024, 1, 1),
        )
        predictor.train(model_data)  # Should not raise
        assert predictor._model is None

    def test_train_with_insufficient_shows(self):
        """Test training with too few shows doesn't crash."""
        predictor = PhishFastPredictor()
        # Only 5 shows, need at least 30
        plays = pd.DataFrame({
            "song_name": ["Song A"] * 5,
            "show_index": list(range(1, 6)),
            "show_date": pd.date_range("2024-01-01", periods=5),
        })
        model_data = ModelData(
            historical_plays=plays,
            reference_date=date(2024, 1, 6),
        )
        predictor.train(model_data)
        # Should have no model since not enough training data
        assert predictor._model is None
