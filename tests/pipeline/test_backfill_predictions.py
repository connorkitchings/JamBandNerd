from __future__ import annotations

from dataclasses import replace

import pandas as pd

from scripts import backfill_predictions as module
from src.jambandnerd.models.registry import get_model_definition


class _Prediction:
    def __init__(self, song_name: str):
        self.song_name = song_name


class _TuplePredictor:
    def predict(self, model_data, top_k=50):  # noqa: ARG002
        return ([_Prediction("Song A")], {"ok": True})


def test_backfill_band_uses_registry_prediction_table(monkeypatch):
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(
            get_model_definition("notebook"),
            prediction_table="predictions_custom",
        ),
    )
    monkeypatch.setattr(
        module,
        "check_stale_predictions",
        lambda band, model, prediction_table: seen.update(
            {
                "band": band,
                "model": model,
                "prediction_table": prediction_table,
            }
        )
        or [],
    )

    result = module.backfill_band("goose", "notebook", dry_run=True)

    assert seen["prediction_table"] == "predictions_custom"
    assert result["stale_count"] == 0


def test_regenerate_prediction_serializes_tuple_predictions(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        module,
        "fetch_table",
        lambda table: [
            {"show_date": "2026-03-20", "show_id": "goose-1", "song_name": "Song A"}
        ],
    )
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (
            pd.DataFrame([{"show_date": "2026-03-20", "show_id": "goose-1"}]),
            pd.DataFrame([{"show_id": "goose-1", "song_name": "Song A"}]),
        ),
    )
    monkeypatch.setattr(module, "generate_model_data", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        module, "build_predictor", lambda slug, *, band, **kwargs: _TuplePredictor()
    )
    monkeypatch.setattr(
        module,
        "get_model_definition",
        lambda slug: replace(get_model_definition("notebook"), default_top_k=1),
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
        lambda table_name, df, conflict_columns: captured.update(
            {"table": table_name, "payload": df.iloc[0]["predictions"]}
        ),
    )
    monkeypatch.setattr(module, "replace_prediction_projection", lambda **kwargs: None)

    success = module.regenerate_prediction(
        "goose", "notebook", "2026-03-21", exclusion_window=3
    )

    assert success is True
    assert captured["table"] == get_model_definition("notebook").prediction_table
    assert captured["payload"] == [{"song_name": "Song A"}]


def test_regenerate_prediction_disables_artifact_persistence_for_training_models(
    monkeypatch,
):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        module,
        "fetch_table",
        lambda table: [
            {"show_date": "2026-03-20", "show_id": "goose-1", "song_name": "Song A"}
        ],
    )
    monkeypatch.setattr(
        module,
        "prepare_band_data",
        lambda shows_df, setlists_df, band: (
            pd.DataFrame([{"show_date": "2026-03-20", "show_id": "goose-1"}]),
            pd.DataFrame([{"show_id": "goose-1", "song_name": "Song A"}]),
        ),
    )
    monkeypatch.setattr(module, "generate_model_data", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        module,
        "build_predictor",
        lambda slug, *, band, **kwargs: captured.update({"kwargs": kwargs})
        or _TuplePredictor(),
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
    monkeypatch.setattr(module, "upsert_dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "replace_prediction_projection", lambda **kwargs: None)

    success = module.regenerate_prediction(
        "goose", "deal", "2026-03-21", exclusion_window=3
    )

    assert success is True
    assert captured["kwargs"] == {"persist_artifacts": False}


def test_check_stale_skips_predictions_regenerated_after_show_date(monkeypatch):
    predictions = pd.DataFrame(
        [
            {
                "band": "wsp",
                "reference_date": "2026-01-05",
                "predicted_at": "2026-01-05T08:00:00+00:00",
                "model_version": "v1",
            },
            {
                "band": "wsp",
                "reference_date": "2026-01-06",
                "predicted_at": "2026-01-07T14:00:00+00:00",
                "model_version": "v1",
            },
        ]
    )
    monkeypatch.setattr(
        module,
        "fetch_table",
        lambda table, **kwargs: predictions.to_dict("records"),
    )
    shows_df = pd.DataFrame(
        [
            {"show_date": "2026-01-05", "show_id": "wsp-1"},
        ]
    )
    shows_df["show_date"] = shows_df["show_date"].astype(str)
    setlists_df = pd.DataFrame([{"show_id": "wsp-1", "song_name": "Song A"}])

    stale = module.check_stale_predictions(
        "wsp",
        "deal",
        "predictions_deal",
        shows_df=shows_df,
        setlists_df=setlists_df,
    )

    assert stale == []


def test_check_stale_flags_predictions_older_than_show_date(monkeypatch):
    predictions = pd.DataFrame(
        [
            {
                "band": "wsp",
                "reference_date": "2026-01-05",
                "predicted_at": "2026-01-05T08:00:00+00:00",
                "model_version": "v1",
            },
            {
                "band": "wsp",
                "reference_date": "2026-01-06",
                "predicted_at": "2026-01-05T09:00:00+00:00",
                "model_version": "v1",
            },
        ]
    )
    monkeypatch.setattr(
        module,
        "fetch_table",
        lambda table, **kwargs: predictions.to_dict("records"),
    )
    shows_df = pd.DataFrame(
        [
            {"show_date": "2026-01-05", "show_id": "wsp-1"},
        ]
    )
    shows_df["show_date"] = shows_df["show_date"].astype(str)
    setlists_df = pd.DataFrame([{"show_id": "wsp-1", "song_name": "Song A"}])

    stale = module.check_stale_predictions(
        "wsp",
        "deal",
        "predictions_deal",
        shows_df=shows_df,
        setlists_df=setlists_df,
    )

    assert len(stale) == 1
    assert stale[0]["reference_date"] == "2026-01-06"
