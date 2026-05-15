"""Tests for PhishFastPredictor."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from jambandnerd.models.phish.experiments import (
    PHISH_SWEEPS,
    PhishFastPlusShowType,
    PhishFastPredictorV3,
)
from jambandnerd.models.phish.fast_predictor import (
    PHISH_FAST_FEATURE_COLS,
    PhishFastPredictor,
    PhishFastPredictorV2,
    PhishPrediction,
    _build_gap_matrix,
    _build_presence,
    _clean_plays,
    _get_candidate_songs,
    _run_position,
    _tour_position,
    _window_plays,
)
from jambandnerd.transformations.gaps import ModelData


def _model_data(plays: pd.DataFrame, reference_date: date) -> ModelData:
    return ModelData(
        historical_plays=plays,
        master_feature_set=pd.DataFrame(),
        reference_date=reference_date,
        reference_index=0,
        recently_played_songs=[],
        diagnostics={},
    )


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

    def test_v2_defaults(self):
        """Test V2 is available as an experiment incumbent."""
        predictor = PhishFastPredictorV2()
        assert predictor.MODEL_VERSION == "phish_fast_gbm_v2"
        assert predictor._EARLY_STOPPING_ROUNDS == 25
        assert "plays_past_5" in predictor._FEATURE_COLS


class TestHelperFunctions:
    """Test helper functions."""

    def test_clean_plays_basic(self):
        """Test basic play cleaning."""
        plays = pd.DataFrame(
            {
                "song_name": ["Song A", "Song B"],
                "show_index": [1, 1],
                "show_date": ["2024-01-01", "2024-01-01"],
                "tour_name": ["Not Part of a Tour", "Not Part of a Tour"],
            }
        )
        cleaned = _clean_plays(plays)
        assert len(cleaned) == 2
        assert cleaned["show_index"].dtype == int
        assert cleaned["tour_name"].tolist() == [
            "Not Part of a Tour",
            "Not Part of a Tour",
        ]

    def test_build_presence(self):
        """Test presence matrix building."""
        plays = pd.DataFrame(
            {
                "song_name": ["Song A", "Song A", "Song B"],
                "show_index": [1, 2, 1],
                "show_date": ["2024-01-01", "2024-01-02", "2024-01-01"],
            }
        )
        plays["show_date"] = pd.to_datetime(plays["show_date"])
        presence, show_cols = _build_presence(plays)
        assert presence.shape == (2, 2)  # 2 songs, 2 shows
        assert presence.loc["Song A", 1]
        assert presence.loc["Song A", 2]
        assert not presence.loc["Song B", 2]

    def test_build_gap_matrix(self):
        """Test gap matrix building."""
        plays = pd.DataFrame(
            {
                "song_name": ["Song A", "Song A", "Song A"],
                "show_index": [1, 2, 4],
                "show_date": ["2024-01-01", "2024-01-02", "2024-01-04"],
            }
        )
        plays["show_date"] = pd.to_datetime(plays["show_date"])
        presence, _ = _build_presence(plays)
        gap_mat = _build_gap_matrix(presence)
        # Gap matrix uses dense show-column positions, not raw show_id deltas.
        assert gap_mat.loc["Song A", 4] == 1.0

    def test_window_plays(self):
        """Test window play counting."""
        plays = pd.DataFrame(
            {
                "song_name": ["Song A"] * 5,
                "show_index": [1, 2, 3, 4, 5],
                "show_date": pd.date_range("2024-01-01", periods=5),
            }
        )
        presence, _ = _build_presence(plays)
        cum = presence.astype(float).cumsum(axis=1)
        # upper_col is the first dense column not included, so this counts shows 4-5.
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
        # Only the immediately preceding date is within the 1-day continuation gap.
        assert _run_position(dates, target, gap_days=1) == 2

    def test_tour_position(self):
        """Test tour position calculation."""
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 10),
            date(2024, 1, 20),
        ]
        target = date(2024, 1, 25)
        # The previous show is within 14 days; the one before it is 15 days away.
        assert _tour_position(dates, target, tour_gap_days=14) == 2


class TestCandidatePruning:
    """Test candidate song pruning functionality."""

    def test_get_candidate_songs_basic(self):
        """Test candidate selection with recent + top career."""
        # Create presence matrix with 200 shows
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
        presence = presence.reindex(columns=show_indices, fill_value=False)
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


class TestPhishExperiments:
    """Test Phish experiment sweep registration."""

    def test_sweeps_are_registered(self):
        assert set(PHISH_SWEEPS) == {
            "hp_sweep",
            "feature_sweep",
            "combo_sweep",
            "show_type_sweep",
            "cleanup_ablation",
        }
        assert len(PHISH_SWEEPS["hp_sweep"]) >= 1
        assert len(PHISH_SWEEPS["feature_sweep"]) >= 1
        assert len(PHISH_SWEEPS["combo_sweep"]) == 7
        assert len(PHISH_SWEEPS["show_type_sweep"]) == 1
        assert len(PHISH_SWEEPS["cleanup_ablation"]) == 1

    def test_feature_sweep_uses_explicit_predictors(self):
        predictor_paths = [
            config.predictor_path for config in PHISH_SWEEPS["feature_sweep"]
        ]
        assert all(
            path.startswith("jambandnerd.models.phish.") for path in predictor_paths
        )

    def test_combo_sweep_uses_stacked_base_predictor(self):
        for config in PHISH_SWEEPS["combo_sweep"]:
            assert (
                config.base_predictor_path
                == "jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun"
            )
            assert not config.predictor_path

    def test_show_type_sweep_uses_explicit_predictor(self):
        config = PHISH_SWEEPS["show_type_sweep"][0]
        assert config.slug == "feat_show_type"
        assert (
            config.predictor_path
            == "jambandnerd.models.phish.experiments.PhishFastPlusShowType"
        )

    def test_cleanup_ablation_uses_cleaned_predictor_without_registry_promotion(self):
        config = PHISH_SWEEPS["cleanup_ablation"][0]
        predictor = PhishFastPredictorV3()

        assert config.slug == "cleanup_v3_dead_features"
        assert (
            config.predictor_path
            == "jambandnerd.models.phish.experiments.PhishFastPredictorV3"
        )
        assert predictor.MODEL_VERSION == "phish_fast_gbm_v3"
        assert "month_play_rate" not in predictor._FEATURE_COLS
        assert "plays_past_10" not in predictor._FEATURE_COLS
        assert "same_venue_run_prior_play_count" not in predictor._FEATURE_COLS

    def test_show_type_features_include_song_level_interactions(self):
        eligible_songs = pd.Index(["Tweezer", "Theme From the Bottom"])
        plays = pd.DataFrame(
            {
                "song_name": [
                    "Tweezer",
                    "Song A",
                    "Theme From the Bottom",
                    "Song B",
                ],
                "show_index": [1, 1, 2, 2],
                "show_date": pd.to_datetime(
                    ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]
                ),
                "tour_name": ["Not Part of a Tour"] * 4,
                "venue_name": ["NPR Headquarters"] * 4,
                "city": ["Washington"] * 4,
                "state": ["DC"] * 4,
                "country": ["USA"] * 4,
            }
        )
        features = PhishFastPlusShowType._show_type_features(
            eligible_songs=eligible_songs,
            plays=plays,
            target_show_context={
                "tour_name": "Not Part of a Tour",
                "venue_name": "NPR Headquarters",
                "city": "Washington",
                "state": "DC",
                "country": "USA",
            },
            career_pct=pd.Series([0.5, 0.2], index=eligible_songs),
            p50=pd.Series([10.0, 2.0], index=eligible_songs),
            notebook_rank_score=[0.9, 0.1],
        )

        assert features["is_not_part_of_tour"].tolist() == [1.0, 1.0]
        assert features["is_atypical_context"].tolist() == [1.0, 1.0]
        assert features["show_type_notebook_score"].tolist() == [0.9, 0.1]
        assert features["show_type_career_score"].tolist() == [0.5, 0.2]


class TestIntegration:
    """Integration tests with sample data."""

    def test_predict_without_train_returns_empty(self):
        """Test that predict without training returns empty list."""
        predictor = PhishFastPredictor()
        # Create minimal ModelData
        plays = pd.DataFrame(
            {
                "song_name": ["Song A"],
                "show_index": [1],
                "show_date": pd.to_datetime(["2024-01-01"]),
            }
        )
        model_data = _model_data(plays, date(2024, 1, 2))
        predictions = predictor.predict(model_data, top_k=10)
        assert predictions == []

    def test_train_with_empty_plays(self):
        """Test training with empty plays doesn't crash."""
        predictor = PhishFastPredictor()
        plays = pd.DataFrame(
            {
                "song_name": [],
                "show_index": [],
                "show_date": [],
            }
        )
        model_data = _model_data(plays, date(2024, 1, 1))
        predictor.train(model_data)  # Should not raise
        assert predictor._model is None

    def test_train_with_insufficient_shows(self):
        """Test training with too few shows doesn't crash."""
        predictor = PhishFastPredictor()
        # Only 5 shows, need at least 30
        plays = pd.DataFrame(
            {
                "song_name": ["Song A"] * 5,
                "show_index": list(range(1, 6)),
                "show_date": pd.date_range("2024-01-01", periods=5),
            }
        )
        model_data = _model_data(plays, date(2024, 1, 6))
        predictor.train(model_data)
        # Should have no model since not enough training data
        assert predictor._model is None
