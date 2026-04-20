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
    monkeypatch.setattr(run_optimized_pipeline, "HAS_BACKFILL", False)
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

    def record(name: str):
        def _inner(*args, **kwargs):
            events.append((name, {"args": args, "kwargs": kwargs}))

        return _inner

    for band, attr_name in COLLECTION_RUNNERS.items():
        monkeypatch.setattr(
            run_optimized_pipeline, attr_name, record(f"{band}:collect")
        )

    monkeypatch.setattr(
        run_optimized_pipeline, "generate_predictions", record("generate_predictions")
    )
    monkeypatch.setattr(run_optimized_pipeline, "run_backtest", record("run_backtest"))
    monkeypatch.setattr(
        run_optimized_pipeline,
        "rebuild_prediction_songs",
        record("rebuild_prediction_songs"),
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

    return events


@pytest.mark.parametrize("band", BANDS)
def test_run_band_pipeline_executes_full_orchestrator_path(band, pipeline_recorder):
    success = run_optimized_pipeline.run_band_pipeline(band)

    assert success is True
    assert [event[0] for event in pipeline_recorder] == [
        f"{band}:collect",
        "generate_predictions",
        "run_backtest",
        "generate_predictions",
        "run_backtest",
        "rebuild_prediction_songs",
        "validate_predictions",
        "validate_accuracy",
    ]

    notebook_prediction = pipeline_recorder[1][1]["kwargs"]
    deal_prediction = pipeline_recorder[3][1]["kwargs"]
    notebook_backtest = pipeline_recorder[2][1]["kwargs"]
    deal_backtest = pipeline_recorder[4][1]["kwargs"]

    assert notebook_prediction == {
        "band": band,
        "model": "notebook",
        "date_str": None,
        "exclusion_window": None,
    }
    assert deal_prediction == {
        "band": band,
        "model": "deal",
        "date_str": None,
        "exclusion_window": None,
    }
    assert notebook_backtest == {
        "band": band,
        "model": "notebook",
        "start": None,
        "end": None,
        "shows": 50,
        "exclusion_window": None,
        "incremental": True,
    }
    assert deal_backtest == {
        "band": band,
        "model": "deal",
        "start": None,
        "end": None,
        "shows": 50,
        "exclusion_window": None,
        "incremental": True,
    }
    assert pipeline_recorder[5][1]["kwargs"] == {
        "band": band,
        "model": None,
        "reference_date_from": "2026-03-10",
        "reference_date_to": "2026-03-31",
    }
    assert pipeline_recorder[6][1]["kwargs"] == {"band": band, "max_age_hours": 72}
    assert pipeline_recorder[7][1]["kwargs"] == {"band": band, "max_age_hours": 72}


@pytest.mark.parametrize("band", BANDS)
def test_run_band_pipeline_skip_accuracy_preserves_predictions_and_validation(
    band, monkeypatch, pipeline_recorder
):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("accuracy step should be skipped")

    monkeypatch.setattr(run_optimized_pipeline, "run_backtest", fail_if_called)

    success = run_optimized_pipeline.run_band_pipeline(band, skip_accuracy=True)

    assert success is True
    assert [event[0] for event in pipeline_recorder] == [
        f"{band}:collect",
        "generate_predictions",
        "generate_predictions",
        "rebuild_prediction_songs",
        "validate_predictions",
    ]


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
        "generate_predictions",
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
        model = kwargs["model"]
        events.append(("generate", model))
        if model == "notebook":
            raise RuntimeError("prediction failed")

    monkeypatch.setattr(run_optimized_pipeline, "generate_predictions", fail_generate)
    monkeypatch.setattr(
        run_optimized_pipeline,
        "run_backtest",
        lambda *args, **kwargs: events.append(("backtest", kwargs["model"])),
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
    assert events == [("collect", band), ("generate", "notebook")]
