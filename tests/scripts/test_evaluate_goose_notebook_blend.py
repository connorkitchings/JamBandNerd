from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from jambandnerd.transformations.gaps import ModelData
from scripts.evaluate_goose_notebook_blend import (
    AggregateScore,
    AlphaResult,
    _notebook_ranked_songs,
    _rank_blended_candidates,
    _rank_scores,
    _select_best_alpha,
)


def _model_data() -> ModelData:
    plays = pd.DataFrame(
        [
            {
                "song_name": "Arcadia",
                "show_index": 1,
                "show_date": "2024-01-01",
            },
            {
                "song_name": "Arcadia",
                "show_index": 3,
                "show_date": "2024-01-03",
            },
            {
                "song_name": "Madhuvan",
                "show_index": 2,
                "show_date": "2024-01-02",
            },
            {
                "song_name": "Tumble",
                "show_index": 4,
                "show_date": "2024-01-04",
            },
            {
                "song_name": "Drive",
                "show_index": 5,
                "show_date": "2024-01-05",
            },
        ]
    )
    master = pd.DataFrame(
        [
            {
                "song_name": "Arcadia",
                "last_played_index": 3,
                "last_played_date": pd.Timestamp("2024-01-03"),
            },
            {
                "song_name": "Madhuvan",
                "last_played_index": 2,
                "last_played_date": pd.Timestamp("2024-01-02"),
            },
            {
                "song_name": "Tumble",
                "last_played_index": 4,
                "last_played_date": pd.Timestamp("2024-01-04"),
            },
            {
                "song_name": "Drive",
                "last_played_index": 5,
                "last_played_date": pd.Timestamp("2024-01-05"),
            },
        ]
    )
    return ModelData(
        historical_plays=plays,
        master_feature_set=master,
        reference_date=date(2024, 1, 6),
        reference_index=6,
        recently_played_songs=["Drive"],
        diagnostics={},
    )


def _score(
    *,
    p10: float,
    r50: float,
    dual: float,
) -> AggregateScore:
    return AggregateScore(
        p10=p10,
        p25=0.0,
        p50=0.0,
        r10=0.0,
        r25=0.0,
        r50=r50,
        weighted_score=0.0,
        dual_score=dual,
        n_shows=2,
    )


def test_rank_scores_normalize_best_to_one_and_worst_to_zero() -> None:
    scores = _rank_scores(["A", "B", "C"])

    assert scores["A"] == pytest.approx(1.0)
    assert scores["B"] == pytest.approx(0.5)
    assert scores["C"] == pytest.approx(0.0)


def test_notebook_ranked_songs_use_frequency_then_gap_and_exclude_recent() -> None:
    ranked = _notebook_ranked_songs(_model_data(), band="goose")

    assert ranked == ["Arcadia", "Madhuvan", "Tumble"]
    assert "Drive" not in ranked


def test_rank_blended_candidates_tie_breaks_by_gbm_then_notebook_then_song() -> None:
    candidates = pd.DataFrame(
        [
            {
                "song_name": "Beta",
                "gbm_rank_score": 0.7,
                "notebook_rank_score": 0.3,
            },
            {
                "song_name": "Alpha",
                "gbm_rank_score": 0.7,
                "notebook_rank_score": 0.3,
            },
            {
                "song_name": "Gamma",
                "gbm_rank_score": 0.3,
                "notebook_rank_score": 0.7,
            },
        ]
    )

    assert _rank_blended_candidates(candidates, alpha=0.5) == [
        "Alpha",
        "Beta",
        "Gamma",
    ]


def test_select_best_alpha_tracks_dual_p10_and_notebook_floor() -> None:
    results = [
        AlphaResult(
            alpha=0.0,
            metrics=_score(p10=0.264, r50=0.518, dual=0.391),
            delta_vs_notebook={},
            delta_vs_base={},
        ),
        AlphaResult(
            alpha=0.5,
            metrics=_score(p10=0.260, r50=0.540, dual=0.400),
            delta_vs_notebook={},
            delta_vs_base={},
        ),
        AlphaResult(
            alpha=1.0,
            metrics=_score(p10=0.242, r50=0.528, dual=0.385),
            delta_vs_notebook={},
            delta_vs_base={},
        ),
    ]

    selected = _select_best_alpha(results, notebook_p10=0.264)

    assert selected["best_dual"].alpha == pytest.approx(0.5)
    assert selected["best_p10"].alpha == pytest.approx(0.0)
    assert selected["best_floor_r50"].alpha == pytest.approx(0.5)
