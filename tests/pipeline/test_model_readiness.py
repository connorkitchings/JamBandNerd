from __future__ import annotations

from pathlib import Path

from scripts import model_readiness as module


def test_run_model_readiness_full_flow_executes_staged_phases(monkeypatch, tmp_path):
    calls: list[str] = []

    monkeypatch.setattr(
        module,
        "build_model_readiness_report",
        lambda *args, **kwargs: {"ready_for_backend": False},
    )
    monkeypatch.setattr(
        module,
        "_run_compare_phase",
        lambda **kwargs: calls.append("compare") or {"path": "compare.json"},
    )
    monkeypatch.setattr(
        module,
        "_run_snapshot_phase",
        lambda **kwargs: calls.append("snapshot") or {"path": "snapshot.json"},
    )
    monkeypatch.setattr(
        module,
        "_run_backfill_history_phase",
        lambda **kwargs: calls.append("backfill-history") or {"path": "history.json"},
    )
    monkeypatch.setattr(
        module,
        "_run_aggregate_phase",
        lambda **kwargs: calls.append("aggregate") or {"bands": ["goose"]},
    )
    monkeypatch.setattr(
        module,
        "_run_validate_phase",
        lambda **kwargs: calls.append("validate") or {"path": "validate.json"},
    )

    result = module.run_model_readiness(
        model_slug="deal",
        bands=["goose"],
        phase="full-readiness",
        artifact_root=tmp_path,
    )

    assert result["artifact_root"] == str(tmp_path / "deal")
    assert calls == [
        "compare",
        "snapshot",
        "backfill-history",
        "aggregate",
        "validate",
    ]


def test_run_model_readiness_report_only_writes_under_model_artifact_root(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        module,
        "_run_validate_phase",
        lambda **kwargs: {"path": "validate.json"},
    )
    monkeypatch.setattr(
        module,
        "build_model_readiness_report",
        lambda *args, **kwargs: {"ready_for_backend": False},
    )

    result = module.run_model_readiness(
        model_slug="deal",
        bands=["goose"],
        phase="report-only",
        artifact_root=tmp_path,
    )

    assert result["artifact_root"] == str(Path(tmp_path) / "deal")
    assert "initial_report" in result
    assert "validation" in result
