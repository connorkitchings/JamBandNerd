from __future__ import annotations

import json

from scripts import recover_deal_last50_local as module
from src.jambandnerd.models.registry import get_model_definition


def _scored_run(show_id: str, target_show_date: str, reference_date: str) -> dict[str, object]:
    return {
        "band": "wsp",
        "model_slug": "deal",
        "model_version": "deal_v2",
        "show_id": show_id,
        "target_show_date": target_show_date,
        "reference_date": reference_date,
        "actual_songs": ["Song A", "Song B", "Song C"],
        "actual_song_count": 3,
        "predictions": [{"rank": 1, "song_name": "Song A"}],
        "prediction_count": 1,
        "generated_at": "2026-04-12T12:00:00+00:00",
        "metrics": {
            "k10": {"hit": 1, "matches": 1, "precision": 0.1, "recall": 0.33, "f1": 0.15},
            "k25": {"hit": 1, "matches": 1, "precision": 0.04, "recall": 0.33, "f1": 0.08},
            "k50": {"hit": 1, "matches": 1, "precision": 0.02, "recall": 0.33, "f1": 0.04},
        },
    }


def test_upload_band_bundle_writes_predictions_then_persists_runs(monkeypatch):
    captured: dict[str, object] = {}
    bundle = {
        "band": "wsp",
        "model_slug": "deal",
        "model_version": "deal_v2",
        "scored_runs": [
            _scored_run("wsp-show-1", "2024-01-20", "2024-01-19"),
            _scored_run("wsp-show-2", "2024-01-20", "2024-01-19"),
        ],
    }

    monkeypatch.setattr(
        module,
        "upsert_dataframe",
        lambda table_name, df, conflict_columns: captured.update(
            {
                "table_name": table_name,
                "rows": df.to_dict(orient="records"),
                "conflict_columns": list(conflict_columns),
            }
        ),
    )
    monkeypatch.setattr(
        module,
        "persist_scored_run_records",
        lambda scored_runs: captured.update({"persisted_runs": list(scored_runs)}),
    )
    monkeypatch.setattr(
        module,
        "save_aggregate_accuracy",
        lambda band, model, shows: captured.update(
            {"aggregate": {"band": band, "model": model, "shows": shows}}
        ),
    )

    module.upload_band_bundle(bundle)

    assert captured["table_name"] == get_model_definition("deal").prediction_table
    assert captured["conflict_columns"] == ["band", "reference_date", "model_version"]
    assert len(captured["rows"]) == 1
    assert captured["rows"][0]["reference_date"] == "2024-01-19"
    assert len(captured["persisted_runs"]) == 2
    assert captured["aggregate"] == {"band": "wsp", "model": "deal", "shows": 50}


def test_recovery_skips_complete_band(monkeypatch, tmp_path):
    recovery_root = tmp_path / "recovery"
    snapshots_root = recovery_root / "snapshots"
    snapshots_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": "2026-04-12T12:00:00+00:00",
        "bands": {
            "phish": {
                "complete": True,
            }
        },
    }
    (recovery_root / module.RECOVERY_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2)
    )

    monkeypatch.setattr(
        module,
        "build_band_bundle",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not rebuild")),
    )
    monkeypatch.setattr(
        module,
        "upload_band_bundle",
        lambda bundle: (_ for _ in ()).throw(AssertionError("should not upload")),
    )

    module.recover_deal_last50_local(
        bands=["phish"],
        recovery_root=recovery_root,
        refresh_snapshots=False,
        rebuild_bundles=False,
        dry_run=False,
        cleanup=False,
    )
