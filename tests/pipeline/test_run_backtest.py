from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from scripts import run_backtest as run_backtest_module
from src.jambandnerd.models.registry import get_model_definition


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


class _TrainingPredictorStub:
    def train(self, model_data):  # noqa: ARG002
        return None

    def predict(self, model_data, top_k=50):  # noqa: ARG002
        return [_Prediction("Song A"), _Prediction("Song B")]


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
    completed_runs: list[dict[str, object]] = []

    def capture_upsert(
        table_name: str, df: pd.DataFrame, conflict_columns
    ):  # noqa: ANN001
        captured["table_name"] = table_name
        captured["df"] = df.copy()
        captured["conflict_columns"] = list(conflict_columns)

    def capture_completed_run(**kwargs):  # noqa: ANN003
        completed_runs.append(dict(kwargs))
        return 987

    monkeypatch.setattr(run_backtest_module, "fetch_table", fetch_table)
    monkeypatch.setattr(
        run_backtest_module, "generate_model_data", lambda *args, **kwargs: object()
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_predictor",
        lambda slug, *, band: _NotebookPredictorStub(),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_model_definition",
        lambda slug: replace(get_model_definition(slug), default_top_k=50),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "serialize_model_predictions",
        lambda slug, preds: [
            {
                "rank": index + 1,
                "song_name": prediction.song_name,
                "plays_past_year": prediction.plays_past_year,
                "current_gap": prediction.current_gap,
                "last_played_date": prediction.last_played_date,
            }
            for index, prediction in enumerate(preds)
        ],
    )
    monkeypatch.setattr(run_backtest_module, "upsert_dataframe", capture_upsert)
    monkeypatch.setattr(
        run_backtest_module,
        "upsert_completed_show_prediction_run",
        capture_completed_run,
    )
    monkeypatch.setattr(
        run_backtest_module, "fetch_scored_show_ids", lambda *a, **kw: set()
    )
    monkeypatch.setattr(
        run_backtest_module, "prune_completed_show_corpus", lambda **kwargs: None
    )

    run_backtest_module.run_backtest(
        band="goose",
        model="notebook",
        start=None,
        end=None,
        shows=1,
        exclusion_window=3,
    )

    assert captured["table_name"] == "completed_show_accuracy"
    assert captured["conflict_columns"] == [
        "band",
        "model_slug",
        "model_version",
        "target_show_key",
    ]
    assert captured["df"]["show_id"].tolist() == ["goose-show-3"]
    assert captured["df"]["show_id"].map(type).eq(str).all()
    assert captured["df"]["prediction_run_id"].tolist() == [987]
    assert len(completed_runs) == 1
    assert completed_runs[0]["band"] == "goose"
    assert completed_runs[0]["model_slug"] == "notebook"
    assert completed_runs[0]["model_version"] == "notebook_v1"
    assert completed_runs[0]["reference_date"] == "2024-01-19"
    assert completed_runs[0]["target_show_key"] == "goose-show-3"
    assert completed_runs[0]["target_show_date"] == "2024-01-20"
    assert completed_runs[0]["actual_songs"] == ["Song A", "Song G", "Song H"]
    assert completed_runs[0]["table_name"] == "completed_show_prediction_runs"
    assert completed_runs[0]["predictions"] == [
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


def test_run_backtest_disables_cached_artifacts_for_training_models(monkeypatch):
    shows_rows = [
        {"show_id": "goose-show-1", "show_date": "2024-01-01"},
        {"show_id": "goose-show-2", "show_date": "2024-01-20"},
    ]
    setlist_rows = [
        {"show_id": "goose-show-1", "song_name": "Song A"},
        {"show_id": "goose-show-1", "song_name": "Song B"},
        {"show_id": "goose-show-1", "song_name": "Song C"},
        {"show_id": "goose-show-2", "song_name": "Song D"},
        {"show_id": "goose-show-2", "song_name": "Song E"},
        {"show_id": "goose-show-2", "song_name": "Song F"},
    ]

    def fetch_table(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
        if table_name == "goose_shows_raw":
            return shows_rows
        if table_name == "goose_setlists_raw":
            return setlist_rows
        raise AssertionError(f"Unexpected table: {table_name}")

    seen: dict[str, object] = {}

    monkeypatch.setattr(run_backtest_module, "fetch_table", fetch_table)
    monkeypatch.setattr(
        run_backtest_module, "generate_model_data", lambda *args, **kwargs: object()
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_predictor",
        lambda slug, *, band, **kwargs: seen.update({"kwargs": kwargs})
        or _TrainingPredictorStub(),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "serialize_model_predictions",
        lambda slug, preds: [
            {"rank": index + 1, "song_name": prediction.song_name}
            for index, prediction in enumerate(preds)
        ],
    )
    monkeypatch.setattr(run_backtest_module, "upsert_dataframe", lambda **kwargs: None)
    monkeypatch.setattr(
        run_backtest_module,
        "upsert_completed_show_prediction_run",
        lambda **kwargs: 123,
    )
    monkeypatch.setattr(
        run_backtest_module, "fetch_scored_show_ids", lambda *a, **kw: set()
    )
    monkeypatch.setattr(
        run_backtest_module, "prune_completed_show_corpus", lambda **kwargs: None
    )

    run_backtest_module.run_backtest(
        band="goose",
        model="deal",
        start=None,
        end=None,
        shows=1,
        exclusion_window=3,
    )

    assert seen["kwargs"] == {"persist_artifacts": False}


def test_run_backtest_dry_run_skips_writes_and_pruning(monkeypatch, capsys):
    shows_rows = [
        {"show_id": "goose-show-1", "show_date": "2024-01-01"},
        {"show_id": "goose-show-2", "show_date": "2024-01-20"},
    ]
    setlist_rows = [
        {"show_id": "goose-show-1", "song_name": "Song A"},
        {"show_id": "goose-show-1", "song_name": "Song B"},
        {"show_id": "goose-show-1", "song_name": "Song C"},
        {"show_id": "goose-show-2", "song_name": "Song A"},
        {"show_id": "goose-show-2", "song_name": "Song G"},
        {"show_id": "goose-show-2", "song_name": "Song H"},
    ]

    def fetch_table(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
        if table_name == "goose_shows_raw":
            return shows_rows
        if table_name == "goose_setlists_raw":
            return setlist_rows
        raise AssertionError(f"Unexpected table: {table_name}")

    monkeypatch.setattr(run_backtest_module, "fetch_table", fetch_table)
    monkeypatch.setattr(
        run_backtest_module, "generate_model_data", lambda *args, **kwargs: object()
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_predictor",
        lambda slug, *, band: _NotebookPredictorStub(),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_model_definition",
        lambda slug: replace(get_model_definition(slug), default_top_k=50),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "serialize_model_predictions",
        lambda slug, preds: [
            {"rank": index + 1, "song_name": prediction.song_name}
            for index, prediction in enumerate(preds)
        ],
    )
    monkeypatch.setattr(
        run_backtest_module,
        "persist_scored_run_records",
        lambda *a, **kw: pytest.fail("dry run should not persist scored records"),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "prune_completed_show_corpus",
        lambda **kwargs: pytest.fail("dry run should not prune retained rows"),
    )
    monkeypatch.setattr(
        run_backtest_module, "fetch_scored_show_ids", lambda *a, **kw: set()
    )

    scored = run_backtest_module.run_backtest(
        band="goose",
        model="notebook",
        start=None,
        end=None,
        shows=2,
        exclusion_window=3,
        dry_run=True,
    )

    assert scored == 2
    output = capsys.readouterr().out
    assert (
        "[GOOSE/NOTEBOOK] Scoring retained show 1/2: "
        "target_show_date=2024-01-01 show_id=goose-show-1"
    ) in output
    assert (
        "[GOOSE/NOTEBOOK] Scoring retained show 2/2: "
        "target_show_date=2024-01-20 show_id=goose-show-2"
    ) in output


def test_run_backtest_raises_when_results_required_and_none_generated(monkeypatch):
    monkeypatch.setattr(
        run_backtest_module,
        "load_backtest_frames",
        lambda band, snapshot_root=None: (
            pd.DataFrame([{"show_id": "goose-show-1", "show_date": "2024-01-20"}]),
            pd.DataFrame(
                [
                    {"show_id": "goose-show-1", "song_name": "Song A"},
                    {"show_id": "goose-show-1", "song_name": "Song B"},
                    {"show_id": "goose-show-1", "song_name": "Song C"},
                ]
            ),
        ),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "list_completed_shows",
        lambda shows_df, sets_df: pd.DataFrame(
            [{"show_id": "goose-show-1", "show_date": pd.Timestamp("2024-01-20")}]
        ),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "select_target_shows",
        lambda completed_shows, **kwargs: completed_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_model_definition",
        lambda slug: get_model_definition("notebook"),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_scored_run_records",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        run_backtest_module, "fetch_scored_show_ids", lambda *a, **kw: set()
    )

    with pytest.raises(RuntimeError, match="No results generated from backtest"):
        run_backtest_module.run_backtest(
            band="goose",
            model="notebook",
            start=None,
            end=None,
            shows=1,
            exclusion_window=3,
            require_results=True,
        )


def test_run_backtest_writes_no_output_when_all_scored(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_backtest_module,
        "load_backtest_frames",
        lambda band, snapshot_root=None: (
            pd.DataFrame(
                [
                    {"show_id": "goose-show-1", "show_date": "2024-01-20"},
                    {"show_id": "goose-show-2", "show_date": "2024-01-25"},
                ]
            ),
            pd.DataFrame(
                [
                    {"show_id": "goose-show-1", "song_name": "Song A"},
                    {"show_id": "goose-show-1", "song_name": "Song B"},
                    {"show_id": "goose-show-1", "song_name": "Song C"},
                    {"show_id": "goose-show-2", "song_name": "Song D"},
                    {"show_id": "goose-show-2", "song_name": "Song E"},
                    {"show_id": "goose-show-2", "song_name": "Song F"},
                ]
            ),
        ),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "list_completed_shows",
        lambda shows_df, sets_df: shows_df,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "select_target_shows",
        lambda completed_shows, **kwargs: completed_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_show_ids",
        lambda *a, **kw: {"goose-show-1", "goose-show-2"},
    )

    output_file = tmp_path / "gha_output"
    output_file.write_text("backtest_incremental_all_scored=true\n")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    result = run_backtest_module.run_backtest(
        band="goose",
        model="notebook",
        start=None,
        end=None,
        shows=2,
        exclusion_window=3,
    )

    assert result == 0
    assert output_file.read_text() == "backtest_incremental_all_scored=true\n"


def test_run_backtest_writes_github_output_false_when_new_shows(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_backtest_module,
        "load_backtest_frames",
        lambda band, snapshot_root=None: (
            pd.DataFrame([{"show_id": "goose-show-1", "show_date": "2024-01-20"}]),
            pd.DataFrame(
                [
                    {"show_id": "goose-show-1", "song_name": "Song A"},
                    {"show_id": "goose-show-1", "song_name": "Song B"},
                    {"show_id": "goose-show-1", "song_name": "Song C"},
                ]
            ),
        ),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "list_completed_shows",
        lambda shows_df, sets_df: shows_df,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "select_target_shows",
        lambda completed_shows, **kwargs: completed_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_model_definition",
        lambda slug: get_model_definition("notebook"),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_scored_run_records",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_show_ids",
        lambda *a, **kw: set(),
    )

    output_file = tmp_path / "gha_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    result = run_backtest_module.run_backtest(
        band="goose",
        model="notebook",
        start=None,
        end=None,
        shows=1,
        exclusion_window=3,
    )

    assert result == 0
    assert output_file.read_text() == "backtest_incremental_all_scored=false\n"


def test_run_backtest_no_github_output_when_env_not_set(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_backtest_module,
        "load_backtest_frames",
        lambda band, snapshot_root=None: (
            pd.DataFrame([{"show_id": "goose-show-1", "show_date": "2024-01-20"}]),
            pd.DataFrame(
                [
                    {"show_id": "goose-show-1", "song_name": "Song A"},
                    {"show_id": "goose-show-1", "song_name": "Song B"},
                    {"show_id": "goose-show-1", "song_name": "Song C"},
                ]
            ),
        ),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "list_completed_shows",
        lambda shows_df, sets_df: shows_df,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "select_target_shows",
        lambda completed_shows, **kwargs: completed_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_model_definition",
        lambda slug: get_model_definition("notebook"),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_scored_run_records",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_show_ids",
        lambda *a, **kw: {"goose-show-1"},
    )
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    candidate_file = tmp_path / "gha_output"
    assert not candidate_file.exists()

    result = run_backtest_module.run_backtest(
        band="goose",
        model="notebook",
        start=None,
        end=None,
        shows=1,
        exclusion_window=3,
    )

    assert result == 0
    assert not candidate_file.exists()
