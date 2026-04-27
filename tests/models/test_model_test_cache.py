from __future__ import annotations

from src.jambandnerd.models.model_test_cache import (
    LocalModelTestCache,
    build_default_cache_dir,
    build_experiment_cache_identity,
    build_experiment_cache_key,
)


def test_experiment_cache_key_changes_when_context_changes() -> None:
    identity = build_experiment_cache_identity(
        candidate_model="deal",
        baseline_models=["ckplus", "notebook"],
        bands=["goose", "phish"],
        windows=[{"label": "last_100", "shows": 100}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
    )
    changed = build_experiment_cache_identity(
        candidate_model="deal",
        baseline_models=["ckplus", "notebook"],
        bands=["goose", "phish"],
        windows=[{"label": "last_100", "shows": 100}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
        candidate_overrides={"min_plays_threshold": 3},
    )

    assert build_experiment_cache_key(identity) != build_experiment_cache_key(changed)


def test_local_model_test_cache_roundtrip(tmp_path) -> None:
    identity = build_experiment_cache_identity(
        candidate_model="deal",
        baseline_models=["ckplus"],
        bands=["goose"],
        windows=[{"label": "last_100", "shows": 100}],
        exclusion_window=3,
        feature_set_label="shared_core_v1",
        fresh_training=True,
    )
    cache = LocalModelTestCache(
        cache_dir=build_default_cache_dir(identity=identity, cache_root=tmp_path),
        experiment_identity=identity,
    )

    record = {
        "band": "goose",
        "model_slug": "deal",
        "model_version": "deal_v2",
        "show_id": "goose-show-3",
        "target_show_date": "2024-01-20",
        "reference_date": "2024-01-19",
        "actual_songs": ["Song A", "Song G", "Song H"],
        "actual_song_count": 3,
        "predictions": [{"rank": 1, "song_name": "Song A"}],
        "prediction_count": 1,
        "generated_at": "2026-04-09T00:00:00+00:00",
        "metrics": {"k10": {"hit": 1}},
    }

    cache.write_scored_run(record)
    loaded = cache.load_scored_run(
        band="goose",
        model_slug="deal",
        reference_date="2024-01-19",
        target_show_id="goose-show-3",
    )

    assert loaded == record
    assert cache.build_summary()["record_count"] == 1
