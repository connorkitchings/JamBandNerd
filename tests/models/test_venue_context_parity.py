"""Training/prediction parity for show-context features.

Each fast predictor builds context features (tour/run position, same-venue run
position) once per historical target show while training and once for the
upcoming show while predicting. Both paths must produce identical values for
the same show, otherwise the model is fit on a feature it never sees at
inference time.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import pytest

from jambandnerd.models.billy.fast_predictor import BillyFastBaselinePredictor
from jambandnerd.models.goose.fast_predictor import _clean_plays as goose_clean_plays
from jambandnerd.models.goose.model import (
    GooseFastRankSpecialNotebookTop10Predictor,
)
from jambandnerd.models.phish.experiments import PhishFastPlusNotebookRankVenueRun
from jambandnerd.models.phish.fast_predictor import PhishFastPredictorV2
from jambandnerd.models.um.fast_predictor import UMFastPredictorV12
from jambandnerd.models.wsp.fast_predictor import WSPFastPredictor

CONTEXT_FEATURES = ("tour_position", "show_position_in_run", "same_venue_run_position")
CONTEXT_KEYS = (
    "show_id",
    "show_date",
    "tour_name",
    "venue_name",
    "city",
    "state",
    "country",
)
SONGS = ["Song A", "Song B", "Song C"]

# The final three shows share the venue NAME "The Fox Theatre" but the first is
# in a different city, so a name-only venue key over-counts the run (3 vs 2).
_VENUES: list[tuple[str, str, str]] = [
    *[(f"Hall {i}", "Somewhere", "ZZ") for i in range(20)],
    ("The Fox Theatre", "Atlanta", "GA"),
    ("The Fox Theatre", "Boulder", "CO"),
    ("The Fox Theatre", "Boulder", "CO"),  # target show
]
TARGET_INDEX = len(_VENUES)


def _plays() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    start = date(2024, 1, 1)
    for index, (venue, city, state) in enumerate(_VENUES, start=1):
        for song in SONGS:
            rows.append(
                {
                    "show_index": index,
                    "show_id": f"show-{index}",
                    "show_date": pd.Timestamp(start + timedelta(days=index)),
                    "song_name": song,
                    "venue_name": venue,
                    "city": city,
                    "state": state,
                    "country": "USA",
                    "tour_name": "Test Tour",
                    "set_type": "set 1",
                    "position": 1,
                }
            )
    return pd.DataFrame(rows)


def _target_context(plays: pd.DataFrame) -> dict[str, Any]:
    row = plays[plays["show_index"] == TARGET_INDEX].iloc[0]
    return {key: row[key] for key in CONTEXT_KEYS}


@pytest.mark.parametrize(
    "predictor_cls",
    [
        PhishFastPredictorV2,
        PhishFastPlusNotebookRankVenueRun,
        WSPFastPredictor,
        UMFastPredictorV12,
        BillyFastBaselinePredictor,
    ],
)
def test_matrix_predictor_context_features_match_between_train_and_predict(
    predictor_cls: type,
) -> None:
    plays = _plays()
    target_row = plays[plays["show_index"] == TARGET_INDEX].iloc[0]
    prior = plays[plays["show_index"] < TARGET_INDEX]
    predictor = predictor_cls()

    full_cache = predictor._prepare(plays)
    prior_cache = predictor._prepare(prior)
    j = list(full_cache["show_cols"]).index(TARGET_INDEX)
    songs = pd.Index(SONGS)
    series = pd.Series(1.0, index=songs)

    train_feats = predictor._extra_training_row_features(
        eligible_songs=songs,
        j=j,
        target_date=pd.Timestamp(target_row["show_date"]).date(),
        gap_e=series,
        career_pct=series,
        p25=series,
        p50=series,
        cache=full_cache,
        plays=plays,
        target_show_index=TARGET_INDEX,
    )
    predict_feats = predictor._extra_predict_features(
        eligible_songs=songs,
        n_shows=len(prior_cache["show_cols"]),
        ref_date=pd.Timestamp(target_row["show_date"]),
        gap_e=series,
        career_pct=series,
        p25=series,
        p50=series,
        cache=prior_cache,
        plays=prior,
        target_show_context=_target_context(plays),
    )

    for name in CONTEXT_FEATURES:
        assert name in train_feats, f"{predictor_cls.__name__} missing {name}"
        assert float(train_feats[name]) == float(predict_feats[name]), name
    # Same venue name in a different city must not count toward the run.
    assert float(train_feats["same_venue_run_position"]) == 2.0


def test_goose_context_features_match_between_train_and_predict() -> None:
    plays = goose_clean_plays(_plays())
    prior = plays[plays["show_index"] < TARGET_INDEX]
    predictor = GooseFastRankSpecialNotebookTop10Predictor()
    songs = pd.Index(SONGS)
    series = pd.Series(1.0, index=songs)
    target_date = pd.Timestamp(
        plays.loc[plays["show_index"] == TARGET_INDEX, "show_date"].iloc[0]
    ).date()

    full_cache = predictor._prepare(plays)
    prior_cache = predictor._prepare(prior)
    upper_col = list(full_cache["show_cols"]).index(TARGET_INDEX)
    # Training passes the target show's own row context via the shared helper.
    from jambandnerd.models.shared.venue_context import training_target_show_context

    train_ctx = predictor._context_features(
        eligible_songs=songs,
        upper_col=upper_col,
        target_date=target_date,
        p25=series,
        p50=series,
        cache=full_cache,
        plays=plays,
        target_show_context=training_target_show_context(plays, TARGET_INDEX),
        target_show_index=TARGET_INDEX,
    )
    predict_ctx = predictor._context_features(
        eligible_songs=songs,
        upper_col=len(prior_cache["show_cols"]),
        target_date=target_date,
        p25=series,
        p50=series,
        cache=prior_cache,
        plays=prior,
        target_show_context=_target_context(_plays()),
        target_show_index=None,
    )

    for name in CONTEXT_FEATURES:
        assert float(train_ctx[name]) == float(predict_ctx[name]), name
    assert float(train_ctx["same_venue_run_position"]) == 2.0
