"""Tests for WSPFastPredictor."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from jambandnerd.models.wsp.fast_predictor import (
    WSPFastCandidateCareer150,
    WSPFastCandidateRecent200,
    WSPFastGapDecoupled,
    WSPFastGapDecoupledClean,
    WSPFastNotebookRank,
    WSPFastPlaysPastYear,
    WSPFastPredictor,
    WSPFastVenueRun,
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


class TestWSPFastPredictor:
    """Test suite for WSPFastPredictor V2."""

    def test_init_defaults(self):
        predictor = WSPFastPredictor()
        assert predictor.band == "wsp"
        assert predictor.MODEL_VERSION == "wsp_fast_gbm_v2"
        assert predictor._model is None
        assert "plays_past_100" in predictor._FEATURE_COLS
        assert "diff_50_to_100" in predictor._FEATURE_COLS
        assert "long_rotation_pressure" in predictor._FEATURE_COLS

    def test_init_wrong_band_raises(self):
        with pytest.raises(ValueError, match="only supports band='wsp'"):
            WSPFastPredictor(band="goose")

    def test_model_version_property(self):
        predictor = WSPFastPredictor()
        assert predictor.MODEL_VERSION == "wsp_fast_gbm_v2"

    def test_diagnostic_feature_columns(self):
        predictor = WSPFastPredictor()
        assert "gap_shows" in predictor.diagnostic_feature_columns
        assert "tour_position" in predictor.diagnostic_feature_columns
        assert "plays_past_5" in predictor.diagnostic_feature_columns
        assert "plays_past_100" in predictor.diagnostic_feature_columns

    def test_lgb_params_v2(self):
        predictor = WSPFastPredictor()
        assert predictor._LGB_PARAMS["learning_rate"] == 0.03
        assert predictor._LGB_PARAMS["num_leaves"] == 31
        assert predictor._LGB_ROUNDS == 700


class TestCandidateHooks:
    """Test that WSP candidate hooks override Phish defaults."""

    def test_default_candidate_values(self):
        predictor = WSPFastPredictor()
        assert predictor._candidate_recent_shows() == 150
        assert predictor._candidate_top_career() == 100

    def test_candidate_recent_200_overrides(self):
        predictor = WSPFastCandidateRecent200()
        assert predictor._candidate_recent_shows() == 200
        assert predictor._candidate_top_career() == 100

    def test_candidate_career_150_overrides(self):
        predictor = WSPFastCandidateCareer150()
        assert predictor._candidate_recent_shows() == 150
        assert predictor._candidate_top_career() == 150


class TestFeatureExperimentSubclasses:
    """Test that feature experiment classes are importable and correctly configured."""

    def test_plays_past_year_model_version(self):
        predictor = WSPFastPlaysPastYear()
        assert predictor.MODEL_VERSION == "wsp_fast_gbm_v2_feat_plays_past_year"
        assert "plays_past_year" in predictor._FEATURE_COLS
        assert "plays_past_100" in predictor._FEATURE_COLS

    def test_notebook_rank_model_version(self):
        predictor = WSPFastNotebookRank()
        assert predictor.MODEL_VERSION == "wsp_fast_gbm_v2_feat_notebook_rank"
        assert "notebook_rank_score" in predictor._FEATURE_COLS
        assert "plays_past_year" in predictor._FEATURE_COLS

    def test_venue_run_model_version(self):
        predictor = WSPFastVenueRun()
        assert predictor.MODEL_VERSION == "wsp_fast_gbm_v2_feat_venue_run"
        assert "same_venue_run_prior_played" in predictor._FEATURE_COLS
        assert "same_venue_run_prior_play_count" in predictor._FEATURE_COLS
        assert "same_venue_run_prior_play_share" in predictor._FEATURE_COLS

    def test_notebook_rank_inherits_plays_past_year(self):
        predictor = WSPFastNotebookRank()
        assert isinstance(predictor, WSPFastPlaysPastYear)
        assert isinstance(predictor, WSPFastPredictor)


class TestGapDecoupledSubclasses:
    """Test WSPFastGapDecoupled and WSPFastGapDecoupledClean."""

    def test_gap_decoupled_feature_count(self):
        predictor = WSPFastGapDecoupled()
        assert len(predictor._FEATURE_COLS) == 21
        assert "gap_percentile" in predictor._FEATURE_COLS
        assert "gap_vs_median" in predictor._FEATURE_COLS
        assert "overdue_ratio" in predictor._FEATURE_COLS
        assert "long_rotation_pressure" in predictor._FEATURE_COLS

    def test_gap_decoupled_model_version(self):
        predictor = WSPFastGapDecoupled()
        assert predictor.MODEL_VERSION == "wsp_fast_gbm_v2_gap_decoupled"

    def test_gap_decoupled_clean_feature_count(self):
        predictor = WSPFastGapDecoupledClean()
        assert len(predictor._FEATURE_COLS) == 19
        assert "gap_percentile" in predictor._FEATURE_COLS
        assert "gap_vs_median" in predictor._FEATURE_COLS
        assert "overdue_ratio" not in predictor._FEATURE_COLS
        assert "long_rotation_pressure" not in predictor._FEATURE_COLS

    def test_gap_decoupled_clean_model_version(self):
        predictor = WSPFastGapDecoupledClean()
        assert predictor.MODEL_VERSION == "wsp_fast_gbm_v2_gap_decoupled_clean"

    def test_gap_decoupled_inherits_wsp(self):
        assert issubclass(WSPFastGapDecoupled, WSPFastPredictor)
        assert issubclass(WSPFastGapDecoupledClean, WSPFastPredictor)


class TestWSPExperiments:
    """Test WSP experiment sweep registration."""

    def test_sweeps_are_registered(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        assert set(WSP_SWEEPS) == {
            "candidate_sweep",
            "hp_sweep",
            "feature_sweep",
            "combo_sweep",
            "es_sweep",
            "fixed_round_sweep",
            "gap_decoupled_sweep",
            "venue_run_sweep",
        }
        assert len(WSP_SWEEPS["candidate_sweep"]) == 5
        assert len(WSP_SWEEPS["hp_sweep"]) >= 1
        assert len(WSP_SWEEPS["feature_sweep"]) == 3
        assert len(WSP_SWEEPS["combo_sweep"]) == 6
        assert len(WSP_SWEEPS["es_sweep"]) == 6
        assert len(WSP_SWEEPS["fixed_round_sweep"]) == 7
        assert len(WSP_SWEEPS["gap_decoupled_sweep"]) == 3
        assert len(WSP_SWEEPS["venue_run_sweep"]) == 3

    def test_feature_sweep_uses_explicit_predictors(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        predictor_paths = [
            config.predictor_path for config in WSP_SWEEPS["feature_sweep"]
        ]
        assert all(
            path.startswith("jambandnerd.models.wsp.") for path in predictor_paths
        )

    def test_candidate_sweep_uses_explicit_predictors(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        predictor_paths = [
            config.predictor_path for config in WSP_SWEEPS["candidate_sweep"]
        ]
        assert all(
            path.startswith("jambandnerd.models.wsp.") for path in predictor_paths
        )

    def test_combo_sweep_uses_base_predictor_path(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        base = "jambandnerd.models.wsp.fast_predictor.WSPFastPredictor"
        for config in WSP_SWEEPS["combo_sweep"]:
            assert config.base_predictor_path == base, (
                f"{config.slug}: expected base_predictor_path={base!r}"
            )
            assert config.predictor_path == "", (
                f"{config.slug}: should not have explicit predictor_path"
            )

    def test_es_sweep_uses_base_predictor_path(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        base = "jambandnerd.models.wsp.fast_predictor.WSPFastPredictor"
        for config in WSP_SWEEPS["es_sweep"]:
            assert config.base_predictor_path == base
            assert config.predictor_path == ""

    def test_es_sweep_attr_overrides_valid(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        allowed = {"_EARLY_STOPPING_ROUNDS", "_VALIDATION_FRACTION"}
        for config in WSP_SWEEPS["es_sweep"]:
            assert set(config.attr_overrides.keys()).issubset(allowed), (
                f"{config.slug}: unexpected attr_overrides keys "
                f"{set(config.attr_overrides.keys()) - allowed}"
            )

    def test_fixed_round_sweep_no_early_stopping(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        for config in WSP_SWEEPS["fixed_round_sweep"]:
            assert config.attr_overrides.get("_EARLY_STOPPING_ROUNDS") is None, (
                f"{config.slug}: should disable early stopping"
            )
            assert config.base_predictor_path.startswith(
                "jambandnerd.models.wsp."
            )
            assert config.predictor_path == ""
            assert config.round_overrides is not None

    def test_make_experiment_predictor_applies_attr_overrides(self):
        from jambandnerd.models.experiment import make_experiment_predictor
        cls = make_experiment_predictor(
            WSPFastPredictor,
            slug_suffix="test_es",
            attr_overrides={"_EARLY_STOPPING_ROUNDS": None, "_VALIDATION_FRACTION": 0.1},
        )
        assert cls._EARLY_STOPPING_ROUNDS is None
        assert cls._VALIDATION_FRACTION == 0.1
        assert cls.MODEL_VERSION == "wsp_fast_gbm_v2_test_es"

    def test_gap_decoupled_sweep_uses_explicit_predictors(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        predictor_paths = [
            config.predictor_path for config in WSP_SWEEPS["gap_decoupled_sweep"]
        ]
        assert all(
            path.startswith("jambandnerd.models.wsp.") for path in predictor_paths
        )

    def test_gap_decoupled_sweep_slugs(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        slugs = [c.slug for c in WSP_SWEEPS["gap_decoupled_sweep"]]
        assert slugs == ["gd_default", "gd_fr50", "gd_clean_fr50"]

    def test_venue_run_sweep_uses_explicit_predictors(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        predictor_paths = [
            config.predictor_path for config in WSP_SWEEPS["venue_run_sweep"]
        ]
        assert all(
            path.startswith("jambandnerd.models.wsp.") for path in predictor_paths
        )

    def test_venue_run_sweep_slugs(self):
        from jambandnerd.models.wsp.experiments import WSP_SWEEPS
        slugs = [c.slug for c in WSP_SWEEPS["venue_run_sweep"]]
        assert slugs == ["vr_default", "vr_fr50", "vr_fr50_lam01"]


class TestIntegration:
    """Integration tests with sample data."""

    def test_predict_without_train_returns_empty(self):
        predictor = WSPFastPredictor()
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
        predictor = WSPFastPredictor()
        plays = pd.DataFrame(
            {
                "song_name": [],
                "show_index": [],
                "show_date": [],
            }
        )
        model_data = _model_data(plays, date(2024, 1, 1))
        predictor.train(model_data)
        assert predictor._model is None

    def test_train_with_insufficient_shows(self):
        predictor = WSPFastPredictor()
        plays = pd.DataFrame(
            {
                "song_name": ["Song A"] * 5,
                "show_index": list(range(1, 6)),
                "show_date": pd.date_range("2024-01-01", periods=5),
            }
        )
        model_data = _model_data(plays, date(2024, 1, 6))
        predictor.train(model_data)
        assert predictor._model is None


class TestRegistryIntegration:
    """Test that WSP is correctly registered in model registry."""

    def test_band_predictor_dispatches_wsp(self):
        from src.jambandnerd.models.registry import (
            build_band_predictor,
            get_band_model_version,
        )
        wsp = build_band_predictor("wsp", persist_artifacts=False)
        assert isinstance(wsp, WSPFastPredictor)
        assert get_band_model_version("wsp") == "wsp_fast_gbm_v2"
