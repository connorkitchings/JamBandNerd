from __future__ import annotations

import pandas as pd
import pytest

from scripts import run_backtest as run_backtest_module
from src.jambandnerd.models.registry import get_band_model_version

_VERIFY_SUPABASE_WRITE_ACCESS = run_backtest_module._verify_supabase_write_access


@pytest.fixture(autouse=True)
def _skip_supabase_write_preflight(monkeypatch):
    monkeypatch.setattr(
        run_backtest_module,
        "_verify_supabase_write_access",
        lambda: None,
    )


def test_supabase_write_preflight_accepts_trimmed_secret_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "  sb_secret_valid_key  \n")
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    _VERIFY_SUPABASE_WRITE_ACCESS()


def test_supabase_write_preflight_rejects_publishable_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_publishable_invalid_key")
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="publishable/anon key"):
        _VERIFY_SUPABASE_WRITE_ACCESS()


def test_run_backtest_dry_run_skips_writes_and_pruning(monkeypatch, capsys):
    shows_df = pd.DataFrame(
        [
            {"show_id": "goose-show-1", "show_date": "2024-01-01"},
            {"show_id": "goose-show-2", "show_date": "2024-01-20"},
        ]
    )
    sets_df = pd.DataFrame(
        [
            {"show_id": "goose-show-1", "song_name": "Song A"},
            {"show_id": "goose-show-1", "song_name": "Song B"},
            {"show_id": "goose-show-1", "song_name": "Song C"},
            {"show_id": "goose-show-2", "song_name": "Song A"},
            {"show_id": "goose-show-2", "song_name": "Song G"},
            {"show_id": "goose-show-2", "song_name": "Song H"},
        ]
    )

    monkeypatch.setattr(
        run_backtest_module,
        "load_backtest_frames",
        lambda band, snapshot_root=None: (shows_df, sets_df),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "list_completed_shows",
        lambda loaded_shows, loaded_sets: loaded_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "select_target_shows",
        lambda completed_shows, **kwargs: completed_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_target_show_keys",
        lambda *a, **kw: set(),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_scored_run_records",
        lambda **kwargs: [
            {"band": "goose", "show_id": "goose-show-1", "model_version": "mv"},
            {"band": "goose", "show_id": "goose-show-2", "model_version": "mv"},
        ],
    )
    monkeypatch.setattr(
        run_backtest_module,
        "summarize_scored_run_records",
        lambda records: {
            k: {
                "hit_rate": 1.0,
                "avg_matches": 1.0,
                "precision": 1.0 / k,
                "recall": 1.0,
                "f1": 0.5,
                "ndcg": 1.0,
            }
            for k in (10, 25, 50)
        },
    )
    monkeypatch.setattr(
        run_backtest_module,
        "persist_scored_run_records",
        lambda *a, **kw: pytest.fail("dry run should not persist scored records"),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "prune_setlist_corpus",
        lambda **kwargs: pytest.fail("dry run should not prune retained rows"),
    )

    scored = run_backtest_module.run_backtest(
        band="goose",
        start=None,
        end=None,
        shows=2,
        exclusion_window=3,
        dry_run=True,
    )

    assert scored == 2
    output = capsys.readouterr().out
    assert "Dry run: scored 2 completed-show record(s)" in output


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
        "build_scored_run_records",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_target_show_keys",
        lambda *a, **kw: set(),
    )

    with pytest.raises(RuntimeError, match="No results generated from backtest"):
        run_backtest_module.run_backtest(
            band="goose",
            start=None,
            end=None,
            shows=1,
            exclusion_window=3,
            require_results=True,
        )


def test_run_backtest_writes_no_output_when_all_scored(monkeypatch, tmp_path):
    captured_prune: dict[str, object] = {}

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
        "fetch_scored_target_show_keys",
        lambda *a, **kw: {"goose-show-1", "goose-show-2"},
    )
    monkeypatch.setattr(
        run_backtest_module,
        "prune_setlist_corpus",
        lambda **kwargs: captured_prune.update(kwargs) or 1,
    )

    output_file = tmp_path / "gha_output"
    output_file.write_text("backtest_incremental_all_scored=true\n")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    result = run_backtest_module.run_backtest(
        band="goose",
        start=None,
        end=None,
        shows=2,
        exclusion_window=3,
    )

    assert result == 0
    assert output_file.read_text() == "backtest_incremental_all_scored=true\n"
    assert captured_prune["band"] == "goose"
    assert captured_prune["model_version"] == get_band_model_version("goose")
    assert captured_prune["retained_target_show_keys"] == [
        "goose-show-1",
        "goose-show-2",
    ]


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
        "build_scored_run_records",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_target_show_keys",
        lambda *a, **kw: set(),
    )

    output_file = tmp_path / "gha_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    result = run_backtest_module.run_backtest(
        band="goose",
        start=None,
        end=None,
        shows=1,
        exclusion_window=3,
    )

    assert result == 0
    assert output_file.read_text() == "backtest_incremental_all_scored=false\n"


def test_run_backtest_incremental_prune_keeps_full_retained_window(monkeypatch):
    shows_df = pd.DataFrame(
        [
            {"show_id": "goose-show-1", "show_date": "2024-01-20"},
            {"show_id": "goose-show-2", "show_date": "2024-01-25"},
        ]
    )
    sets_df = pd.DataFrame(
        [
            {"show_id": "goose-show-1", "song_name": "Song A"},
            {"show_id": "goose-show-1", "song_name": "Song B"},
            {"show_id": "goose-show-1", "song_name": "Song C"},
            {"show_id": "goose-show-2", "song_name": "Song D"},
            {"show_id": "goose-show-2", "song_name": "Song E"},
            {"show_id": "goose-show-2", "song_name": "Song F"},
        ]
    )
    scored_records = [
        {
            "band": "goose",
            "model_version": "goose_fast_rank_v1_candidate_relaxed_special_nbtop10",
            "show_id": "goose-show-2",
            "target_show_key": "goose-show-2",
            "target_show_date": "2024-01-25",
            "show_date": "2024-01-25",
            "reference_date": "2024-01-24",
            "actual_song_count": 3,
            "metrics": {
                f"k{k}": {
                    "hit": True,
                    "matches": 1,
                    "precision": 1 / k,
                    "recall": 1 / 3,
                    "f1": 0.1,
                    "ndcg": 1.0,
                }
                for k in (10, 25, 50)
            },
        }
    ]
    captured_prune: dict[str, object] = {}

    monkeypatch.setattr(
        run_backtest_module,
        "load_backtest_frames",
        lambda band, snapshot_root=None: (shows_df, sets_df),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "list_completed_shows",
        lambda loaded_shows, loaded_sets: loaded_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "select_target_shows",
        lambda completed_shows, **kwargs: completed_shows,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_target_show_keys",
        lambda *a, **kw: {"goose-show-1"},
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_scored_run_records",
        lambda **kwargs: scored_records,
    )
    monkeypatch.setattr(
        run_backtest_module,
        "persist_scored_run_records",
        lambda *a, **kw: pd.DataFrame(scored_records),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "prune_setlist_corpus",
        lambda **kwargs: captured_prune.update(kwargs) or 0,
    )

    result = run_backtest_module.run_backtest(
        band="goose",
        start=None,
        end=None,
        shows=2,
        exclusion_window=3,
    )

    assert result == 1
    assert captured_prune["retained_target_show_keys"] == [
        "goose-show-1",
        "goose-show-2",
    ]


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
        "fetch_scored_target_show_keys",
        lambda *a, **kw: {"goose-show-1"},
    )
    monkeypatch.setattr(
        run_backtest_module,
        "prune_setlist_corpus",
        lambda **kwargs: 0,
    )
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    candidate_file = tmp_path / "gha_output"
    assert not candidate_file.exists()

    result = run_backtest_module.run_backtest(
        band="goose",
        start=None,
        end=None,
        shows=1,
        exclusion_window=3,
    )

    assert result == 0
    assert not candidate_file.exists()
