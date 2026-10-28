from __future__ import annotations

from datetime import date

import pytest

from scripts import generate_live_predictions as module


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
        module, "build_band_predictor", lambda band, **kwargs: _PredictorStub()
    )
    monkeypatch.setattr(
        module,
        "get_band_serializer",
        lambda band: (
            lambda preds: [
                {"rank": index + 1, "song_name": pred.song_name}
                for index, pred in enumerate(preds)
            ]
        ),
    )
    monkeypatch.setattr(
        module,
        "get_band_metadata",
        lambda band: type(
            "Metadata", (), {"model_version": "goose_baseline_v1", "default_top_k": 2}
        )(),
    )
    monkeypatch.setattr(
        module,
        "upsert_setlist_prediction_run",
        lambda **kwargs: pytest.fail("dry run should not upsert live run"),
    )
    monkeypatch.setattr(
        module,
        "replace_setlist_prediction_projection",
        lambda **kwargs: pytest.fail("dry run should not replace projection"),
    )

    result = module.generate_live_predictions(
        band="goose",
        today=date(2026, 4, 24),
        dry_run=True,
    )

    assert result is True
    output = capsys.readouterr().out
    assert "Dry run" in output
    assert "target_show_key=future-show" in output
    assert "top_k=2" in output
    assert "top_song=Song A" in output


def test_generate_live_predictions_holds_off_when_recent_completed_show_missing_setlist(
    monkeypatch, capsys
):
    rows_by_table = {
        "wsp_shows_raw": [
            {
                "show_id": "22488",
                "show_date": "2026-10-23",
                "venue_name": "The Riverside Theater",
                "city": "Milwaukee",
                "state": "WI",
            },
            {
                "show_id": "22489",
                "show_date": "2026-10-24",
                "venue_name": "The Riverside Theater",
                "city": "Milwaukee",
                "state": "WI",
            },
        ],
        "wsp_setlists_raw": [
            {"show_id": "22400", "song_name": "Chilly Water"},
            {"show_id": "22400", "song_name": "Porch Song"},
            {"show_id": "22400", "song_name": "Tall Boy"},
        ],
    }

    monkeypatch.setattr(module, "fetch_table", lambda table: rows_by_table[table])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        module,
        "get_band_metadata",
        lambda band: type(
            "Metadata", (), {"model_version": "wsp_deal_v2", "default_top_k": 50}
        )(),
    )
    monkeypatch.setattr(module, "get_band_serializer", lambda band: lambda preds: preds)
    monkeypatch.setattr(
        module,
        "generate_model_data",
        lambda *a, **kw: pytest.fail("should hold off before generate_model_data"),
    )

    result = module.generate_live_predictions(
        band="wsp",
        today=date(2026, 10, 24),
        dry_run=True,
    )

    assert result is False
    output = capsys.readouterr().out
    assert "Holding off on live prediction board generation" in output
    assert "2026-10-23 (Milwaukee, WI)" in output

    with pytest.raises(
        RuntimeError, match="Holding off on live prediction board generation"
    ):
        module.generate_live_predictions(
            band="wsp",
            today=date(2026, 10, 24),
            require_output=True,
        )


def test_generate_live_predictions_allows_override_when_recent_setlist_missing(
    monkeypatch,
):
    rows_by_table = {
        "wsp_shows_raw": [
            {"show_id": "22488", "show_date": "2026-10-23"},
            {"show_id": "22489", "show_date": "2026-10-24"},
        ],
        "wsp_setlists_raw": [
            {"show_id": "22400", "song_name": "Chilly Water"},
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
        module, "build_band_predictor", lambda band, **kwargs: _PredictorStub()
    )
    monkeypatch.setattr(
        module,
        "get_band_serializer",
        lambda band: (
            lambda preds: [
                {"rank": index + 1, "song_name": pred.song_name}
                for index, pred in enumerate(preds)
            ]
        ),
    )
    monkeypatch.setattr(
        module,
        "get_band_metadata",
        lambda band: type(
            "Metadata", (), {"model_version": "wsp_deal_v2", "default_top_k": 2}
        )(),
    )

    result = module.generate_live_predictions(
        band="wsp",
        today=date(2026, 10, 24),
        dry_run=True,
        allow_missing_recent_setlists=True,
    )
    assert result is True


def _stub_pipeline(monkeypatch, rows_by_table):
    monkeypatch.setattr(module, "fetch_table", lambda table: rows_by_table[table])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(module, "generate_model_data", lambda *a, **kw: object())
    monkeypatch.setattr(
        module, "build_band_predictor", lambda band, **kwargs: _PredictorStub()
    )
    monkeypatch.setattr(
        module,
        "get_band_serializer",
        lambda band: (
            lambda preds: [
                {"rank": i + 1, "song_name": p.song_name} for i, p in enumerate(preds)
            ]
        ),
    )
    monkeypatch.setattr(
        module,
        "get_band_metadata",
        lambda band: type(
            "Metadata", (), {"model_version": "goose_v2", "default_top_k": 2}
        )(),
    )


_GOOSE_ROWS = {
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


def test_generate_live_predictions_prunes_other_versions_after_write(monkeypatch):
    _stub_pipeline(monkeypatch, _GOOSE_ROWS)
    calls: list[str] = []
    monkeypatch.setattr(
        module, "upsert_setlist_prediction_run", lambda **kw: calls.append("run") or 7
    )
    monkeypatch.setattr(
        module,
        "replace_setlist_prediction_projection",
        lambda **kw: calls.append("projection"),
    )
    monkeypatch.setattr(
        module,
        "delete_other_model_version_boards",
        lambda **kw: calls.append(f"prune:{kw['band']}:{kw['model_version']}") or {},
    )

    result = module.generate_live_predictions(band="goose", today=date(2026, 4, 24))

    assert result is True
    assert calls == ["run", "projection", "prune:goose:goose_v2"]


def test_generate_live_predictions_dry_run_does_not_prune(monkeypatch):
    _stub_pipeline(monkeypatch, _GOOSE_ROWS)
    monkeypatch.setattr(
        module,
        "delete_other_model_version_boards",
        lambda **kw: pytest.fail("dry run must not prune"),
    )

    assert module.generate_live_predictions(
        band="goose", today=date(2026, 4, 24), dry_run=True
    )


def test_generate_live_predictions_hold_off_does_not_prune(monkeypatch):
    rows = {
        "wsp_shows_raw": [
            {"show_id": "1", "show_date": "2026-10-23"},
            {"show_id": "2", "show_date": "2026-10-24"},
        ],
        "wsp_setlists_raw": [{"show_id": "0", "song_name": "X"}],
    }
    _stub_pipeline(monkeypatch, rows)
    monkeypatch.setattr(
        module,
        "delete_other_model_version_boards",
        lambda **kw: pytest.fail("hold-off must not prune"),
    )

    assert (
        module.generate_live_predictions(band="wsp", today=date(2026, 10, 24)) is False
    )
