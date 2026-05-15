from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from jambandnerd.transformations.gaps import ModelData
from scripts.evaluate_goose_notebook_blend import (
    AggregateScore,
    AlphaResult,
    BlendCacheConfig,
    _build_blend_cache_identity,
    _cache_record_path,
    _deserialize_scored_show,
    _load_cached_scored_show,
    _notebook_ranked_songs,
    _ordered_scored_shows,
    _rank_blended_candidates,
    _rank_scores,
    _score_target_shows_with_cache,
    _select_best_alpha,
    _serialize_scored_show,
    _stable_hash,
    _write_cached_scored_show,
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
    p25: float = 0.0,
    f1_25: float = 0.0,
    r50: float,
    dual: float,
    dual_f1: float = 0.0,
) -> AggregateScore:
    return AggregateScore(
        p10=p10,
        p25=p25,
        p50=0.0,
        r10=0.0,
        r25=0.0,
        r50=r50,
        f1_10=0.0,
        f1_25=f1_25,
        f1_50=0.0,
        weighted_score=0.0,
        dual_score=dual,
        dual_f1_score=dual_f1,
        avg_actual_song_count=0.0,
        avg_p25_ceiling=0.0,
        n_shows=2,
    )


def _scored_show(show_id: str = "show-1", target_show_date: str = "2026-04-25"):
    return {
        "show_id": show_id,
        "target_show_date": target_show_date,
        "reference_date": "2026-04-24",
        "actual_songs": ["Arcadia", "Drive"],
        "notebook_songs": ["Arcadia", "Drive", "Tumble"],
        "candidates": pd.DataFrame(
            [
                {
                    "song_name": "Arcadia",
                    "gbm_raw_score": 2.0,
                    "gbm_rank_score": 1.0,
                    "notebook_rank_score": 1.0,
                    "unused_column": "drop-me",
                },
                {
                    "song_name": "Drive",
                    "gbm_raw_score": 1.0,
                    "gbm_rank_score": 0.5,
                    "notebook_rank_score": 0.5,
                    "unused_column": "drop-me",
                },
            ]
        ),
    }


def _target_shows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"show_id": "show-1", "show_date": date(2026, 4, 24)},
            {"show_id": "show-2", "show_date": date(2026, 4, 25)},
        ]
    )


def test_rank_scores_normalize_best_to_one_and_worst_to_zero() -> None:
    scores = _rank_scores(["A", "B", "C"])

    assert scores["A"] == pytest.approx(1.0)
    assert scores["B"] == pytest.approx(0.5)
    assert scores["C"] == pytest.approx(0.0)


def test_blend_cache_identity_changes_with_snapshot_and_features() -> None:
    base = _build_blend_cache_identity(
        band="goose",
        predictor_path="jambandnerd.models.goose.model.GooseGbmV2Predictor",
        model_version="goose_phase_b_v2_gbm",
        feature_columns=["current_gap", "avg_ltp"],
        shows=2,
        target_shows=_target_shows(),
        snapshot_manifest={"tables": {"goose_shows_raw": {"row_count": 2}}},
    )
    changed_snapshot = _build_blend_cache_identity(
        band="goose",
        predictor_path="jambandnerd.models.goose.model.GooseGbmV2Predictor",
        model_version="goose_phase_b_v2_gbm",
        feature_columns=["current_gap", "avg_ltp"],
        shows=2,
        target_shows=_target_shows(),
        snapshot_manifest={"tables": {"goose_shows_raw": {"row_count": 3}}},
    )
    changed_features = _build_blend_cache_identity(
        band="goose",
        predictor_path="jambandnerd.models.goose.model.GooseGbmV2Predictor",
        model_version="goose_phase_b_v2_gbm",
        feature_columns=["current_gap", "avg_ltp", "new_feature"],
        shows=2,
        target_shows=_target_shows(),
        snapshot_manifest={"tables": {"goose_shows_raw": {"row_count": 2}}},
    )

    assert _stable_hash(base) != _stable_hash(changed_snapshot)
    assert _stable_hash(base) != _stable_hash(changed_features)


def test_blend_cache_roundtrip_reconstructs_candidates(tmp_path) -> None:
    cache_path = _cache_record_path(
        cache_dir=tmp_path,
        show_id="show-1",
        target_show_date="2026-04-25",
    )
    original = _scored_show()

    _write_cached_scored_show(cache_path, original)
    loaded = _load_cached_scored_show(cache_path)

    assert loaded is not None
    assert loaded["show_id"] == original["show_id"]
    assert loaded["actual_songs"] == original["actual_songs"]
    assert list(loaded["candidates"].columns) == [
        "song_name",
        "gbm_raw_score",
        "gbm_rank_score",
        "notebook_rank_score",
    ]
    assert "unused_column" not in _serialize_scored_show(original)["candidates"][0]
    assert _deserialize_scored_show(_serialize_scored_show(original))["show_id"] == (
        "show-1"
    )


def test_cached_show_records_skip_scorer(monkeypatch, tmp_path) -> None:
    cache_path = _cache_record_path(
        cache_dir=tmp_path,
        show_id="show-1",
        target_show_date="2026-04-24",
    )
    _write_cached_scored_show(cache_path, _scored_show(target_show_date="2026-04-24"))

    def fail_if_called(**kwargs):
        raise AssertionError("scorer should not run on cache hit")

    monkeypatch.setattr(
        "scripts.evaluate_goose_notebook_blend._score_target_show",
        fail_if_called,
    )

    scored, stats = _score_target_shows_with_cache(
        band="goose",
        predictor_path="unused.Predictor",
        predictor_class=object,
        shows_df=pd.DataFrame(),
        sets_df=pd.DataFrame(),
        target_shows=pd.DataFrame(
            [{"show_id": "show-1", "show_date": date(2026, 4, 24)}]
        ),
        cache_config=BlendCacheConfig(
            enabled=True,
            cache_dir=tmp_path,
            force_rebuild=False,
        ),
        jobs=1,
    )

    assert scored[0]["show_id"] == "show-1"
    assert stats.hits == 1
    assert stats.misses == 0
    assert stats.writes == 0


def test_force_rebuild_cache_bypasses_existing_record(monkeypatch, tmp_path) -> None:
    cache_path = _cache_record_path(
        cache_dir=tmp_path,
        show_id="show-1",
        target_show_date="2026-04-24",
    )
    _write_cached_scored_show(cache_path, _scored_show(target_show_date="2026-04-24"))

    def score_rebuilt(**kwargs):
        return _scored_show(show_id="show-1", target_show_date="2026-04-24")

    monkeypatch.setattr(
        "scripts.evaluate_goose_notebook_blend._score_target_show",
        score_rebuilt,
    )

    scored, stats = _score_target_shows_with_cache(
        band="goose",
        predictor_path="unused.Predictor",
        predictor_class=object,
        shows_df=pd.DataFrame(),
        sets_df=pd.DataFrame(),
        target_shows=pd.DataFrame(
            [{"show_id": "show-1", "show_date": date(2026, 4, 24)}]
        ),
        cache_config=BlendCacheConfig(
            enabled=True,
            cache_dir=tmp_path,
            force_rebuild=True,
        ),
        jobs=1,
    )

    assert scored[0]["show_id"] == "show-1"
    assert stats.hits == 0
    assert stats.misses == 1
    assert stats.writes == 1


def test_ordered_scored_shows_preserves_target_order() -> None:
    ordered = _ordered_scored_shows(
        {
            2: _scored_show(show_id="show-3"),
            0: _scored_show(show_id="show-1"),
            1: _scored_show(show_id="show-2"),
        }
    )

    assert [row["show_id"] for row in ordered] == ["show-1", "show-2", "show-3"]


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

    selected = _select_best_alpha(results, notebook_p10=0.264, notebook_p25=0.0)

    assert selected["best_dual"].alpha == pytest.approx(0.5)
    assert selected["best_p10"].alpha == pytest.approx(0.0)
    assert selected["best_floor_r50"].alpha == pytest.approx(0.5)


def test_select_best_alpha_tracks_guarded_dual_f1() -> None:
    results = [
        AlphaResult(
            alpha=0.0,
            metrics=_score(
                p10=0.280,
                p25=0.210,
                f1_25=0.270,
                r50=0.520,
                dual=0.400,
                dual_f1=0.300,
            ),
            delta_vs_notebook={},
            delta_vs_base={},
        ),
        AlphaResult(
            alpha=0.5,
            metrics=_score(
                p10=0.276,
                p25=0.206,
                f1_25=0.275,
                r50=0.540,
                dual=0.410,
                dual_f1=0.320,
            ),
            delta_vs_notebook={},
            delta_vs_base={},
        ),
        AlphaResult(
            alpha=1.0,
            metrics=_score(
                p10=0.274,
                p25=0.204,
                f1_25=0.280,
                r50=0.550,
                dual=0.420,
                dual_f1=0.340,
            ),
            delta_vs_notebook={},
            delta_vs_base={},
        ),
    ]

    selected = _select_best_alpha(results, notebook_p10=0.280, notebook_p25=0.210)

    assert selected["best_dual_f1_guarded"].alpha == pytest.approx(0.5)
