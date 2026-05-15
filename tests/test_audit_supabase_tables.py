from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from scripts import audit_supabase_tables as module
from scripts.check_supported_model_freshness import SupportedModelFreshnessResult
from scripts.verify_data_freshness import RecentSetlistCompletenessResult

NOW = datetime.now(timezone.utc)
MODEL_VERSION = "goose_phase_b_v1"


def _prediction_row(
    *,
    top_k: int = 25,
    song_name: str = "Song A",
    generated_at: datetime | None = None,
    predictions: object | None = None,
) -> dict[str, object]:
    value = predictions
    if value is None:
        value = json.dumps([{"song_name": song_name}] * top_k)
    timestamp = generated_at or NOW
    return {
        "band": "goose",
        "model_version": MODEL_VERSION,
        "target_show_key": "goose-show-1",
        "target_show_date": "2026-04-10",
        "reference_date": "2026-04-09",
        "generated_at": timestamp.isoformat() if timestamp else None,
        "top_k": top_k,
        "predictions": value,
    }


def _projection_rows(
    *, count: int = 25, top_song: str = "Song A"
) -> list[dict[str, object]]:
    return [
        {
            "target_show_key": "goose-show-1",
            "song_name": top_song if index == 0 else f"Song {index + 1}",
            "rank": index + 1,
        }
        for index in range(count)
    ]


def _replay_rows(*, count: int = 100, missing_lineage: bool = False):
    return [
        {
            "show_date": f"2026-03-{index + 1:02d}",
            "prediction_run_id": (
                None if missing_lineage and index == 0 else 100 + index
            ),
            "actual_song_count": 12,
            "evaluated_at": NOW.isoformat(),
        }
        for index in range(count)
    ]


def _freshness_result(
    *,
    state: str = "fresh",
    stale_prediction_models: tuple[str, ...] = (),
    stale_accuracy_models: tuple[str, ...] = (),
) -> SupportedModelFreshnessResult:
    return SupportedModelFreshnessResult(
        band="goose",
        max_age_hours=72,
        skip_accuracy=state == "warning",
        freshness_state=state,
        stale_prediction_models=stale_prediction_models,
        stale_accuracy_models=stale_accuracy_models,
        max_prediction_age_hours=4.0,
        max_accuracy_age_hours=4.0,
        freshness_reason="stubbed",
    )


def _raw_result(*, missing_show_count: int = 0) -> RecentSetlistCompletenessResult:
    return RecentSetlistCompletenessResult(
        band="goose",
        cutoff="2026-04-08",
        end_date="2026-04-14",
        recent_show_count=3,
        missing_show_count=missing_show_count,
        missing_show_ids=tuple(f"show-{index}" for index in range(missing_show_count)),
    )


def _install_audit_stubs(
    monkeypatch,
    *,
    latest_row: dict[str, object] | None = None,
    projection_rows: list[dict[str, object]] | None = None,
    replay_rows: list[dict[str, object]] | None = None,
    count_overrides: dict[str, int] | None = None,
    freshness_result: SupportedModelFreshnessResult | None = None,
    raw_result: RecentSetlistCompletenessResult | None = None,
    has_upcoming_show: bool = True,
) -> None:
    counts = {
        "setlist_predictions": 1,
        "setlist_results": 100,
        "setlist_accuracy": 100,
    }
    counts.update(count_overrides or {})

    monkeypatch.setattr(module, "get_supabase_client", lambda: object())
    monkeypatch.setattr(module, "list_active_bands", lambda: ["goose"])
    monkeypatch.setattr(
        module,
        "get_band_metadata",
        lambda band: SimpleNamespace(model_version=MODEL_VERSION, default_top_k=25),
    )
    monkeypatch.setattr(
        module,
        "audit_supported_model_freshness",
        lambda **kwargs: freshness_result or _freshness_result(),
    )
    monkeypatch.setattr(
        module,
        "audit_recent_setlist_completeness",
        lambda band, *, client, emit_text: raw_result or _raw_result(),
    )
    monkeypatch.setattr(
        module,
        "_count_rows",
        lambda client, table, *, filters: counts.get(table, 0),
    )
    monkeypatch.setattr(
        module,
        "_latest_prediction_row",
        lambda client, *, table, band, model_version: latest_row,
    )
    monkeypatch.setattr(
        module,
        "_latest_projection_rows",
        lambda client, *, band, model_version, target_show_key: (
            projection_rows if projection_rows is not None else _projection_rows()
        ),
    )
    monkeypatch.setattr(
        module,
        "_recent_replay_eligible_rows",
        lambda client, *, table, band, model_version, limit: (
            replay_rows if replay_rows is not None else _replay_rows(count=limit)
        ),
    )
    monkeypatch.setattr(
        module,
        "_has_upcoming_show",
        lambda client, *, band: has_upcoming_show,
    )


def test_run_supabase_audit_happy_path(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(),
        projection_rows=_projection_rows(),
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "ok"
    assert report.promoted_models == (MODEL_VERSION,)
    assert report.bands[0].models[0].model_version == MODEL_VERSION
    assert report.bands[0].models[0].latest_projection_rows == 25


def test_run_supabase_audit_fails_when_canonical_prediction_missing(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=None,
        count_overrides={"setlist_predictions": 0},
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "failed"
    assert f"goose:{MODEL_VERSION}:canonical_predictions_missing" in report.blockers


def test_run_supabase_audit_allows_missing_prediction_without_upcoming_show(
    monkeypatch,
):
    _install_audit_stubs(
        monkeypatch,
        latest_row=None,
        count_overrides={"setlist_predictions": 0},
        has_upcoming_show=False,
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert "canonical_predictions_missing" not in " ".join(report.blockers)


def test_run_supabase_audit_fails_on_invalid_latest_json(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(predictions="{bad json"),
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert (
        f"goose:{MODEL_VERSION}:canonical_predictions_invalid_json" in report.blockers
    )


def test_run_supabase_audit_fails_on_top_k_payload_mismatch(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(
            top_k=10,
            predictions=json.dumps([{"song_name": "Song A"}] * 25),
        ),
        projection_rows=_projection_rows(count=10),
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert (
        f"goose:{MODEL_VERSION}:canonical_predictions_top_k_mismatch" in report.blockers
    )


def test_run_supabase_audit_fails_on_projection_row_count_mismatch(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(),
        projection_rows=_projection_rows(count=24),
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert (
        f"goose:{MODEL_VERSION}:prediction_projection_count_mismatch" in report.blockers
    )


def test_run_supabase_audit_fails_when_history_or_accuracy_below_window(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(),
        count_overrides={"setlist_results": 99, "setlist_accuracy": 98},
        replay_rows=_replay_rows(count=98),
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert f"goose:{MODEL_VERSION}:historical_run_rows_below_window" in report.blockers
    assert (
        f"goose:{MODEL_VERSION}:per_show_accuracy_rows_below_window" in report.blockers
    )
    assert f"goose:{MODEL_VERSION}:replay_eligible_rows_below_window" in report.blockers


def test_run_supabase_audit_fails_when_replay_lineage_missing(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(),
        replay_rows=_replay_rows(missing_lineage=True),
    )

    report = module.run_supabase_audit(bands=["goose"])

    model_result = report.bands[0].models[0]
    assert "replay_lineage_missing_prediction_run_id" in model_result.blockers
    assert model_result.replay_lineage_missing_dates == ("2026-03-01",)


def test_run_supabase_audit_treats_stale_accuracy_as_warning_when_skipped(
    monkeypatch, capsys
):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(),
        freshness_result=_freshness_result(
            state="warning",
            stale_accuracy_models=(MODEL_VERSION,),
        ),
    )

    report = module.run_supabase_audit(
        bands=["goose"],
        skip_accuracy=True,
    )

    assert report.state == "warning"
    assert (
        f"goose:{MODEL_VERSION}:supported_accuracy_freshness_warning" in report.warnings
    )
    assert (
        f"goose:{MODEL_VERSION}:supported_accuracy_freshness_stale"
        not in report.blockers
    )

    module._print_report(report)
    captured = capsys.readouterr().out
    assert "expected immutable freshness drift" in captured


def test_run_supabase_audit_default_scope_uses_active_bands(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(),
    )
    monkeypatch.setattr(module, "list_active_bands", lambda: ["goose"])

    report = module.run_supabase_audit()

    assert report.promoted_models == (MODEL_VERSION,)
    assert report.bands[0].band == "goose"


def test_run_supabase_audit_warns_on_recent_missing_setlists(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_row=_prediction_row(),
        raw_result=_raw_result(missing_show_count=2),
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "warning"
    assert "goose:recent_completed_shows_missing_setlists" in report.warnings
