from __future__ import annotations

import pandas as pd

from scripts import run_backtest as run_backtest_module


class _Prediction:
    def __init__(self, song_name: str):
        self.song_name = song_name
        self.plays_past_year = 1
        self.current_gap = 5
        self.last_played_date = "2023-12-31"


class _NotebookPredictorStub:
    def predict(self, model_data, top_k=50):  # noqa: ARG002
        return (
            [_Prediction("Song A"), _Prediction("Song B"), _Prediction("Song C")],
            {},
        )


def test_run_backtest_persists_string_show_ids(monkeypatch):
    shows_rows = [
        {"show_id": "goose-show-1", "show_date": "2024-01-01"},
        {"show_id": "goose-show-2", "show_date": "2024-01-10"},
        {"show_id": "goose-show-3", "show_date": "2024-01-20"},
    ]
    setlist_rows = [
        {"show_id": "goose-show-1", "song_name": "Song A"},
        {"show_id": "goose-show-1", "song_name": "Song B"},
        {"show_id": "goose-show-1", "song_name": "Song C"},
        {"show_id": "goose-show-2", "song_name": "Song D"},
        {"show_id": "goose-show-2", "song_name": "Song E"},
        {"show_id": "goose-show-2", "song_name": "Song F"},
        {"show_id": "goose-show-3", "song_name": "Song A"},
        {"show_id": "goose-show-3", "song_name": "Song G"},
        {"show_id": "goose-show-3", "song_name": "Song H"},
    ]

    def fetch_table(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
        if table_name == "goose_shows_raw":
            return shows_rows
        if table_name == "goose_setlists_raw":
            return setlist_rows
        raise AssertionError(f"Unexpected table: {table_name}")

    captured: dict[str, pd.DataFrame] = {}
    historical_runs: list[dict[str, object]] = []

    def capture_upsert(
        table_name: str, df: pd.DataFrame, conflict_columns
    ):  # noqa: ANN001
        captured["table_name"] = table_name
        captured["df"] = df.copy()
        captured["conflict_columns"] = list(conflict_columns)

    def capture_historical_run(**kwargs):  # noqa: ANN003
        historical_runs.append(dict(kwargs))
        return 987

    monkeypatch.setattr(run_backtest_module, "fetch_table", fetch_table)
    monkeypatch.setattr(
        run_backtest_module, "generate_model_data", lambda *args, **kwargs: object()
    )
    monkeypatch.setattr(
        run_backtest_module, "NotebookPredictor", _NotebookPredictorStub
    )
    monkeypatch.setattr(run_backtest_module, "upsert_dataframe", capture_upsert)
    monkeypatch.setattr(
        run_backtest_module,
        "upsert_historical_prediction_run",
        capture_historical_run,
    )

    run_backtest_module.run_backtest(
        band="goose",
        model="notebook",
        start=None,
        end=None,
        shows=1,
        exclusion_window=3,
    )

    assert captured["table_name"] == "accuracy_per_show"
    assert captured["conflict_columns"] == ["band", "model_version", "show_id"]
    assert captured["df"]["show_id"].tolist() == ["goose-show-3"]
    assert captured["df"]["show_id"].map(type).eq(str).all()
    assert captured["df"]["prediction_run_id"].tolist() == [987]
    assert len(historical_runs) == 1
    assert historical_runs[0]["band"] == "goose"
    assert historical_runs[0]["model_slug"] == "notebook"
    assert historical_runs[0]["model_version"] == "notebook_v1"
    assert historical_runs[0]["reference_date"] == "2024-01-19"
    assert historical_runs[0]["target_show_id"] == "goose-show-3"
    assert historical_runs[0]["target_show_date"] == "2024-01-20"
    assert historical_runs[0]["actual_songs"] == ["Song A", "Song G", "Song H"]
    assert historical_runs[0]["table_name"] == "historical_prediction_runs"
    assert historical_runs[0]["predictions"] == [
        {
            "rank": 1,
            "song_name": "Song A",
            "plays_past_year": 1,
            "current_gap": 5,
            "last_played_date": "2023-12-31",
        },
        {
            "rank": 2,
            "song_name": "Song B",
            "plays_past_year": 1,
            "current_gap": 5,
            "last_played_date": "2023-12-31",
        },
        {
            "rank": 3,
            "song_name": "Song C",
            "plays_past_year": 1,
            "current_gap": 5,
            "last_played_date": "2023-12-31",
        },
    ]
