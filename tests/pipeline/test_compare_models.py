from __future__ import annotations

from copy import deepcopy

import pandas as pd

from scripts import compare_models as module
from scripts import run_backtest as backtest_module


class _Prediction:
    def __init__(self, song_name: str):
        self.song_name = song_name
        self.plays_past_year = 1
        self.current_gap = 5
        self.last_played_date = "2023-12-31"


class _Predictor:
    def __init__(self, model_slug: str):
        self.model_slug = model_slug

    def predict(self, model_data, top_k=50):  # noqa: ARG002
        if self.model_slug == "notebook":
            return ([_Prediction("Song A"), _Prediction("Song B")], {})
        if self.model_slug == "ckplus":
            return ([_Prediction("Song A"), _Prediction("Song Z")], {})
        return [_Prediction("Song A")]


def _mock_tables(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
    if table_name == "goose_shows_raw":
        return [
            {"show_id": "goose-show-1", "show_date": "2024-01-01"},
            {"show_id": "goose-show-2", "show_date": "2024-01-10"},
            {"show_id": "goose-show-3", "show_date": "2024-01-20"},
        ]
    if table_name == "goose_setlists_raw":
        return [
            {"show_id": "goose-show-1", "song_name": "Song A"},
            {"show_id": "goose-show-1", "song_name": "Song B"},
            {"show_id": "goose-show-1", "song_name": "Song C"},
            {"show_id": "goose-show-2", "song_name": "Song A"},
            {"show_id": "goose-show-2", "song_name": "Song D"},
            {"show_id": "goose-show-2", "song_name": "Song E"},
            {"show_id": "goose-show-3", "song_name": "Song A"},
            {"show_id": "goose-show-3", "song_name": "Song F"},
            {"show_id": "goose-show-3", "song_name": "Song G"},
        ]
    raise AssertionError(f"Unexpected table: {table_name}")


def _mock_tables_multi_band(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
    band = table_name.split("_", 1)[0]
    if table_name.endswith("_shows_raw"):
        return [
            {"show_id": f"{band}-show-1", "show_date": "2024-01-01"},
            {"show_id": f"{band}-show-2", "show_date": "2024-01-10"},
            {"show_id": f"{band}-show-3", "show_date": "2024-01-20"},
        ]
    if table_name.endswith("_setlists_raw"):
        return [
            {"show_id": f"{band}-show-1", "song_name": "Song A"},
            {"show_id": f"{band}-show-1", "song_name": "Song B"},
            {"show_id": f"{band}-show-1", "song_name": "Song C"},
            {"show_id": f"{band}-show-2", "song_name": "Song A"},
            {"show_id": f"{band}-show-2", "song_name": "Song D"},
            {"show_id": f"{band}-show-2", "song_name": "Song E"},
            {"show_id": f"{band}-show-3", "song_name": "Song A"},
            {"show_id": f"{band}-show-3", "song_name": "Song F"},
            {"show_id": f"{band}-show-3", "song_name": "Song G"},
        ]
    raise AssertionError(f"Unexpected table: {table_name}")


def _serialize_predictions(slug, predictions):  # noqa: ARG001
    return [
        {
            "rank": index + 1,
            "song_name": prediction.song_name,
            "plays_past_year": prediction.plays_past_year,
            "current_gap": prediction.current_gap,
            "last_played_date": prediction.last_played_date,
        }
        for index, prediction in enumerate(predictions)
    ]


def test_compare_models_generate_report_emits_schema(monkeypatch):
    monkeypatch.setattr(module, "fetch_table", _mock_tables)
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        module,
        "build_evaluation_predictor",
        lambda model_slug, *, band, fresh_training=False: _Predictor(model_slug),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.build_evaluation_predictor",
        lambda model_slug, *, band, fresh_training=False: _Predictor(model_slug),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.generate_model_data",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.serialize_model_predictions",
        _serialize_predictions,
    )

    report = module.generate_report(
        candidate_model="deal",
        baseline_models=["ckplus", "notebook"],
        bands=["goose"],
        windows=[{"label": "last_2", "shows": 2}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
        include_candidate_diagnostics=False,
    )

    assert report["candidate_model"] == {"slug": "deal", "version": "deal_v2"}
    assert report["baseline_models"] == [
        {"slug": "ckplus", "version": "ckplus_v1"},
        {"slug": "notebook", "version": "notebook_v1"},
    ]
    assert report["requested_bands"] == ["goose"]
    assert report["completed_bands"] == ["goose"]
    assert report["report_status"] == "complete"
    window = report["windows"]["last_2"]
    assert "metrics_by_band" in window
    assert "cross_band_summary" in window
    assert "deltas" in window
    assert "promotion_gate" in window
    assert set(window["metrics_by_band"]["goose"].keys()) == {
        "deal",
        "ckplus",
        "notebook",
    }


def test_compare_models_parse_window_specs_accepts_positive_integers_only():
    assert module._parse_window_specs(["50"]) == [{"label": "last_50", "shows": 50}]

    try:
        module._parse_window_specs(["all-history"])
    except ValueError as exc:
        assert "Unsupported window spec" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError(
            "all-history should not be accepted as a comparison window"
        )


def test_compare_models_promotion_gate_fails_when_candidate_loses(monkeypatch):
    monkeypatch.setattr(module, "fetch_table", _mock_tables)
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.build_evaluation_predictor",
        lambda model_slug, *, band, fresh_training=False: _Predictor(model_slug),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.generate_model_data",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.serialize_model_predictions",
        _serialize_predictions,
    )

    report = module.generate_report(
        candidate_model="deal",
        baseline_models=["ckplus"],
        bands=["goose"],
        windows=[{"label": "last_2", "shows": 2}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
        include_candidate_diagnostics=False,
    )

    assert report["windows"]["last_2"]["promotion_gate"]["passes"] is False


def test_compare_models_candidate_notebook_matches_backtest_metrics(monkeypatch):
    monkeypatch.setattr(module, "fetch_table", _mock_tables)
    monkeypatch.setattr(backtest_module, "fetch_table", _mock_tables)
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        backtest_module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.build_evaluation_predictor",
        lambda model_slug, *, band, fresh_training=False: _Predictor(model_slug),
    )
    monkeypatch.setattr(
        backtest_module,
        "build_predictor",
        lambda slug, *, band: _Predictor(slug),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.generate_model_data",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        backtest_module,
        "generate_model_data",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.serialize_model_predictions",
        _serialize_predictions,
    )
    monkeypatch.setattr(
        backtest_module, "serialize_model_predictions", _serialize_predictions
    )

    captured: dict[str, pd.DataFrame] = {}
    monkeypatch.setattr(
        backtest_module,
        "upsert_historical_prediction_run",
        lambda **kwargs: 101,
    )
    monkeypatch.setattr(
        backtest_module,
        "upsert_dataframe",
        lambda table_name, df, conflict_columns: captured.update({"df": df.copy()}),
    )

    backtest_module.run_backtest(
        band="goose",
        model="notebook",
        start=None,
        end=None,
        shows=2,
        exclusion_window=3,
    )
    report = module.generate_report(
        candidate_model="notebook",
        baseline_models=["ckplus"],
        bands=["goose"],
        windows=[{"label": "last_2", "shows": 2}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=False,
        include_candidate_diagnostics=False,
    )

    expected_recall = captured["df"]["k10_recall"].mean()
    actual_recall = report["windows"]["last_2"]["metrics_by_band"]["goose"]["notebook"][
        "metrics"
    ]["k10"]["recall"]
    assert actual_recall == expected_recall


def test_compare_models_loads_each_band_once_across_multiple_windows(monkeypatch):
    fetch_events: list[str] = []

    def tracked_fetch(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
        fetch_events.append(table_name)
        return _mock_tables(table_name)

    monkeypatch.setattr(module, "fetch_table", tracked_fetch)
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.build_evaluation_predictor",
        lambda model_slug, *, band, fresh_training=False: _Predictor(model_slug),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.generate_model_data",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.serialize_model_predictions",
        _serialize_predictions,
    )

    module.generate_report(
        candidate_model="deal",
        baseline_models=["ckplus", "notebook"],
        bands=["goose"],
        windows=[
            {"label": "last_2", "shows": 2},
            {"label": "last_3", "shows": 3},
        ],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
        include_candidate_diagnostics=False,
    )

    assert fetch_events.count("goose_shows_raw") == 1
    assert fetch_events.count("goose_setlists_raw") == 1


def test_compare_models_raises_when_no_band_contexts_load(monkeypatch):
    monkeypatch.setattr(module, "fetch_table", lambda table_name, chunk_size=10000: [])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )

    try:
        module.generate_report(
            candidate_model="deal",
            baseline_models=["ckplus"],
            bands=["goose"],
            windows=[{"label": "last_2", "shows": 2}],
            exclusion_window=3,
            feature_set_label="shared_core_v1",
            fresh_training=True,
            include_candidate_diagnostics=False,
        )
    except RuntimeError as exc:
        assert "No band contexts were loaded" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("generate_report should fail when no band contexts load")


def test_compare_models_writes_partial_report_after_each_completed_band(
    monkeypatch, tmp_path
):
    snapshots: list[dict[str, object]] = []

    monkeypatch.setattr(module, "fetch_table", _mock_tables_multi_band)
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.build_evaluation_predictor",
        lambda model_slug, *, band, fresh_training=False: _Predictor(model_slug),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.generate_model_data",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.serialize_model_predictions",
        _serialize_predictions,
    )
    monkeypatch.setattr(
        module,
        "_write_json_report",
        lambda output_path, report: snapshots.append(deepcopy(report)),
    )

    report = module.generate_report(
        candidate_model="deal",
        baseline_models=["ckplus"],
        bands=["goose", "phish"],
        windows=[{"label": "last_2", "shows": 2}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
        include_candidate_diagnostics=False,
        output_path=tmp_path / "comparison.json",
    )

    assert [snapshot["completed_bands"] for snapshot in snapshots] == [
        ["goose"],
        ["goose", "phish"],
        ["goose", "phish"],
    ]
    assert snapshots[0]["report_status"] == "partial"
    assert snapshots[0]["windows"]["last_2"]["promotion_gate"]["passes"] is False
    assert snapshots[-1]["report_status"] == "complete"
    assert report["completed_bands"] == ["goose", "phish"]


def test_compare_models_resume_skips_completed_bands(monkeypatch, tmp_path):
    fetch_events: list[str] = []

    def tracked_fetch(table_name: str, chunk_size: int = 10000):  # noqa: ARG001
        fetch_events.append(table_name)
        return _mock_tables_multi_band(table_name)

    monkeypatch.setattr(module, "fetch_table", tracked_fetch)
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.build_evaluation_predictor",
        lambda model_slug, *, band, fresh_training=False: _Predictor(model_slug),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.generate_model_data",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "src.jambandnerd.models.comparison.serialize_model_predictions",
        _serialize_predictions,
    )

    existing_report = {
        "candidate_model": {"slug": "deal", "version": "deal_v2"},
        "baseline_models": [{"slug": "ckplus", "version": "ckplus_v1"}],
        "experiment_metadata": {
            "evaluation_windows": ["last_2"],
            "exclusion_window": 3,
            "feature_set_label": "shared_core_v1",
            "fresh_training": True,
        },
        "requested_bands": ["goose", "phish"],
        "completed_bands": ["goose"],
        "report_status": "partial",
        "windows": {
            "last_2": {
                "metrics_by_band": {
                    "goose": {
                        "deal": {
                            "shows_evaluated": 2,
                            "metrics": {
                                "k10": {
                                    "hit_rate": 0.5,
                                    "avg_matches": 1,
                                    "precision": 0.1,
                                    "recall": 0.1,
                                    "f1": 0.1,
                                },
                                "k25": {
                                    "hit_rate": 0.5,
                                    "avg_matches": 1,
                                    "precision": 0.1,
                                    "recall": 0.1,
                                    "f1": 0.1,
                                },
                                "k50": {
                                    "hit_rate": 0.5,
                                    "avg_matches": 1,
                                    "precision": 0.1,
                                    "recall": 0.1,
                                    "f1": 0.1,
                                },
                            },
                        },
                        "ckplus": {
                            "shows_evaluated": 2,
                            "metrics": {
                                "k10": {
                                    "hit_rate": 0.6,
                                    "avg_matches": 1,
                                    "precision": 0.1,
                                    "recall": 0.2,
                                    "f1": 0.1,
                                },
                                "k25": {
                                    "hit_rate": 0.6,
                                    "avg_matches": 1,
                                    "precision": 0.1,
                                    "recall": 0.2,
                                    "f1": 0.1,
                                },
                                "k50": {
                                    "hit_rate": 0.6,
                                    "avg_matches": 1,
                                    "precision": 0.1,
                                    "recall": 0.2,
                                    "f1": 0.1,
                                },
                            },
                        },
                    }
                },
                "cross_band_summary": {},
                "deltas": {},
                "promotion_gate": {"passes": False},
            }
        },
    }

    report = module.generate_report(
        candidate_model="deal",
        baseline_models=["ckplus"],
        bands=["goose", "phish"],
        windows=[{"label": "last_2", "shows": 2}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
        include_candidate_diagnostics=False,
        output_path=tmp_path / "comparison.json",
        existing_report=existing_report,
    )

    assert "goose_shows_raw" not in fetch_events
    assert "goose_setlists_raw" not in fetch_events
    assert "phish_shows_raw" in fetch_events
    assert "phish_setlists_raw" in fetch_events
    assert report["completed_bands"] == ["goose", "phish"]
    assert set(report["windows"]["last_2"]["metrics_by_band"].keys()) == {
        "goose",
        "phish",
    }
