from __future__ import annotations

import pytest

from jambandnerd.models.billy.fast_predictor import BillyFastBaselinePredictor
from jambandnerd.models.goose.model import GooseFastRankSpecialNotebookTop10Predictor
from jambandnerd.models.phish.fast_predictor import PhishFastPredictor
from jambandnerd.models.um.fast_predictor import UMFastPredictorV2
from jambandnerd.models.wsp.fast_predictor import WSPFastPredictor
from src.jambandnerd.models.registry import (
    build_band_predictor,
    build_predictor,
    get_band_model_version,
    get_model_definition,
    is_model_promoted_to_web,
    list_accuracy_validation_models,
    list_active_bands,
    list_backfill_models,
    list_model_slugs,
    list_models,
    list_pipeline_models,
    list_promoted_web_models,
    list_web_models,
)


def test_registry_includes_expected_models() -> None:
    slugs = list_model_slugs()
    assert slugs == ["notebook", "ckplus", "deal"]


def test_registry_capability_lists_are_flag_driven() -> None:
    assert [definition.slug for definition in list_pipeline_models()] == [
        "notebook",
        "deal",
    ]
    assert [definition.slug for definition in list_web_models()] == [
        "notebook",
        "deal",
    ]
    assert [definition.slug for definition in list_promoted_web_models()] == [
        "notebook",
        "deal",
    ]
    assert [definition.slug for definition in list_backfill_models()] == [
        "notebook",
        "deal",
    ]
    assert [definition.slug for definition in list_accuracy_validation_models()] == [
        "notebook",
        "deal",
    ]


def test_registry_unknown_slug_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown model slug"):
        get_model_definition("unknown")


def test_build_predictor_constructs_model_for_band() -> None:
    predictor = build_predictor("notebook", band="goose")
    assert predictor is not None


def test_active_band_predictors_dispatch_to_registered_single_models() -> None:
    expected = {
        "goose": (
            GooseFastRankSpecialNotebookTop10Predictor,
            "goose_fast_rank_v1_candidate_relaxed_special_nbtop10",
        ),
        "phish": (
            PhishFastPredictor,
            "phish_fast_gbm_v2_feat_notebook_rank_venue_run",
        ),
        "wsp": (WSPFastPredictor, "wsp_fast_gbm_v2"),
        "billy": (BillyFastBaselinePredictor, "billy_fast_gbm_v10_hp_tuned"),
        "um": (UMFastPredictorV2, "um_fast_gbm_v2"),
    }

    assert list_active_bands() == ["goose", "phish", "wsp", "billy", "um"]

    for band, (predictor_cls, model_version) in expected.items():
        predictor = build_band_predictor(band, persist_artifacts=False)

        assert isinstance(predictor, predictor_cls)
        assert predictor.MODEL_VERSION == model_version
        assert get_band_model_version(band) == model_version


def test_registry_invariants_for_serializer_and_capabilities() -> None:
    for definition in list_models():
        assert callable(definition.serializer)

        if is_model_promoted_to_web(definition.slug):
            assert definition.supports_live_predictions

        if definition.enabled_for_pipeline:
            assert definition.supports_backtest

        if definition.enabled_for_accuracy_validation:
            assert definition.supports_backtest


def test_registry_lifecycle_metadata_tracks_staged_rollout() -> None:
    notebook = get_model_definition("notebook")
    deal = get_model_definition("deal")
    ckplus = get_model_definition("ckplus")

    assert notebook.lifecycle_stage == "web_promoted"
    assert notebook.web_visibility == "promoted"
    assert deal.lifecycle_stage == "web_promoted"
    assert deal.web_visibility == "promoted"
    assert deal.readiness_windows == (100,)
    assert deal.readiness_baselines == ("notebook",)
    assert ckplus.lifecycle_stage == "retired"
