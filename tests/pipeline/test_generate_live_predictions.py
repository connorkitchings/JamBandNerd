from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from scripts import generate_live_predictions as module
from src.jambandnerd.models.registry import get_model_definition


class _Prediction:
    def __init__(self, song_name: str):
        self.song_name = song_name


class _PredictorStub:
    def predict(self, model_data, top_k=50):  # noqa: ARG002
        return ([_Prediction("Song A"), _Prediction("Song B")], {})


def test_generate_live_predictions_dry_run_skips_writes(monkeypatch, capsys):
    rows_by_table = {
        "goose_shows_raw": [
            {"show_id": "past-show", "show_date": "2026-04-20"},
            {"show_id": "future-show", "show_date": "2026-04-25"},
        ],
        "goose_setlists_raw": [
            {"show_id": "past-show", "song_name": "Song A"},
            {"show_id": "past-show", "song_name": "Song B"},
            {"show_id": "past-show", "song_name": "Song C"},
        ],
    }

    monkeypatch.setattr(module, "fetch_table", lambda table: rows_by_table[table])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(module, "generate_model_data", lambda *a, **kw: object())
    monkeypatch.setattr(
        module, "build_predictor", lambda slug, *, band, **kwargs: _PredictorStub()
    )
    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(get_model_definition("notebook"), default_top_k=2),
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, preds: [
            {"rank": index + 1, "song_name": pred.song_name}
            for index, pred in enumerate(preds)
        ],
    )
    monkeypatch.setattr(
        module,
        "upsert_next_show_prediction_run",
        lambda **kwargs: pytest.fail("dry run should not upsert live run"),
    )
    monkeypatch.setattr(
        module,
        "replace_next_show_prediction_projection",
        lambda **kwargs: pytest.fail("dry run should not replace projection"),
    )

    result = module.generate_live_predictions(
        band="goose",
        model="notebook",
        today=date(2026, 4, 24),
        dry_run=True,
    )

    assert result is True
    output = capsys.readouterr().out
    assert "Dry run" in output
    assert "target_show_key=future-show" in output
    assert "top_k=2" in output
    assert "top_song=Song A" in output
