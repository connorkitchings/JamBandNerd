from __future__ import annotations

from dataclasses import replace
from datetime import date

from scripts import evaluate_deal_model as module
from src.jambandnerd.models.registry import get_model_definition


class _DealPredictorStub:
    def __init__(self):
        self.trained = 0

    def train(self, model_data):  # noqa: ARG002
        self.trained += 1

    def build_evaluation_report(self, model_data):  # noqa: ARG002
        return {
            "status": "ready",
            "training_summary": {"rows": 100},
            "coefficients": [{"feature": "current_gap", "coefficient": 0.3}],
            "probability_distribution": {"mean": 0.42},
            "calibration_summary": [{"bucket_start": 0.0, "bucket_end": 0.2}],
        }


def test_generate_report_emits_registry_aligned_promotion_gate(monkeypatch):
    shows = [
        {"show_id": "goose-1", "show_date": "2026-03-20"},
        {"show_id": "goose-2", "show_date": "2026-03-21"},
        {"show_id": "goose-3", "show_date": "2026-03-22"},
    ]
    setlists = [
        {"show_id": "goose-1", "song_name": "Song A"},
        {"show_id": "goose-2", "song_name": "Song B"},
        {"show_id": "goose-3", "song_name": "Song C"},
    ]

    monkeypatch.setattr(
        module,
        "fetch_table",
        lambda table: shows if "shows" in table else setlists,
    )
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(module, "resolve_reference_date", lambda *_args, **_kwargs: date(2026, 3, 27))
    monkeypatch.setattr(module, "generate_model_data", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(module, "build_evaluation_predictor", lambda slug, band: _DealPredictorStub())
    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(
            get_model_definition("deal") if slug == "deal" else get_model_definition(slug),
            enabled_for_web=False,
            version="deal_v2",
        )
        if slug == "deal"
        else get_model_definition(slug),
    )
    monkeypatch.setattr(module, "load_legacy_reference", lambda: {"deal": 0.3})
    monkeypatch.setattr(
        module,
        "evaluate_model_window",
        lambda band, model_slug, shows_df, setlists_df, show_rows: {
            "deal": {"hit_rate": 0.4, "avg_matches": 2.0, "precision": 0.4, "recall": 0.4, "f1": 0.4, "shows": 3.0},
            "ckplus": {"hit_rate": 0.35, "avg_matches": 2.0, "precision": 0.35, "recall": 0.35, "f1": 0.35, "shows": 3.0},
            "notebook": {"hit_rate": 0.32, "avg_matches": 2.0, "precision": 0.32, "recall": 0.32, "f1": 0.32, "shows": 3.0},
        }[model_slug],
    )

    report = module.generate_report("goose", 3)

    assert report["status"] == "ready"
    assert set(report["comparison_window"]["metrics"].keys()) == {"deal", "ckplus", "notebook"}
    assert report["promotion_gate"]["model_slug"] == "deal"
    assert report["promotion_gate"]["model_version"] == "deal_v2"
    assert report["promotion_gate"]["enabled_for_web"] is False
    assert report["promotion_gate"]["beats_legacy_deal_by_0_05"] is True
    assert report["promotion_gate"]["matches_or_beats_ckplus"] is True

