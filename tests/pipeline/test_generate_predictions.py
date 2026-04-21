from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from scripts import generate_predictions as module
from src.jambandnerd.models.registry import get_model_definition

# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------


class _Prediction:
    def __init__(self, song_name: str):
        self.song_name = song_name


class _TuplePredictor:
    def predict(self, model_data, top_k=50):  # noqa: ARG002
        return ([_Prediction("Song A"), _Prediction("Song B")], {"ok": True})


class _TrainingPredictor:
    def __init__(self):
        self.trained = 0

    def train(self, model_data):  # noqa: ARG002
        self.trained += 1

    def predict(self, model_data, top_k=50):  # noqa: ARG002
        return [_Prediction("Song A")]


class _EmptyPredictor:
    def predict(self, model_data, top_k=50):  # noqa: ARG002
        return ([], {"ok": False})


class _ModelData:
    recently_played_songs = ["Old Song"]


def _setup_common_monkeypatches(monkeypatch):
    monkeypatch.setattr(module, "fetch_table", lambda table: [{"id": table}])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        module, "resolve_reference_date", lambda *_args, **_kwargs: date(2026, 3, 27)
    )
    monkeypatch.setattr(
        module, "generate_model_data", lambda *_args, **_kwargs: _ModelData()
    )


def _setup_write_monkeypatches(monkeypatch):
    monkeypatch.setattr(module, "upsert_dataframe", lambda **kwargs: None)
    monkeypatch.setattr(module, "replace_prediction_projection", lambda **kwargs: None)


def test_generate_predictions_uses_registry_for_tuple_predictors(monkeypatch):
    _setup_common_monkeypatches(monkeypatch)

    records: dict[str, object] = {}
    monkeypatch.setattr(
        module, "build_predictor", lambda slug, *, band, **kwargs: _TuplePredictor()
    )
    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(get_model_definition(slug), default_top_k=2),
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [
            {"song_name": prediction.song_name} for prediction in predictions
        ],
    )
    monkeypatch.setattr(
        module,
        "upsert_dataframe",
        lambda table_name, df, conflict_columns: records.update(
            {
                "table": table_name,
                "df": df,
                "conflict": conflict_columns,
            }
        ),
    )
    monkeypatch.setattr(
        module,
        "replace_prediction_projection",
        lambda **kwargs: records.update({"projection": kwargs}),
    )

    module.generate_predictions(
        band="goose",
        model="notebook",
        date_str=None,
        exclusion_window=3,
    )

    assert records["table"] == get_model_definition("notebook").prediction_table
    assert (
        records["df"].iloc[0]["model_version"]
        == get_model_definition("notebook").version
    )
    assert (
        records["projection"]["model_version"]
        == get_model_definition("notebook").version
    )


def test_generate_predictions_trains_training_capable_models(monkeypatch):
    _setup_common_monkeypatches(monkeypatch)

    predictor = _TrainingPredictor()
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        module,
        "build_predictor",
        lambda slug, *, band, **kwargs: seen.update({"kwargs": kwargs}) or predictor,
    )
    monkeypatch.setattr(
        module, "get_model_definition", lambda slug: get_model_definition("deal")
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [
            {"song_name": prediction.song_name} for prediction in predictions
        ],
    )
    monkeypatch.setattr(module, "upsert_dataframe", lambda **kwargs: None)
    monkeypatch.setattr(module, "replace_prediction_projection", lambda **kwargs: None)

    module.generate_predictions(
        band="goose",
        model="deal",
        date_str=None,
        exclusion_window=3,
    )

    assert predictor.trained == 1
    assert seen["kwargs"] == {"persist_artifacts": False}


def test_generate_predictions_retrain_allows_training_artifact_persistence(monkeypatch):
    _setup_common_monkeypatches(monkeypatch)

    predictor = _TrainingPredictor()
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        module,
        "build_predictor",
        lambda slug, *, band, **kwargs: seen.update({"kwargs": kwargs}) or predictor,
    )
    monkeypatch.setattr(
        module, "get_model_definition", lambda slug: get_model_definition("deal")
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [
            {"song_name": prediction.song_name} for prediction in predictions
        ],
    )
    monkeypatch.setattr(module, "upsert_dataframe", lambda **kwargs: None)
    monkeypatch.setattr(module, "replace_prediction_projection", lambda **kwargs: None)

    module.generate_predictions(
        band="goose",
        model="deal",
        date_str=None,
        exclusion_window=3,
        retrain=True,
    )

    assert predictor.trained == 1
    assert seen["kwargs"] == {}


def test_main_rejects_retrain_for_non_training_models(monkeypatch):
    monkeypatch.setattr(
        module, "get_model_definition", lambda slug: get_model_definition("notebook")
    )
    monkeypatch.setattr(
        module,
        "generate_predictions",
        lambda **kwargs: pytest.fail("generate_predictions should not run"),
    )
    monkeypatch.setattr(
        module.sys,
        "argv",
        [
            "generate_predictions.py",
            "--band",
            "goose",
            "--model",
            "notebook",
            "--retrain",
        ],
    )

    with pytest.raises(SystemExit):
        module.main()


def test_generate_predictions_raises_when_output_required_and_none_written(monkeypatch):
    _setup_common_monkeypatches(monkeypatch)

    monkeypatch.setattr(
        module, "build_predictor", lambda slug, *, band, **kwargs: _EmptyPredictor()
    )
    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(get_model_definition(slug), default_top_k=2),
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [
            {"song_name": prediction.song_name} for prediction in predictions
        ],
    )
    monkeypatch.setattr(
        module,
        "upsert_dataframe",
        lambda **kwargs: pytest.fail("upsert_dataframe should not run"),
    )
    monkeypatch.setattr(
        module,
        "replace_prediction_projection",
        lambda **kwargs: pytest.fail("replace_prediction_projection should not run"),
    )

    with pytest.raises(RuntimeError, match="No predictions were generated"):
        module.generate_predictions(
            band="goose",
            model="notebook",
            date_str=None,
            exclusion_window=3,
            require_output=True,
        )


# ---------------------------------------------------------------------------
# Multi-date batching tests
# ---------------------------------------------------------------------------


def test_batched_trains_once_for_two_dates(monkeypatch):
    """Training-capable models must train exactly once even with two distinct dates."""
    dates_iter = iter([date(2026, 3, 27), date(2026, 3, 28)])
    monkeypatch.setattr(module, "fetch_table", lambda table: [{"id": table}])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        module,
        "resolve_reference_date",
        lambda *_args, **_kwargs: next(dates_iter),
    )
    monkeypatch.setattr(
        module, "generate_model_data", lambda *_args, **_kwargs: _ModelData()
    )

    predictor = _TrainingPredictor()
    monkeypatch.setattr(
        module,
        "build_predictor",
        lambda slug, *, band, **kwargs: predictor,
    )
    monkeypatch.setattr(
        module, "get_model_definition", lambda slug: get_model_definition("deal")
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [
            {"song_name": p.song_name} for p in predictions
        ],
    )
    _setup_write_monkeypatches(monkeypatch)

    result = module.generate_predictions_batched(
        band="goose",
        model="deal",
        date_strs=["2026-03-27", "2026-03-28"],
        exclusion_window=None,
    )

    assert result is True
    assert predictor.trained == 1, (
        f"Expected train() to be called once, got {predictor.trained}"
    )


def test_batched_default_sentinel_resolves_as_upcoming_show(monkeypatch):
    """The 'default' string sentinel must be treated as None (upcoming show lookup)."""
    resolved: list = []
    monkeypatch.setattr(module, "fetch_table", lambda table: [{"id": table}])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )

    def _track_resolve(date_str, *args, **kwargs):
        resolved.append(date_str)
        return date(2026, 3, 27)

    monkeypatch.setattr(module, "resolve_reference_date", _track_resolve)
    monkeypatch.setattr(
        module, "generate_model_data", lambda *_args, **_kwargs: _ModelData()
    )
    monkeypatch.setattr(
        module, "build_predictor", lambda slug, *, band, **kwargs: _TuplePredictor()
    )
    monkeypatch.setattr(
        module, "get_model_definition", lambda slug: get_model_definition("notebook")
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [{"song_name": p.song_name} for p in predictions],
    )
    _setup_write_monkeypatches(monkeypatch)

    module.generate_predictions_batched(
        band="goose",
        model="notebook",
        date_strs=["default", "2026-03-28"],
        exclusion_window=None,
    )

    # "default" should arrive at resolve_reference_date as None
    assert None in resolved, f"Expected None in resolved calls, got {resolved}"


def test_batched_deduplicates_identical_dates(monkeypatch):
    """Passing the same date twice should result in exactly one prediction write."""
    monkeypatch.setattr(module, "fetch_table", lambda table: [{"id": table}])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(
        module,
        "resolve_reference_date",
        lambda *_args, **_kwargs: date(2026, 3, 27),
    )
    monkeypatch.setattr(
        module, "generate_model_data", lambda *_args, **_kwargs: _ModelData()
    )
    monkeypatch.setattr(
        module, "build_predictor", lambda slug, *, band, **kwargs: _TuplePredictor()
    )
    monkeypatch.setattr(
        module, "get_model_definition", lambda slug: get_model_definition("notebook")
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [{"song_name": p.song_name} for p in predictions],
    )
    write_count = {"n": 0}
    monkeypatch.setattr(
        module,
        "upsert_dataframe",
        lambda **kwargs: write_count.update({"n": write_count["n"] + 1}),
    )
    monkeypatch.setattr(module, "replace_prediction_projection", lambda **kwargs: None)

    module.generate_predictions_batched(
        band="goose",
        model="notebook",
        date_strs=["2026-03-27", "2026-03-27"],
        exclusion_window=None,
    )

    assert write_count["n"] == 1, f"Expected 1 write, got {write_count['n']}"
