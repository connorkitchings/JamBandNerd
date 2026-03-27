from __future__ import annotations

import pytest

from src.jambandnerd.models.registry import (
    build_predictor,
    get_aggregate_accuracy_table,
    get_model_definition,
    list_accuracy_validation_models,
    list_aggregate_accuracy_models,
    list_backfill_models,
    list_model_slugs,
    list_models,
    list_pipeline_models,
    list_web_models,
)


def test_registry_includes_expected_models() -> None:
    slugs = list_model_slugs()
    assert slugs == ["notebook", "ckplus", "deal"]


def test_registry_capability_lists_are_flag_driven() -> None:
    assert [definition.slug for definition in list_pipeline_models()] == [
        "notebook",
        "ckplus",
    ]
    assert [definition.slug for definition in list_web_models()] == [
        "notebook",
        "ckplus",
    ]
    assert [definition.slug for definition in list_backfill_models()] == [
        "notebook",
        "ckplus",
    ]
    assert [definition.slug for definition in list_accuracy_validation_models()] == [
        "notebook",
        "ckplus",
    ]
    assert [definition.slug for definition in list_aggregate_accuracy_models()] == [
        "notebook",
        "ckplus",
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

        if definition.enabled_for_web:
            assert definition.supports_live_predictions

        if definition.enabled_for_pipeline:
            assert definition.supports_backtest

        if definition.enabled_for_accuracy_validation:
            assert get_aggregate_accuracy_table(definition.slug) is not None
