"""Evaluate offline Goose GBM + Notebook rank blends.

This script is Phase B evidence tooling only. It does not register, promote, or
persist a model. For each target show it trains the requested GBM predictor,
scores that predictor's candidate universe, adds a Notebook-style rank score
from the same pre-target history, and grid-searches rank blends.

Usage:
    uv run python scripts/evaluate_goose_notebook_blend.py \\
        --band goose \\
        --base-predictor jambandnerd.models.goose.model.GooseGbmTop10V3Predictor \\
        --shows 50 \\
        --snapshot-root .snapshots/goose_phase_b \\
        --out-dir .snapshots/goose_phase_b/blends
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import os
import sys
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
    weighted_score: float
    dual_score: float
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
        return AggregateScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

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
    return AggregateScore(
        p10=agg[10].precision,
        p25=agg[25].precision,
        p50=agg[50].precision,
        r10=agg[10].recall,
        r25=agg[25].recall,
        r50=agg[50].recall,
        weighted_score=weighted,
        dual_score=dual,
        n_shows=len(prediction_records),
    )


def _metric_deltas(left: AggregateScore, right: AggregateScore) -> dict[str, float]:
    return {
        "p10": left.p10 - right.p10,
        "p25": left.p25 - right.p25,
        "r50": left.r50 - right.r50,
        "weighted_score": left.weighted_score - right.weighted_score,
        "dual_score": left.dual_score - right.dual_score,
    }


def _select_best_alpha(
    results: list[AlphaResult],
    *,
    notebook_p10: float,
    p10_floor_delta: float = -0.005,
) -> dict[str, AlphaResult | None]:
    if not results:
        return {"best_dual": None, "best_p10": None, "best_floor_r50": None}

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
        "actual_songs": actual_songs,
        "notebook_songs": notebook_ranked[:50],
        "candidates": candidates,
    }


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
    lines.append("")
    lines.append("## Baselines")
    lines.append("")
    lines.append("| model | p@10 | p@25 | r@50 | weighted_p | dual |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    lines.append(
        "| Notebook | "
        f"{notebook_metrics.p10:.3f} | {notebook_metrics.p25:.3f} | "
        f"{notebook_metrics.r50:.3f} | {notebook_metrics.weighted_score:.3f} | "
        f"{notebook_metrics.dual_score:.3f} |"
    )
    lines.append(
        "| Base alpha=1.00 | "
        f"{base_metrics.p10:.3f} | {base_metrics.p25:.3f} | "
        f"{base_metrics.r50:.3f} | {base_metrics.weighted_score:.3f} | "
        f"{base_metrics.dual_score:.3f} |"
    )
    lines.append("")
    lines.append("## Best Alphas")
    lines.append("")
    lines.append("| selector | alpha | p@10 | r@50 | dual | Δdual vs Notebook |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for label, result in selections.items():
        if result is None:
            lines.append(f"| {label} | n/a | n/a | n/a | n/a | n/a |")
            continue
        lines.append(
            f"| {label} | {result.alpha:.2f} | {result.metrics.p10:.3f} | "
            f"{result.metrics.r50:.3f} | {result.metrics.dual_score:.3f} | "
            f"{result.delta_vs_notebook['dual_score']:+.3f} |"
        )
    lines.append("")
    lines.append("## Alpha Grid")
    lines.append("")
    lines.append(
        "| alpha | p@10 | p@25 | r@50 | weighted_p | dual | Δp@10 N | Δr@50 N | Δdual N | Δdual base |"
    )
    lines.append(
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for result in alpha_results:
        lines.append(
            f"| {result.alpha:.2f} | {result.metrics.p10:.3f} | "
            f"{result.metrics.p25:.3f} | {result.metrics.r50:.3f} | "
            f"{result.metrics.weighted_score:.3f} | {result.metrics.dual_score:.3f} | "
            f"{result.delta_vs_notebook['p10']:+.3f} | "
            f"{result.delta_vs_notebook['r50']:+.3f} | "
            f"{result.delta_vs_notebook['dual_score']:+.3f} | "
            f"{result.delta_vs_base['dual_score']:+.3f} |"
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
) -> tuple[Path, Path]:
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
    total = len(target_shows)
    print(
        f"[{band.upper()}/{model_version}] Evaluating Notebook blends for "
        f"{total} shows ({target_shows['show_date'].min()} - "
        f"{target_shows['show_date'].max()})"
    )

    scored_shows: list[dict[str, Any]] = []
    for idx, (_, show_row) in enumerate(target_shows.iterrows(), start=1):
        ref_date = show_row["show_date"]
        print(
            f"  [{idx}/{total}] {ref_date} (show_id={show_row['show_id']})",
            end="\r",
            flush=True,
        )
        scored = _score_target_show(
            band=band,
            predictor_class=predictor_class,
            shows_df=shows_df,
            sets_df=sets_df,
            show_row=show_row,
        )
        if scored is not None:
            scored_shows.append(scored)
    print()
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
    selections = _select_best_alpha(alpha_results, notebook_p10=notebook_metrics.p10)
    comparison_alpha = (
        selections["best_dual"].alpha if selections["best_dual"] is not None else 1.0
    )
    comparisons = _show_comparisons(
        scored_shows=scored_shows,
        alpha=comparison_alpha,
    )

    payload = {
        "band": band,
        "model_version": model_version,
        "predictor": predictor_path,
        "shows_requested": shows,
        "shows_scored": len(scored_shows),
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
        default="jambandnerd.models.goose.model.GooseGbmTop10V3Predictor",
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
    args = parser.parse_args()

    if args.alpha_step <= 0 or args.alpha_step > 1:
        raise ValueError("--alpha-step must be in (0, 1].")
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
    )


if __name__ == "__main__":
    main()
