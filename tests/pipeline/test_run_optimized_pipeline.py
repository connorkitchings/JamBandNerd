from __future__ import annotations

from typing import Any

import pytest

from scripts import run_optimized_pipeline
from scripts.collection_preflight import CollectionPreflight

from .fixtures import BANDS

COLLECTION_RUNNERS = {
    "goose": "run_goose_collection",
    "eggy": "run_eggy_collection",
    "phish": "run_phish_collection",
    "wsp": "run_wsp_collection",
    "billy": "run_billy_collection",
    "um": "run_um_collection",
}


@pytest.fixture
def preflight_stub(monkeypatch):
    monkeypatch.setattr(
        run_optimized_pipeline,
        "compute_band_preflight",
        lambda band: CollectionPreflight(
            band=band,
            collection_mode="always_refresh",
            execution_mode="full_refresh",
            should_run_collection=True,
            recent_completed_show_count=0,
            missing_recent_setlist_count=0,
            upcoming_show_count=0,
            has_upcoming_show_soon=False,
            has_upcoming_show=False,
            last_successful_collection_at=None,
            supports_upstream_update_timestamp=False,
            skip_existing_setlists=False,
            recent_window_start="2026-03-10",
            recent_window_end="2026-03-16",
            lookahead_end="2026-03-31",
        ),
    )


@pytest.fixture
def pipeline_recorder(monkeypatch, preflight_stub):
    events: list[tuple[str, dict[str, Any]]] = []

    def record(name: str, return_value=None):
        def _inner(*args, **kwargs):
            events.append((name, {"args": args, "kwargs": kwargs}))
            return return_value

        return _inner

    for band, attr_name in COLLECTION_RUNNERS.items():
        monkeypatch.setattr(
            run_optimized_pipeline, attr_name, record(f"{band}:collect")
        )

    monkeypatch.setattr(
        run_optimized_pipeline,
        "_generate_band_predictions",
        record("generate_live_predictions"),
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_run_band_backtest",
        record("run_backtest", return_value=1),
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_validate_band_predictions",
        record("validate_predictions"),
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_validate_band_accuracy",
        record("validate_accuracy"),
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_validate_band_accuracy_skip_freshness",
        record("validate_accuracy_skip_freshness"),
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_audit_band_supabase",
        record("audit_supabase"),
    )

    return events


@pytest.mark.parametrize("band", BANDS)
def test_run_band_pipeline_executes_full_orchestrator_path(band, pipeline_recorder):
    success = run_optimized_pipeline.run_band_pipeline(band)

    assert success is True
    assert [event[0] for event in pipeline_recorder] == [
        f"{band}:collect",
        "generate_live_predictions",
        "run_backtest",
        "validate_predictions",
        "validate_accuracy",
        "audit_supabase",
    ]

    prediction = pipeline_recorder[1][1]["kwargs"]
    backtest = pipeline_recorder[2][1]["kwargs"]

    assert prediction == {"band": band}
    assert backtest == {"band": band}
    assert pipeline_recorder[3][1]["kwargs"] == {"band": band, "max_age_hours": 72}
    assert pipeline_recorder[4][1]["kwargs"] == {"band": band, "max_age_hours": 72}
    assert pipeline_recorder[5][1]["kwargs"] == {
        "band": band,
        "max_age_hours": 72,
        "skip_accuracy": False,
    }


@pytest.mark.parametrize("band", BANDS)
def test_run_band_pipeline_skip_accuracy_preserves_predictions_and_validation(
    band, monkeypatch, pipeline_recorder
):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("accuracy step should be skipped")

    monkeypatch.setattr(run_optimized_pipeline, "_run_band_backtest", fail_if_called)

    success = run_optimized_pipeline.run_band_pipeline(band, skip_accuracy=True)

    assert success is True
    assert [event[0] for event in pipeline_recorder] == [
        f"{band}:collect",
        "generate_live_predictions",
        "validate_predictions",
        "audit_supabase",
    ]
    assert pipeline_recorder[-1][1]["kwargs"] == {
        "band": band,
        "max_age_hours": 72,
        "skip_accuracy": True,
    }


def test_run_band_pipeline_skips_prediction_work_for_verify_only_preflight(
    monkeypatch, pipeline_recorder
):
    band = "goose"
    monkeypatch.setattr(
        run_optimized_pipeline,
        "compute_band_preflight",
        lambda band: CollectionPreflight(
            band=band,
            collection_mode="window_refresh",
            execution_mode="verify_only",
            should_run_collection=False,
            recent_completed_show_count=0,
            missing_recent_setlist_count=0,
            upcoming_show_count=0,
            has_upcoming_show_soon=False,
            has_upcoming_show=False,
            last_successful_collection_at=None,
            supports_upstream_update_timestamp=True,
            skip_existing_setlists=True,
            recent_window_start="2026-03-10",
            recent_window_end="2026-03-16",
            lookahead_end="2026-03-31",
        ),
    )

    success = run_optimized_pipeline.run_band_pipeline(band)

    assert success is True
    assert pipeline_recorder == []


def test_run_band_pipeline_force_overrides_verify_only_preflight(
    monkeypatch, pipeline_recorder
):
    band = "goose"
    monkeypatch.setattr(
        run_optimized_pipeline,
        "compute_band_preflight",
        lambda band: CollectionPreflight(
            band=band,
            collection_mode="window_refresh",
            execution_mode="verify_only",
            should_run_collection=False,
            recent_completed_show_count=0,
            missing_recent_setlist_count=0,
            upcoming_show_count=0,
            has_upcoming_show_soon=False,
            has_upcoming_show=False,
            last_successful_collection_at=None,
            supports_upstream_update_timestamp=True,
            skip_existing_setlists=True,
            recent_window_start="2026-03-10",
            recent_window_end="2026-03-16",
            lookahead_end="2026-03-31",
        ),
    )

    success = run_optimized_pipeline.run_band_pipeline(band, force=True)

    assert success is True
    assert [event[0] for event in pipeline_recorder] == [
        "generate_live_predictions",
        "run_backtest",
        "validate_predictions",
        "validate_accuracy",
        "audit_supabase",
    ]


def test_run_band_pipeline_all_scored_skips_accuracy_freshness(
    monkeypatch, pipeline_recorder
):
    band = "goose"
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_run_band_backtest",
        lambda *args, **kwargs: (
            pipeline_recorder.append(("run_backtest", {"args": args, "kwargs": kwargs}))
            or 0
        ),
    )

    success = run_optimized_pipeline.run_band_pipeline(band)

    assert success is True
    assert [event[0] for event in pipeline_recorder][-3:] == [
        "validate_predictions",
        "validate_accuracy_skip_freshness",
        "audit_supabase",
    ]
    assert pipeline_recorder[-1][1]["kwargs"] == {
        "band": band,
        "max_age_hours": 72,
        "skip_accuracy": True,
    }


@pytest.mark.parametrize("band", BANDS)
def test_run_band_pipeline_stops_after_collection_failure(
    band, monkeypatch, preflight_stub
):
    events: list[str] = []

    def fail_collection():
        events.append("collect")
        raise RuntimeError("boom")

    monkeypatch.setattr(
        run_optimized_pipeline, COLLECTION_RUNNERS[band], fail_collection
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_generate_band_predictions",
        lambda *args, **kwargs: events.append("generate"),
    )

    success = run_optimized_pipeline.run_band_pipeline(band)

    assert success is False
    assert events == ["collect"]


@pytest.mark.parametrize("band", BANDS)
def test_run_band_pipeline_stops_after_prediction_failure(
    band, monkeypatch, preflight_stub
):
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(
        run_optimized_pipeline,
        COLLECTION_RUNNERS[band],
        lambda: events.append(("collect", band)),
    )

    def fail_generate(*_args, **kwargs):
        events.append(("generate", kwargs["band"]))
        raise RuntimeError("prediction failed")

    monkeypatch.setattr(
        run_optimized_pipeline,
        "_generate_band_predictions",
        fail_generate,
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_run_band_backtest",
        lambda *args, **kwargs: events.append(("backtest", kwargs["band"])),
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_validate_band_predictions",
        lambda *args, **kwargs: events.append(("validate", "done")),
    )
    monkeypatch.setattr(
        run_optimized_pipeline,
        "_validate_band_accuracy",
        lambda *args, **kwargs: events.append(("validate_accuracy", "done")),
    )

    success = run_optimized_pipeline.run_band_pipeline(band)

    assert success is False
    assert events == [("collect", band), ("generate", band)]
