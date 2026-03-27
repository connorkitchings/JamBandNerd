from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from scripts import generate_predictions as module
from src.jambandnerd.models.registry import get_model_definition


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


class _ModelData:
    recently_played_songs = ["Old Song"]


def _setup_common_monkeypatches(monkeypatch):
    monkeypatch.setattr(module, "fetch_table", lambda table: [{"id": table}])
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (shows_df, setlists_df),
    )
    monkeypatch.setattr(module, "resolve_reference_date", lambda *_args, **_kwargs: date(2026, 3, 27))
    monkeypatch.setattr(module, "generate_model_data", lambda *_args, **_kwargs: _ModelData())


def test_generate_predictions_uses_registry_for_tuple_predictors(monkeypatch):
    _setup_common_monkeypatches(monkeypatch)

    records: dict[str, object] = {}
    monkeypatch.setattr(module, "build_predictor", lambda slug, *, band, **kwargs: _TuplePredictor())
    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(get_model_definition(slug), default_top_k=2),
    )
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [{"song_name": prediction.song_name} for prediction in predictions],
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
    assert records["df"].iloc[0]["model_version"] == get_model_definition("notebook").version
    assert records["projection"]["model_version"] == get_model_definition("notebook").version


def test_generate_predictions_trains_training_capable_models(monkeypatch):
    _setup_common_monkeypatches(monkeypatch)

    predictor = _TrainingPredictor()
    monkeypatch.setattr(module, "build_predictor", lambda slug, *, band, **kwargs: predictor)
    monkeypatch.setattr(module, "get_model_definition", lambda slug: get_model_definition("deal"))
    monkeypatch.setattr(
        module,
        "serialize_model_predictions",
        lambda slug, predictions: [{"song_name": prediction.song_name} for prediction in predictions],
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


def test_main_rejects_retrain_for_non_training_models(monkeypatch):
    monkeypatch.setattr(module, "get_model_definition", lambda slug: get_model_definition("notebook"))
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

