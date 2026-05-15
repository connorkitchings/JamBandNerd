"""Evaluate offline Goose GBM + Notebook rank blends.

This script is Phase B evidence tooling only. It does not register, promote, or
persist a model. For each target show it trains the requested GBM predictor,
scores that predictor's candidate universe, adds a Notebook-style rank score
from the same pre-target history, and grid-searches rank blends.

Usage:
    uv run python scripts/evaluate_goose_notebook_blend.py \\
        --band goose \\
        --base-predictor jambandnerd.models.goose.model.GooseGbmV2Predictor \\
        --shows 50 \\
        --snapshot-root .snapshots/goose_phase_b \\
        --out-dir .snapshots/goose_phase_b/blends
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Type

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.config.bands import get_excluded_songs
from jambandnerd.models.accuracy import (
    aggregate_metrics,
    compute_per_show_metrics,
    compute_weighted_precision_score,
    dual_f1_objective_score_for_band,
    dual_objective_score_for_band,
)
from jambandnerd.models.base import PredictionModel
from jambandnerd.models.evaluation import (
    get_evaluation_reference_date,
    list_completed_shows,
    select_target_shows,
)
from jambandnerd.models.gbm.predictor import BandGbmPredictor
from jambandnerd.transformations.gaps import ModelData, generate_model_data
from scripts.common import fetch_table, prepare_band_data


@dataclass(frozen=True)
class AggregateScore:
    p10: float
    p25: float
    p50: float
    r10: float
    r25: float
    r50: float
    f1_10: float
    f1_25: float
    f1_50: float
    weighted_score: float
    dual_score: float
    dual_f1_score: float
    avg_actual_song_count: float
    avg_p25_ceiling: float
    n_shows: int


@dataclass(frozen=True)
class AlphaResult:
    alpha: float
    metrics: AggregateScore
    delta_vs_notebook: dict[str, float]
    delta_vs_base: dict[str, float]


@dataclass(frozen=True)
class ShowComparison:
    show_id: str
    target_show_date: str
    alpha: float
    notebook_top10_matches: int
    blend_top10_matches: int
    notebook_only_hits: list[str]
    blend_only_hits: list[str]
    notebook_misses_in_blend: list[str]
    blend_misses_in_notebook: list[str]


BLEND_CACHE_SCHEMA_VERSION = 1
BLEND_SELECTION_VERSION = "f1_guarded_v1"
BLEND_CACHE_CANDIDATE_COLUMNS = [
    "song_name",
    "gbm_raw_score",
    "gbm_rank_score",
    "notebook_rank_score",
]

_WORKER_BAND: str | None = None
_WORKER_PREDICTOR_CLASS: Type[PredictionModel] | None = None
_WORKER_SHOWS_DF: pd.DataFrame | None = None
_WORKER_SETS_DF: pd.DataFrame | None = None


@dataclass(frozen=True)
class BlendCacheConfig:
    enabled: bool
    cache_dir: Path | None
    force_rebuild: bool


@dataclass
class BlendCacheStats:
    enabled: bool
    cache_dir: str | None
    force_rebuild: bool
    hits: int = 0
    misses: int = 0
    writes: int = 0


@dataclass(frozen=True)
class ScoringTask:
    index: int
    show_row: dict[str, Any]
    cache_path: Path | None


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(value: Any, *, length: int = 16) -> str:
    return hashlib.sha256(_stable_json_dumps(value).encode("utf-8")).hexdigest()[
        :length
    ]


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temp_path.replace(path)


def _load_snapshot_manifest(snapshot_root: str | None) -> dict[str, Any] | None:
    if not snapshot_root:
        return None
    manifest_path = Path(snapshot_root) / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text())


def _target_show_identity(target_shows: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for _, row in target_shows.iterrows():
        show_date = row.get("show_date")
        if isinstance(show_date, date):
            show_date_value = show_date.isoformat()
        else:
            show_date_value = str(show_date)
        rows.append(
            {
                "show_id": str(row.get("show_id")),
                "show_date": show_date_value,
            }
        )
    return rows


def _build_blend_cache_identity(
    *,
    band: str,
    predictor_path: str,
    model_version: str,
    feature_columns: list[str],
    shows: int,
    target_shows: pd.DataFrame,
    snapshot_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": BLEND_CACHE_SCHEMA_VERSION,
        "selection_version": BLEND_SELECTION_VERSION,
        "band": band,
        "predictor_path": predictor_path,
        "model_version": model_version,
        "feature_columns": list(feature_columns),
        "shows": shows,
        "target_shows": _target_show_identity(target_shows),
        "snapshot_manifest": snapshot_manifest,
    }


def _build_blend_cache_dir(
    *,
    out_dir: Path,
    cache_dir: Path | None,
    band: str,
    model_version: str,
    cache_key: str,
) -> Path:
    if cache_dir is not None:
        return cache_dir
    return out_dir / ".cache" / f"{band}_{model_version}_{cache_key}"


def _cache_record_path(
    *,
    cache_dir: Path,
    show_id: str,
    target_show_date: str,
) -> Path:
    suffix = _stable_hash(
        {"show_id": show_id, "target_show_date": target_show_date},
        length=12,
    )
    return cache_dir / "shows" / f"{target_show_date}__{suffix}.json"


def _serialize_scored_show(show: dict[str, Any]) -> dict[str, Any]:
    candidates = show["candidates"]
    candidate_rows = candidates[BLEND_CACHE_CANDIDATE_COLUMNS].to_dict(orient="records")
    return {
        "schema_version": BLEND_CACHE_SCHEMA_VERSION,
        "show_id": str(show["show_id"]),
        "target_show_date": str(show["target_show_date"]),
        "reference_date": str(show.get("reference_date", "")),
        "actual_songs": [str(song) for song in show["actual_songs"]],
        "notebook_songs": [str(song) for song in show["notebook_songs"]],
        "candidates": candidate_rows,
    }


def _deserialize_scored_show(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != BLEND_CACHE_SCHEMA_VERSION:
        raise ValueError("Blend cache schema version mismatch.")
    candidates = pd.DataFrame(payload.get("candidates", []))
    missing = [
        column for column in BLEND_CACHE_CANDIDATE_COLUMNS if column not in candidates
    ]
    if missing:
        raise ValueError(f"Blend cache candidate columns missing: {missing}")
    return {
        "show_id": str(payload["show_id"]),
        "target_show_date": str(payload["target_show_date"]),
        "reference_date": str(payload.get("reference_date", "")),
        "actual_songs": [str(song) for song in payload.get("actual_songs", [])],
        "notebook_songs": [str(song) for song in payload.get("notebook_songs", [])],
        "candidates": candidates[BLEND_CACHE_CANDIDATE_COLUMNS],
    }


def _load_cached_scored_show(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    return _deserialize_scored_show(json.loads(cache_path.read_text()))


def _write_cached_scored_show(cache_path: Path, scored_show: dict[str, Any]) -> None:
    _write_json_atomic(cache_path, _serialize_scored_show(scored_show))


def _load_predictor_class(dotted_path: str) -> Type[PredictionModel]:
    if ":" in dotted_path:
        module_path, class_name = dotted_path.rsplit(":", 1)
    else:
        module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, PredictionModel)):
        raise TypeError(f"{dotted_path} must be a PredictionModel subclass")
    if not issubclass(cls, BandGbmPredictor):
        raise TypeError(f"{dotted_path} must be a BandGbmPredictor subclass")
    return cls


def _rank_scores(song_names: list[str]) -> dict[str, float]:
    """Map ordered songs to [1.0, 0.0] rank scores, preserving first occurrence."""
    ordered = list(dict.fromkeys(str(name) for name in song_names))
    if not ordered:
        return {}
    if len(ordered) == 1:
        return {ordered[0]: 1.0}
    denominator = len(ordered) - 1
    return {
        song_name: 1.0 - (rank / denominator) for rank, song_name in enumerate(ordered)
    }


def _notebook_ranked_songs(model_data: ModelData, *, band: str) -> list[str]:
    """Return Notebook-style full candidate ranking for the supplied history."""
    features = model_data.master_feature_set
    plays = model_data.historical_plays
    if features.empty or plays.empty:
        return []

    features = features.copy()
    plays = plays.copy()
    features["last_played_date"] = pd.to_datetime(
        features["last_played_date"], errors="coerce"
    )
    plays["show_date"] = pd.to_datetime(plays["show_date"], errors="coerce")

    last_completed_show_date = features["last_played_date"].max()
    if pd.isna(last_completed_show_date):
        return []
    window_start = last_completed_show_date - timedelta(days=365)
    plays_in_window = plays[plays["show_date"] >= window_start]
    plays_past_year_count = (
        plays_in_window.groupby("song_name")["show_index"]
        .nunique()
        .rename("plays_past_year")
    )

    candidates = features.merge(plays_past_year_count, on="song_name", how="inner")
    if candidates.empty:
        return []

    candidates["current_gap"] = (
        model_data.reference_index - candidates["last_played_index"] - 1
    ).clip(lower=0)
    candidates = candidates[
        ~candidates["song_name"].isin(set(model_data.recently_played_songs))
    ]
    excluded = get_excluded_songs(band)
    if excluded:
        candidates = candidates[
            ~candidates["song_name"].str.lower().str.strip().isin(excluded)
        ]
    if candidates.empty:
        return []

    ranked = candidates.sort_values(
        by=["plays_past_year", "current_gap", "song_name"],
        ascending=[False, False, True],
    )
    return ranked["song_name"].astype(str).tolist()


def _rank_blended_candidates(candidates: pd.DataFrame, *, alpha: float) -> list[str]:
    ranked = candidates.copy()
    ranked["blend_score"] = (
        alpha * ranked["gbm_rank_score"] + (1.0 - alpha) * ranked["notebook_rank_score"]
    )
    ranked = ranked.sort_values(
        by=["blend_score", "gbm_rank_score", "notebook_rank_score", "song_name"],
        ascending=[False, False, False, True],
    )
    return ranked["song_name"].astype(str).tolist()


def _aggregate_prediction_metrics(
    prediction_records: list[dict[str, Any]],
    *,
    band: str,
) -> AggregateScore:
    if not prediction_records:
        return AggregateScore(
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0,
        )

    agg = {}
    for k in [10, 25, 50]:
        per_show = [
            compute_per_show_metrics(record["pred_songs"], record["actual_songs"], k)
            for record in prediction_records
        ]
        agg[k] = aggregate_metrics(per_show, k)

    weighted = compute_weighted_precision_score(
        agg[10].precision,
        agg[25].precision,
        agg[50].precision,
    )
    dual = dual_objective_score_for_band(agg[10].precision, agg[50].recall, band)
    dual_f1 = dual_f1_objective_score_for_band(agg[10].f1, agg[50].f1, band)
    actual_counts = [len(set(record["actual_songs"])) for record in prediction_records]
    avg_actual_song_count = sum(actual_counts) / len(actual_counts)
    avg_p25_ceiling = sum(min(count, 25) / 25 for count in actual_counts) / len(
        actual_counts
    )
    return AggregateScore(
        p10=agg[10].precision,
        p25=agg[25].precision,
        p50=agg[50].precision,
        r10=agg[10].recall,
        r25=agg[25].recall,
        r50=agg[50].recall,
        f1_10=agg[10].f1,
        f1_25=agg[25].f1,
        f1_50=agg[50].f1,
        weighted_score=weighted,
        dual_score=dual,
        dual_f1_score=dual_f1,
        avg_actual_song_count=avg_actual_song_count,
        avg_p25_ceiling=avg_p25_ceiling,
        n_shows=len(prediction_records),
    )


def _metric_deltas(left: AggregateScore, right: AggregateScore) -> dict[str, float]:
    return {
        "p10": left.p10 - right.p10,
        "p25": left.p25 - right.p25,
        "f1_25": left.f1_25 - right.f1_25,
        "r50": left.r50 - right.r50,
        "weighted_score": left.weighted_score - right.weighted_score,
        "dual_score": left.dual_score - right.dual_score,
        "dual_f1_score": left.dual_f1_score - right.dual_f1_score,
    }


def _select_best_alpha(
    results: list[AlphaResult],
    *,
    notebook_p10: float,
    notebook_p25: float,
    p10_floor_delta: float = -0.005,
    p25_floor_delta: float = -0.005,
) -> dict[str, AlphaResult | None]:
    if not results:
        return {
            "best_dual_f1_guarded": None,
            "best_dual": None,
            "best_p10": None,
            "best_floor_r50": None,
        }

    best_dual = max(
        results,
        key=lambda result: (
            result.metrics.dual_score,
            result.metrics.p10,
            result.metrics.r50,
            -result.alpha,
        ),
    )
    best_p10 = max(
        results,
        key=lambda result: (
            result.metrics.p10,
            result.metrics.dual_score,
            result.metrics.r50,
            -result.alpha,
        ),
    )
    floor = notebook_p10 + p10_floor_delta
    eligible = [result for result in results if result.metrics.p10 >= floor]
    f1_floor_p10 = notebook_p10 + p10_floor_delta
    f1_floor_p25 = notebook_p25 + p25_floor_delta
    f1_eligible = [
        result
        for result in results
        if result.metrics.p10 >= f1_floor_p10 and result.metrics.p25 >= f1_floor_p25
    ]
    best_dual_f1_guarded = (
        max(
            f1_eligible,
            key=lambda result: (
                result.metrics.dual_f1_score,
                result.metrics.f1_25,
                result.metrics.p10,
                -result.alpha,
            ),
        )
        if f1_eligible
        else None
    )
    best_floor_r50 = (
        max(
            eligible,
            key=lambda result: (
                result.metrics.r50,
                result.metrics.dual_score,
                result.metrics.p10,
                -result.alpha,
            ),
        )
        if eligible
        else None
    )
    return {
        "best_dual_f1_guarded": best_dual_f1_guarded,
        "best_dual": best_dual,
        "best_p10": best_p10,
        "best_floor_r50": best_floor_r50,
    }


def _score_target_show(
    *,
    band: str,
    predictor_class: Type[PredictionModel],
    shows_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    show_row: pd.Series,
) -> dict[str, Any] | None:
    ref_date = show_row["show_date"]
    if not isinstance(ref_date, date):
        ref_date = pd.Timestamp(ref_date).date()
    show_id = str(show_row["show_id"])
    actual_songs = (
        sets_df.loc[sets_df["show_id"] == show_id, "song_name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    if len(actual_songs) <= 2:
        return None

    prediction_date = get_evaluation_reference_date(ref_date)
    model_data = generate_model_data(
        shows_df,
        sets_df,
        prediction_date,
        band=band,
        target_show_context=show_row,
    )

    predictor = predictor_class(band=band, persist_artifacts=False)
    predictor.train(model_data)
    if not isinstance(predictor, BandGbmPredictor) or predictor._booster is None:
        return None

    candidates = predictor._get_candidate_features(model_data)
    if candidates.empty:
        return None
    candidates = candidates.copy()
    excluded = get_excluded_songs(band)
    if excluded:
        candidates = candidates[
            ~candidates["song_name"].str.lower().str.strip().isin(excluded)
        ]
    if candidates.empty:
        return None

    X = candidates[predictor.feature_columns].fillna(0.0).to_numpy(dtype=float)
    candidates["gbm_raw_score"] = predictor._booster.predict(X)
    gbm_ranked = candidates.sort_values(
        by=["gbm_raw_score", "song_name"],
        ascending=[False, True],
    )
    candidates["gbm_rank_score"] = (
        candidates["song_name"]
        .astype(str)
        .map(_rank_scores(gbm_ranked["song_name"].astype(str).tolist()))
    ).fillna(0.0)

    notebook_ranked = _notebook_ranked_songs(model_data, band=band)
    notebook_scores = _rank_scores(notebook_ranked)
    candidates["notebook_rank_score"] = (
        candidates["song_name"].astype(str).map(notebook_scores)
    ).fillna(0.0)

    return {
        "show_id": show_id,
        "target_show_date": ref_date.isoformat(),
        "reference_date": prediction_date.isoformat(),
        "actual_songs": actual_songs,
        "notebook_songs": notebook_ranked[:50],
        "candidates": candidates,
    }


def _init_score_worker(
    band: str,
    predictor_path: str,
    shows_records: list[dict[str, Any]],
    setlist_records: list[dict[str, Any]],
) -> None:
    global _WORKER_BAND
    global _WORKER_PREDICTOR_CLASS
    global _WORKER_SHOWS_DF
    global _WORKER_SETS_DF

    _WORKER_BAND = band
    _WORKER_PREDICTOR_CLASS = _load_predictor_class(predictor_path)
    _WORKER_SHOWS_DF = pd.DataFrame(shows_records)
    _WORKER_SETS_DF = pd.DataFrame(setlist_records)


def _score_target_show_worker(task: ScoringTask) -> tuple[int, dict[str, Any] | None]:
    if (
        _WORKER_BAND is None
        or _WORKER_PREDICTOR_CLASS is None
        or _WORKER_SHOWS_DF is None
        or _WORKER_SETS_DF is None
    ):
        raise RuntimeError("Score worker was not initialized.")
    scored = _score_target_show(
        band=_WORKER_BAND,
        predictor_class=_WORKER_PREDICTOR_CLASS,
        shows_df=_WORKER_SHOWS_DF,
        sets_df=_WORKER_SETS_DF,
        show_row=pd.Series(task.show_row),
    )
    return task.index, scored


def _score_uncached_tasks_serial(
    *,
    band: str,
    predictor_class: Type[PredictionModel],
    shows_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    tasks: list[ScoringTask],
    scored_shows_by_index: dict[int, dict[str, Any]],
    total: int,
    cache_stats: BlendCacheStats,
) -> None:
    for task in tasks:
        ref_date = task.show_row["show_date"]
        print(
            f"  [{task.index + 1}/{total}] {ref_date} "
            f"(show_id={task.show_row['show_id']})",
            end="\r",
            flush=True,
        )
        scored = _score_target_show(
            band=band,
            predictor_class=predictor_class,
            shows_df=shows_df,
            sets_df=sets_df,
            show_row=pd.Series(task.show_row),
        )
        if scored is None:
            continue
        scored_shows_by_index[task.index] = scored
        if task.cache_path is not None:
            _write_cached_scored_show(task.cache_path, scored)
            cache_stats.writes += 1


def _score_uncached_tasks_parallel(
    *,
    band: str,
    predictor_path: str,
    shows_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    tasks: list[ScoringTask],
    scored_shows_by_index: dict[int, dict[str, Any]],
    total: int,
    jobs: int,
    cache_stats: BlendCacheStats,
) -> None:
    with ProcessPoolExecutor(
        max_workers=jobs,
        initializer=_init_score_worker,
        initargs=(
            band,
            predictor_path,
            shows_df.to_dict(orient="records"),
            sets_df.to_dict(orient="records"),
        ),
    ) as executor:
        futures = {
            executor.submit(_score_target_show_worker, task): task for task in tasks
        }
        completed = 0
        for future in as_completed(futures):
            task = futures[future]
            completed += 1
            print(
                f"  [{completed}/{len(tasks)} cold tasks] {task.show_row['show_date']} "
                f"(show_id={task.show_row['show_id']}, window_index={task.index + 1}/{total})",
                end="\r",
                flush=True,
            )
            index, scored = future.result()
            if scored is None:
                continue
            scored_shows_by_index[index] = scored
            if task.cache_path is not None:
                _write_cached_scored_show(task.cache_path, scored)
                cache_stats.writes += 1


def _score_target_shows_with_cache(
    *,
    band: str,
    predictor_path: str,
    predictor_class: Type[PredictionModel],
    shows_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    target_shows: pd.DataFrame,
    cache_config: BlendCacheConfig,
    jobs: int,
) -> tuple[list[dict[str, Any]], BlendCacheStats]:
    total = len(target_shows)
    cache_stats = BlendCacheStats(
        enabled=cache_config.enabled,
        cache_dir=str(cache_config.cache_dir) if cache_config.cache_dir else None,
        force_rebuild=cache_config.force_rebuild,
    )
    scored_shows_by_index: dict[int, dict[str, Any]] = {}
    uncached_tasks: list[ScoringTask] = []

    for index, (_, show_row) in enumerate(target_shows.iterrows()):
        row_dict = show_row.to_dict()
        show_date = row_dict.get("show_date")
        target_show_date = (
            show_date.isoformat() if isinstance(show_date, date) else str(show_date)
        )
        cache_path = (
            _cache_record_path(
                cache_dir=cache_config.cache_dir,
                show_id=str(row_dict.get("show_id")),
                target_show_date=target_show_date,
            )
            if cache_config.enabled and cache_config.cache_dir is not None
            else None
        )

        cached = None
        if cache_path is not None and not cache_config.force_rebuild:
            cached = _load_cached_scored_show(cache_path)
        if cached is not None:
            cache_stats.hits += 1
            scored_shows_by_index[index] = cached
            continue

        if cache_config.enabled:
            cache_stats.misses += 1
        uncached_tasks.append(
            ScoringTask(
                index=index,
                show_row=row_dict,
                cache_path=cache_path,
            )
        )

    if uncached_tasks:
        if jobs == 1:
            _score_uncached_tasks_serial(
                band=band,
                predictor_class=predictor_class,
                shows_df=shows_df,
                sets_df=sets_df,
                tasks=uncached_tasks,
                scored_shows_by_index=scored_shows_by_index,
                total=total,
                cache_stats=cache_stats,
            )
        else:
            _score_uncached_tasks_parallel(
                band=band,
                predictor_path=predictor_path,
                shows_df=shows_df,
                sets_df=sets_df,
                tasks=uncached_tasks,
                scored_shows_by_index=scored_shows_by_index,
                total=total,
                jobs=jobs,
                cache_stats=cache_stats,
            )

    print()
    scored_shows = _ordered_scored_shows(scored_shows_by_index)
    return scored_shows, cache_stats


def _ordered_scored_shows(
    scored_shows_by_index: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [scored_shows_by_index[index] for index in sorted(scored_shows_by_index)]


def _show_comparisons(
    *,
    scored_shows: list[dict[str, Any]],
    alpha: float,
    limit: int = 12,
) -> list[ShowComparison]:
    comparisons: list[ShowComparison] = []
    for show in scored_shows:
        actual = set(show["actual_songs"])
        notebook_top10 = show["notebook_songs"][:10]
        blend_top10 = _rank_blended_candidates(show["candidates"], alpha=alpha)[:10]
        notebook_hits = [song for song in notebook_top10 if song in actual]
        blend_hits = [song for song in blend_top10 if song in actual]
        comparisons.append(
            ShowComparison(
                show_id=show["show_id"],
                target_show_date=show["target_show_date"],
                alpha=alpha,
                notebook_top10_matches=len(notebook_hits),
                blend_top10_matches=len(blend_hits),
                notebook_only_hits=[
                    song for song in notebook_hits if song not in set(blend_hits)
                ],
                blend_only_hits=[
                    song for song in blend_hits if song not in set(notebook_hits)
                ],
                notebook_misses_in_blend=[
                    song for song in notebook_hits if song not in set(blend_top10)
                ],
                blend_misses_in_notebook=[
                    song for song in blend_hits if song not in set(notebook_top10)
                ],
            )
        )

    comparisons.sort(
        key=lambda row: (
            abs(row.blend_top10_matches - row.notebook_top10_matches),
            max(row.blend_top10_matches, row.notebook_top10_matches),
            row.target_show_date,
        ),
        reverse=True,
    )
    return comparisons[:limit]


def _render_markdown(
    *,
    band: str,
    predictor_path: str,
    model_version: str,
    shows: int,
    run_metadata: dict[str, Any],
    notebook_metrics: AggregateScore,
    base_metrics: AggregateScore,
    alpha_results: list[AlphaResult],
    selections: dict[str, AlphaResult | None],
    comparisons: list[ShowComparison],
) -> str:
    lines: list[str] = []
    lines.append(f"# Goose Notebook Blend — `{model_version}`")
    lines.append("")
    lines.append(f"- predictor: `{predictor_path}`")
    lines.append(f"- band: `{band}`")
    lines.append(f"- shows analyzed: {shows}")
    lines.append(f"- scored shows: {base_metrics.n_shows}")
    lines.append(f"- avg actual songs: {base_metrics.avg_actual_song_count:.2f}")
    lines.append(f"- avg p@25 ceiling: {base_metrics.avg_p25_ceiling:.3f}")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append("| setting | value |")
    lines.append("| --- | --- |")
    for key, value in run_metadata.items():
        lines.append(f"| {key} | `{value}` |")
    lines.append("")
    lines.append("## Baselines")
    lines.append("")
    lines.append("| model | p@10 | p@25 | F1@25 | r@50 | weighted_p | dual | dual_f1 |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    lines.append(
        "| Notebook | "
        f"{notebook_metrics.p10:.3f} | {notebook_metrics.p25:.3f} | "
        f"{notebook_metrics.f1_25:.3f} | "
        f"{notebook_metrics.r50:.3f} | {notebook_metrics.weighted_score:.3f} | "
        f"{notebook_metrics.dual_score:.3f} | "
        f"{notebook_metrics.dual_f1_score:.3f} |"
    )
    lines.append(
        "| Base alpha=1.00 | "
        f"{base_metrics.p10:.3f} | {base_metrics.p25:.3f} | "
        f"{base_metrics.f1_25:.3f} | "
        f"{base_metrics.r50:.3f} | {base_metrics.weighted_score:.3f} | "
        f"{base_metrics.dual_score:.3f} | "
        f"{base_metrics.dual_f1_score:.3f} |"
    )
    lines.append("")
    lines.append("## Best Alphas")
    lines.append("")
    lines.append(
        "| selector | alpha | p@10 | p@25 | F1@25 | r@50 | dual | dual_f1 | Δdual_f1 vs Notebook |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for label, result in selections.items():
        if result is None:
            lines.append(f"| {label} | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        lines.append(
            f"| {label} | {result.alpha:.2f} | {result.metrics.p10:.3f} | "
            f"{result.metrics.p25:.3f} | {result.metrics.f1_25:.3f} | "
            f"{result.metrics.r50:.3f} | {result.metrics.dual_score:.3f} | "
            f"{result.metrics.dual_f1_score:.3f} | "
            f"{result.delta_vs_notebook['dual_f1_score']:+.3f} |"
        )
    lines.append("")
    lines.append("## Alpha Grid")
    lines.append("")
    lines.append(
        "| alpha | p@10 | p@25 | F1@25 | r@50 | weighted_p | dual | dual_f1 | Δp@10 N | Δp@25 N | ΔF1@25 N | Δr@50 N | Δdual_f1 N |"
    )
    lines.append(
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for result in alpha_results:
        lines.append(
            f"| {result.alpha:.2f} | {result.metrics.p10:.3f} | "
            f"{result.metrics.p25:.3f} | {result.metrics.f1_25:.3f} | "
            f"{result.metrics.r50:.3f} | "
            f"{result.metrics.weighted_score:.3f} | {result.metrics.dual_score:.3f} | "
            f"{result.metrics.dual_f1_score:.3f} | "
            f"{result.delta_vs_notebook['p10']:+.3f} | "
            f"{result.delta_vs_notebook['p25']:+.3f} | "
            f"{result.delta_vs_notebook['f1_25']:+.3f} | "
            f"{result.delta_vs_notebook['r50']:+.3f} | "
            f"{result.delta_vs_notebook['dual_f1_score']:+.3f} |"
        )
    lines.append("")
    lines.append("## Top-10 Swing Rows")
    lines.append("")
    lines.append(
        "| date | show_id | Notebook hits | blend hits | Notebook-only hits | blend-only hits |"
    )
    lines.append("| --- | --- | ---: | ---: | --- | --- |")
    for row in comparisons:
        lines.append(
            f"| {row.target_show_date} | {row.show_id} | "
            f"{row.notebook_top10_matches} | {row.blend_top10_matches} | "
            f"{', '.join(row.notebook_only_hits) or '-'} | "
            f"{', '.join(row.blend_only_hits) or '-'} |"
        )
    lines.append("")
    return "\n".join(lines)


def evaluate_blend(
    *,
    band: str,
    predictor_path: str,
    shows: int,
    snapshot_root: str | None,
    out_dir: Path,
    alpha_step: float,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    force_rebuild_cache: bool = False,
    jobs: int = 1,
) -> tuple[Path, Path]:
    if jobs < 1:
        raise ValueError("jobs must be >= 1.")
    predictor_class = _load_predictor_class(predictor_path)

    if snapshot_root:
        shows_rows = fetch_table(f"{band}_shows_raw", snapshot_root=snapshot_root)
        setlist_rows = fetch_table(f"{band}_setlists_raw", snapshot_root=snapshot_root)
    else:
        shows_rows = fetch_table(f"{band}_shows_raw")
        setlist_rows = fetch_table(f"{band}_setlists_raw")

    shows_df = pd.DataFrame(shows_rows)
    sets_df = pd.DataFrame(setlist_rows)
    if shows_df.empty or sets_df.empty:
        raise RuntimeError(f"No data found for band '{band}'.")

    shows_df, sets_df = prepare_band_data(shows_df, sets_df, band=band)
    completed = list_completed_shows(shows_df, sets_df)
    target_shows = select_target_shows(completed, shows=shows)
    if target_shows.empty:
        raise RuntimeError(f"No completed shows found for band '{band}'.")

    probe = predictor_class(band=band, persist_artifacts=False)
    model_version: str = getattr(probe, "MODEL_VERSION", "unknown")
    feature_columns = list(getattr(probe, "feature_columns", []))
    snapshot_manifest = _load_snapshot_manifest(snapshot_root)
    cache_identity = _build_blend_cache_identity(
        band=band,
        predictor_path=predictor_path,
        model_version=model_version,
        feature_columns=feature_columns,
        shows=shows,
        target_shows=target_shows,
        snapshot_manifest=snapshot_manifest,
    )
    cache_key = _stable_hash(cache_identity)
    resolved_cache_dir = _build_blend_cache_dir(
        out_dir=out_dir,
        cache_dir=cache_dir,
        band=band,
        model_version=model_version,
        cache_key=cache_key,
    )
    cache_config = BlendCacheConfig(
        enabled=use_cache,
        cache_dir=resolved_cache_dir if use_cache else None,
        force_rebuild=force_rebuild_cache,
    )
    if use_cache:
        _write_json_atomic(
            resolved_cache_dir / "manifest.json",
            {
                "cache_key": cache_key,
                "cache_identity": cache_identity,
            },
        )

    total = len(target_shows)
    print(
        f"[{band.upper()}/{model_version}] Evaluating Notebook blends for "
        f"{total} shows ({target_shows['show_date'].min()} - "
        f"{target_shows['show_date'].max()})"
    )

    scored_shows, cache_stats = _score_target_shows_with_cache(
        band=band,
        predictor_path=predictor_path,
        predictor_class=predictor_class,
        shows_df=shows_df,
        sets_df=sets_df,
        target_shows=target_shows,
        cache_config=cache_config,
        jobs=jobs,
    )
    if not scored_shows:
        raise RuntimeError("No shows scored; check predictor and snapshot inputs.")

    notebook_records = [
        {
            "pred_songs": show["notebook_songs"][:50],
            "actual_songs": show["actual_songs"],
        }
        for show in scored_shows
    ]
    notebook_metrics = _aggregate_prediction_metrics(notebook_records, band=band)

    alphas = [
        round(i * alpha_step, 10) for i in range(int(round(1.0 / alpha_step)) + 1)
    ]
    alpha_results: list[AlphaResult] = []
    base_metrics = None
    for alpha in alphas:
        prediction_records = []
        for show in scored_shows:
            pred_songs = _rank_blended_candidates(show["candidates"], alpha=alpha)[:50]
            prediction_records.append(
                {"pred_songs": pred_songs, "actual_songs": show["actual_songs"]}
            )
        metrics = _aggregate_prediction_metrics(prediction_records, band=band)
        if alpha == 1.0:
            base_metrics = metrics
        alpha_results.append(
            AlphaResult(
                alpha=alpha,
                metrics=metrics,
                delta_vs_notebook=_metric_deltas(metrics, notebook_metrics),
                delta_vs_base={},
            )
        )

    if base_metrics is None:
        raise RuntimeError("Alpha grid must include alpha=1.00.")

    alpha_results = [
        AlphaResult(
            alpha=result.alpha,
            metrics=result.metrics,
            delta_vs_notebook=result.delta_vs_notebook,
            delta_vs_base=_metric_deltas(result.metrics, base_metrics),
        )
        for result in alpha_results
    ]
    selections = _select_best_alpha(
        alpha_results,
        notebook_p10=notebook_metrics.p10,
        notebook_p25=notebook_metrics.p25,
    )
    comparison_alpha = (
        selections["best_dual_f1_guarded"].alpha
        if selections["best_dual_f1_guarded"] is not None
        else 1.0
    )
    comparisons = _show_comparisons(
        scored_shows=scored_shows,
        alpha=comparison_alpha,
    )
    run_metadata = {
        "cache_enabled": cache_stats.enabled,
        "cache_dir": cache_stats.cache_dir,
        "cache_key": cache_key if use_cache else None,
        "cache_hits": cache_stats.hits,
        "cache_misses": cache_stats.misses,
        "cache_writes": cache_stats.writes,
        "force_rebuild_cache": cache_stats.force_rebuild,
        "jobs": jobs,
    }

    payload = {
        "band": band,
        "model_version": model_version,
        "predictor": predictor_path,
        "shows_requested": shows,
        "shows_scored": len(scored_shows),
        "run_metadata": run_metadata,
        "selection_criteria": {
            "primary": "max dual_f1_score",
            "constraints": {
                "p10_min_vs_notebook": -0.005,
                "p25_min_vs_notebook": -0.005,
            },
            "tie_breakers": ["f1_25", "p10", "lower_alpha"],
        },
        "notebook_metrics": dataclasses.asdict(notebook_metrics),
        "base_metrics": dataclasses.asdict(base_metrics),
        "alpha_results": [
            {
                "alpha": result.alpha,
                "metrics": dataclasses.asdict(result.metrics),
                "delta_vs_notebook": result.delta_vs_notebook,
                "delta_vs_base": result.delta_vs_base,
            }
            for result in alpha_results
        ],
        "selections": {
            key: (
                {
                    "alpha": value.alpha,
                    "metrics": dataclasses.asdict(value.metrics),
                    "delta_vs_notebook": value.delta_vs_notebook,
                    "delta_vs_base": value.delta_vs_base,
                }
                if value is not None
                else None
            )
            for key, value in selections.items()
        },
        "top10_swing_rows": [dataclasses.asdict(row) for row in comparisons],
    }
    markdown = _render_markdown(
        band=band,
        predictor_path=predictor_path,
        model_version=model_version,
        shows=shows,
        run_metadata=run_metadata,
        notebook_metrics=notebook_metrics,
        base_metrics=base_metrics,
        alpha_results=alpha_results,
        selections=selections,
        comparisons=comparisons,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{band}_{model_version}_notebook_blend_{shows}shows"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(payload, indent=2))
    md_path.write_text(markdown)
    print(f"Wrote blend JSON to {json_path}")
    print(f"Wrote blend report to {md_path}")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--band", default="goose")
    parser.add_argument(
        "--base-predictor",
        default="jambandnerd.models.goose.model.GooseGbmV2Predictor",
        help="Dotted path to a BandGbmPredictor subclass.",
    )
    parser.add_argument("--shows", type=int, default=50)
    parser.add_argument(
        "--snapshot-root",
        default=".snapshots/goose_phase_b",
        help="Local snapshot root (set to empty string to use Supabase).",
    )
    parser.add_argument(
        "--out-dir",
        default=".snapshots/goose_phase_b/blends",
        help="Directory for markdown and JSON reports.",
    )
    parser.add_argument(
        "--alpha-step",
        type=float,
        default=0.05,
        help="Blend grid step. Must divide 1.0 evenly.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Override the blend-show cache directory.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable blend-show cache reads and writes.",
    )
    parser.add_argument(
        "--force-rebuild-cache",
        action="store_true",
        help="Ignore existing blend-show cache records and rewrite them.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of independent target shows to score in parallel.",
    )
    args = parser.parse_args()

    if args.alpha_step <= 0 or args.alpha_step > 1:
        raise ValueError("--alpha-step must be in (0, 1].")
    if args.jobs < 1:
        raise ValueError("--jobs must be >= 1.")
    grid_size = 1.0 / args.alpha_step
    if abs(grid_size - round(grid_size)) > 1e-9:
        raise ValueError("--alpha-step must divide 1.0 evenly.")

    evaluate_blend(
        band=args.band,
        predictor_path=args.base_predictor,
        shows=args.shows,
        snapshot_root=args.snapshot_root or None,
        out_dir=Path(args.out_dir),
        alpha_step=args.alpha_step,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        force_rebuild_cache=args.force_rebuild_cache,
        jobs=args.jobs,
    )


if __name__ == "__main__":
    main()
