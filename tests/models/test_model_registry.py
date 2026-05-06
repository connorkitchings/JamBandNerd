from __future__ import annotations

import pytest

from src.jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    is_model_promoted_to_web,
    list_accuracy_validation_models,
    list_backfill_models,
    list_model_slugs,
    list_models,
    list_pipeline_models,
    list_promoted_web_models,
    list_web_models,
)


def test_registry_includes_expected_models() -> None:
    slugs = list_model_slugs()
    assert slugs == ["notebook", "deal"]


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

    assert notebook.lifecycle_stage == "web_promoted"
    assert notebook.web_visibility == "promoted"
    assert deal.lifecycle_stage == "web_promoted"
    assert deal.web_visibility == "promoted"
    assert deal.readiness_windows == (50,)
    assert deal.readiness_baselines == ("notebook",)
