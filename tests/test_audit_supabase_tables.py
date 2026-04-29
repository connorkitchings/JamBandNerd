from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from scripts import audit_supabase_tables as module
from scripts.check_supported_model_freshness import SupportedModelFreshnessResult
from scripts.verify_data_freshness import RecentSetlistCompletenessResult

NOW = datetime.now(timezone.utc)


def _definition(slug: str, version: str):
    return SimpleNamespace(
        slug=slug,
        version=version,
        prediction_table="next_show_prediction_runs",
        default_top_k=50,
    )


PROMOTED_MODELS = (
    _definition("notebook", "notebook_v1"),
    _definition("deal", "deal_v2"),
)


def _readiness_status(
    model_slug: str,
    *,
    overlap_model: str,
    prediction_rows: int = 3,
    latest_reference_date: str = "2026-04-10",
    latest_prediction_top_k: int = 50,
    latest_projection_rows: int = 50,
    historical_runs: int = 50,
    unique_historical_target_dates: int = 50,
    per_show_rows: int = 50,
    replay_overlap: int = 50,
) -> dict[str, object]:
    return {
        "band": "goose",
        "model_slug": model_slug,
        "model_version": "notebook_v1" if model_slug == "notebook" else "deal_v2",
        "required_window": 50,
        "prediction_rows": prediction_rows,
        "projection_rows": 150,
        "latest_reference_date": latest_reference_date,
        "latest_prediction_top_k": latest_prediction_top_k,
        "latest_projection_rows": latest_projection_rows,
        "historical_runs": historical_runs,
        "unique_historical_target_dates": unique_historical_target_dates,
        "per_show_rows": per_show_rows,
        "aggregate_windows": {"50": True},
        "replay_overlap": {overlap_model: replay_overlap},
        "blockers": [],
        "ready": True,
    }


def _prediction_row(
    *,
    top_k: int = 50,
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
        "model_slug": "notebook",
        "model_version": "notebook_v1",
        "reference_date": "2026-04-10",
        "generated_at": timestamp.isoformat() if timestamp else None,
        "top_k": top_k,
        "predictions": value,
    }


def _projection_rows(
    *, count: int = 50, top_song: str = "Song A"
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        rows.append(
            {
                "song_name": top_song if index == 0 else f"Song {index + 1}",
                "rank": index + 1,
                "reference_date": "2026-04-10",
            }
        )
    return rows


def _replay_rows(*, count: int = 50, missing_lineage: bool = False):
    rows = []
    for index in range(count):
        month = (index // 28) + 3
        day = (index % 28) + 1
        rows.append(
            {
                "show_date": f"2026-{month:02d}-{day:02d}",
                "prediction_run_id": (
                    None if missing_lineage and index == 0 else 100 + index
                ),
                "actual_song_count": 12,
            }
        )
    return rows


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
    readiness_overrides: dict[str, dict[str, object]] | None = None,
    latest_rows: dict[str, dict[str, object] | None] | None = None,
    projection_rows: dict[str, list[dict[str, object]]] | None = None,
    replay_rows: dict[str, list[dict[str, object]]] | None = None,
    freshness_result: SupportedModelFreshnessResult | None = None,
    raw_result: RecentSetlistCompletenessResult | None = None,
    stale_projection_dates: dict[str, list[str]] | None = None,
) -> None:
    readiness_overrides = readiness_overrides or {}
    latest_rows = latest_rows or {}
    projection_rows = projection_rows or {}
    replay_rows = replay_rows or {}
    stale_projection_dates = stale_projection_dates or {}
    freshness = freshness_result or _freshness_result()
    recent_raw = raw_result or _raw_result()

    monkeypatch.setattr(
        module, "list_promoted_web_models", lambda: list(PROMOTED_MODELS)
    )
    monkeypatch.setattr(module, "get_supabase_client", lambda: object())

    def _build_report(model_slug: str, *, bands, client):
        base_status = _readiness_status(
            model_slug,
            overlap_model="deal" if model_slug == "notebook" else "notebook",
        )
        base_status.update(readiness_overrides.get(model_slug, {}))
        return {"bands": [base_status]}

    monkeypatch.setattr(module, "build_model_readiness_report", _build_report)

    def _latest_row(client, *, table, band, model_slug, model_version):
        row = latest_rows.get(model_slug)
        if row is None:
            return None
        payload = dict(row)
        payload["model_slug"] = model_slug
        payload["model_version"] = model_version
        return payload

    monkeypatch.setattr(module, "_latest_prediction_row", _latest_row)
    monkeypatch.setattr(
        module,
        "fetch_prediction_songs_for_date",
        lambda *, band, model_slug, reference_date, table_name=None: projection_rows.get(
            model_slug, _projection_rows()
        ),
    )
    monkeypatch.setattr(
        module,
        "_recent_replay_eligible_rows",
        lambda client, *, table, band, model_version, limit: replay_rows.get(
            model_version, _replay_rows()
        ),
    )
    monkeypatch.setattr(
        module,
        "list_stale_projection_reference_dates",
        lambda **kwargs: stale_projection_dates.get(kwargs["model_slug"], []),
    )
    monkeypatch.setattr(
        module,
        "audit_supported_model_freshness",
        lambda **kwargs: freshness,
    )
    monkeypatch.setattr(
        module,
        "audit_recent_setlist_completeness",
        lambda band, *, client, emit_text: recent_raw,
    )


def test_run_supabase_audit_happy_path(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "ok"
    assert report.promoted_models == ("notebook", "deal")
    assert report.bands[0].models[0].latest_projection_rows == 50


def test_run_supabase_audit_fails_when_canonical_prediction_missing(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": None,
        },
        readiness_overrides={"deal": {"prediction_rows": 0}},
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "failed"
    assert "goose:deal:canonical_predictions_missing" in report.blockers


def test_run_supabase_audit_fails_on_invalid_latest_json(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(predictions="{bad json"),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={"deal": _projection_rows(top_song="Song B")},
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "failed"
    assert "goose:notebook:canonical_predictions_invalid_json" in report.blockers


def test_run_supabase_audit_allows_consistent_lower_top_k(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(top_k=49),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(count=49),
            "deal": _projection_rows(top_song="Song B"),
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert "goose:notebook:canonical_predictions_top_k_mismatch" not in report.blockers
    assert report.state == "ok"


def test_run_supabase_audit_fails_on_top_k_payload_mismatch(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(
                top_k=25,
                predictions=json.dumps([{"song_name": "Song A"}] * 50),
            ),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(count=25),
            "deal": _projection_rows(top_song="Song B"),
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert "goose:notebook:canonical_predictions_top_k_mismatch" in report.blockers


def test_run_supabase_audit_fails_on_projection_row_count_mismatch(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(count=49),
            "deal": _projection_rows(top_song="Song B"),
        },
        readiness_overrides={"notebook": {"latest_projection_rows": 49}},
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert "goose:notebook:prediction_projection_count_mismatch" in report.blockers


def test_run_supabase_audit_warns_when_historical_runs_below_window_intact_lineage(
    monkeypatch,
):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        readiness_overrides={
            "notebook": {"historical_runs": 49, "unique_historical_target_dates": 49}
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "warning"
    assert "goose:notebook:historical_run_rows_below_window" in report.warnings
    assert "goose:notebook:historical_run_rows_below_window" not in report.blockers
    assert (
        "goose:notebook:historical_unique_target_dates_below_window" in report.warnings
    )


def test_run_supabase_audit_warns_when_accuracy_rows_below_window_intact_lineage(
    monkeypatch,
):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        readiness_overrides={"notebook": {"per_show_rows": 49}},
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "warning"
    assert "goose:notebook:per_show_accuracy_rows_below_window" in report.warnings
    assert "goose:notebook:per_show_accuracy_rows_below_window" not in report.blockers


def test_run_supabase_audit_warns_when_replay_overlap_below_window_intact_lineage(
    monkeypatch,
):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        readiness_overrides={
            "notebook": {"replay_overlap": {"deal": 49}},
            "deal": {"replay_overlap": {"notebook": 49}},
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "warning"
    assert "goose:notebook:replay_overlap_below_window:deal" in report.warnings
    assert "goose:notebook:replay_overlap_below_window:deal" not in report.blockers
    assert "goose:deal:replay_overlap_below_window:notebook" in report.warnings


def test_run_supabase_audit_fails_when_replay_lineage_missing(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        replay_rows={"notebook_v1": _replay_rows(missing_lineage=True)},
    )

    report = module.run_supabase_audit(bands=["goose"])

    notebook_result = report.bands[0].models[0]
    assert "replay_lineage_missing_prediction_run_id" in notebook_result.blockers
    assert notebook_result.replay_lineage_missing_dates == ("2026-03-01",)


def test_run_supabase_audit_treats_stale_accuracy_as_warning_when_skipped(
    monkeypatch, capsys
):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        freshness_result=_freshness_result(
            state="warning",
            stale_accuracy_models=("notebook",),
        ),
    )

    report = module.run_supabase_audit(
        bands=["goose"],
        skip_accuracy=True,
    )

    assert report.state == "warning"
    assert "goose:notebook:supported_accuracy_freshness_warning" in report.warnings
    assert "goose:notebook:supported_accuracy_freshness_stale" not in report.blockers

    module._print_report(report)
    captured = capsys.readouterr().out
    assert "expected immutable freshness drift" in captured


def test_run_supabase_audit_treats_accuracy_windows_as_warnings_when_skipped(
    monkeypatch,
):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        readiness_overrides={
            "notebook": {
                "historical_runs": 0,
                "unique_historical_target_dates": 0,
                "per_show_rows": 0,
                "replay_overlap": {"deal": 0},
            },
            "deal": {
                "historical_runs": 0,
                "unique_historical_target_dates": 0,
                "per_show_rows": 0,
                "replay_overlap": {"notebook": 0},
            },
        },
        replay_rows={
            "notebook_v1": [],
            "deal_v2": [],
        },
    )

    report = module.run_supabase_audit(
        bands=["goose"],
        skip_accuracy=True,
    )

    assert report.state == "warning"
    assert not report.blockers
    assert "goose:notebook:historical_run_rows_below_window" in report.warnings
    assert "goose:notebook:per_show_accuracy_rows_below_window" in report.warnings
    assert "goose:notebook:replay_eligible_rows_below_window" in report.warnings
    assert "goose:notebook:replay_overlap_below_window:deal" in report.warnings


def test_run_supabase_audit_default_scope_excludes_non_promoted_models(monkeypatch):
    calls: list[str] = []
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
    )
    monkeypatch.setattr(module, "get_repo_supported_bands", lambda: ["goose"])

    original_build = module.build_model_readiness_report

    def _tracking_build(model_slug: str, *, bands, client):
        calls.append(model_slug)
        return original_build(model_slug, bands=bands, client=client)

    monkeypatch.setattr(module, "build_model_readiness_report", _tracking_build)

    report = module.run_supabase_audit()

    assert report.promoted_models == ("notebook", "deal")
    assert calls == ["notebook", "deal"]
    assert "ckplus" not in report.promoted_models


def test_run_supabase_audit_warns_on_recent_missing_setlists(monkeypatch):
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        raw_result=_raw_result(missing_show_count=2),
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "warning"
    assert "goose:recent_completed_shows_missing_setlists" in report.warnings


def test_audit_warns_below_window_with_intact_lineage(monkeypatch):
    """48/50 rows with no broken links → warnings only, workflow passes."""
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        readiness_overrides={
            "notebook": {
                "historical_runs": 48,
                "unique_historical_target_dates": 48,
                "per_show_rows": 48,
                "replay_overlap": {"deal": 48},
            },
            "deal": {
                "historical_runs": 48,
                "unique_historical_target_dates": 48,
                "per_show_rows": 48,
                "replay_overlap": {"notebook": 48},
            },
        },
        replay_rows={
            "notebook_v1": _replay_rows(count=48),
            "deal_v2": _replay_rows(count=48),
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "warning"
    assert not report.blockers
    assert "goose:notebook:historical_run_rows_below_window" in report.warnings
    assert "goose:notebook:per_show_accuracy_rows_below_window" in report.warnings
    assert "goose:notebook:replay_eligible_rows_below_window" in report.warnings
    assert "goose:notebook:replay_overlap_below_window:deal" in report.warnings
    assert "goose:deal:replay_overlap_below_window:notebook" in report.warnings


def test_audit_blocks_below_window_with_broken_lineage(monkeypatch):
    """48/50 rows where 1 has a missing prediction_run_id → blockers."""
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        readiness_overrides={
            "notebook": {
                "historical_runs": 48,
                "unique_historical_target_dates": 48,
                "per_show_rows": 48,
                "replay_overlap": {"deal": 48},
            },
        },
        replay_rows={
            "notebook_v1": _replay_rows(count=48, missing_lineage=True),
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "failed"
    assert "goose:notebook:replay_lineage_missing_prediction_run_id" in report.blockers
    assert "goose:notebook:historical_run_rows_below_window" in report.blockers
    assert "goose:notebook:replay_eligible_rows_below_window" in report.blockers


def test_audit_blocks_empty_replay_corpus(monkeypatch):
    """0 replay rows is treated as broken corpus → blockers even with intact readiness counts."""
    _install_audit_stubs(
        monkeypatch,
        latest_rows={
            "notebook": _prediction_row(),
            "deal": _prediction_row(song_name="Song B"),
        },
        projection_rows={
            "notebook": _projection_rows(),
            "deal": _projection_rows(top_song="Song B"),
        },
        replay_rows={
            "notebook_v1": [],
            "deal_v2": [],
        },
    )

    report = module.run_supabase_audit(bands=["goose"])

    assert report.state == "failed"
    assert "goose:notebook:replay_eligible_rows_below_window" in report.blockers
    assert "goose:deal:replay_eligible_rows_below_window" in report.blockers
