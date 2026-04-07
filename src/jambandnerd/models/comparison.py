"""Shared model comparison helpers."""

from __future__ import annotations

from datetime import timezone
from typing import Any, Iterable, Sequence

import pandas as pd

from jambandnerd.config import DEAL_MIN_TRAINING_SHOWS, DEAL_TRAINING_WINDOW_SHOWS
from jambandnerd.models.accuracy import aggregate_metrics, compute_per_show_metrics
from jambandnerd.models.evaluation import get_evaluation_reference_date
from jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    serialize_model_predictions,
)
from jambandnerd.transformations.gaps import generate_model_data

PRIMARY_BASELINE_SLUG = "ckplus"
PRIMARY_PROMOTION_METRIC = "recall"


def build_evaluation_predictor(
    model_slug: str,
    *,
    band: str,
    fresh_training: bool = False,
):
    """Build a predictor for comparison runs.

    Training-capable models default to in-memory training when
    ``fresh_training`` is enabled so comparisons are not influenced by stale
    on-disk artifacts.
    """

    kwargs: dict[str, Any] = {}
    definition = get_model_definition(model_slug)
    if fresh_training and definition.supports_training:
        kwargs["persist_artifacts"] = False
    return build_predictor(model_slug, band=band, **kwargs)


def extract_experiment_metadata(
    *,
    model_slug: str,
    predictor: Any,
    feature_set_label: str,
    exclusion_window: int,
    window_labels: Sequence[str],
    fresh_training: bool,
) -> dict[str, Any]:
    """Collect reproducible experiment metadata for a comparison run."""

    scalar_types = (str, int, float, bool)
    ignored_keys = {
        "band",
        "model",
        "model_path",
        "latest_training_summary",
        "persist_artifacts",
    }
    hyperparameters = {
        key: value
        for key, value in vars(predictor).items()
        if key not in ignored_keys and isinstance(value, scalar_types)
    }

    training_window: dict[str, Any] | None = None
    if model_slug == "deal":
        training_window = {
            "training_window_shows": DEAL_TRAINING_WINDOW_SHOWS,
            "min_training_shows": DEAL_MIN_TRAINING_SHOWS,
        }

    return {
        "model_slug": model_slug,
        "model_version": get_model_definition(model_slug).version,
        "feature_set_label": feature_set_label,
        "hyperparameters": hyperparameters,
        "training_window": training_window,
        "exclusion_window": exclusion_window,
        "evaluation_windows": list(window_labels),
        "fresh_training": fresh_training,
        "generated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
    }


def maybe_build_model_diagnostics(
    *,
    band: str,
    model_slug: str,
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date,
    exclusion_window: int,
    fresh_training: bool,
) -> dict[str, Any] | None:
    """Build optional candidate diagnostics when the predictor supports it."""

    predictor = build_evaluation_predictor(
        model_slug,
        band=band,
        fresh_training=fresh_training,
    )
    if not hasattr(predictor, "build_evaluation_report"):
        return None

    model_data = generate_model_data(
        shows_df,
        setlists_df,
        reference_date,
        exclusion_window=exclusion_window,
        band=band,
    )
    definition = get_model_definition(model_slug)
    if definition.supports_training:
        predictor.train(model_data)

    return predictor.build_evaluation_report(model_data)


def score_model_on_target_shows(
    *,
    band: str,
    model_slug: str,
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    target_shows: pd.DataFrame,
    exclusion_window: int,
    fresh_training: bool = False,
    progress_callback: Any | None = None,
) -> list[dict[str, Any]]:
    """Score a model across a target completed-show window."""

    definition = get_model_definition(model_slug)
    predictor = build_evaluation_predictor(
        model_slug,
        band=band,
        fresh_training=fresh_training,
    )
    scored_rows: list[dict[str, Any]] = []

    total_shows = len(target_shows)
    for index, (_, show_row) in enumerate(target_shows.iterrows(), start=1):
        target_show_date = show_row["show_date"]
        show_id = str(show_row["show_id"])
        if not hasattr(target_show_date, "isoformat"):
            continue

        if progress_callback is not None and (
            index == 1 or index == total_shows or index % 10 == 0
        ):
            progress_callback(
                model_slug=model_slug,
                show_index=index,
                total_shows=total_shows,
                target_show_date=target_show_date,
                show_id=show_id,
            )

        actual_songs = (
            setlists_df.loc[setlists_df["show_id"] == show_id, "song_name"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        if len(actual_songs) <= 2:
            continue

        reference_date = get_evaluation_reference_date(target_show_date)
        try:
            model_data = generate_model_data(
                shows_df,
                setlists_df,
                reference_date,
                exclusion_window=exclusion_window,
                band=band,
            )
            if definition.supports_training:
                predictor.train(model_data)
            prediction_output = predictor.predict(
                model_data=model_data,
                top_k=definition.default_top_k,
            )
            predictions = (
                prediction_output[0]
                if isinstance(prediction_output, tuple)
                else prediction_output
            )
            if not predictions:
                continue

            serialized_predictions = serialize_model_predictions(
                model_slug, predictions
            )
            predicted_song_names = [
                prediction["song_name"] for prediction in serialized_predictions
            ]
        except (ValueError, AttributeError, KeyError, TypeError):
            continue
        except Exception:
            continue

        metrics_by_k: dict[str, dict[str, float]] = {}
        for k in (10, 25, 50):
            metrics_by_k[f"k{k}"] = compute_per_show_metrics(
                predicted_song_names,
                actual_songs,
                k,
            )

        scored_rows.append(
            {
                "band": band,
                "model_slug": model_slug,
                "model_version": definition.version,
                "show_id": show_id,
                "target_show_date": target_show_date.isoformat(),
                "reference_date": reference_date.isoformat(),
                "actual_song_count": len(actual_songs),
                "prediction_count": len(serialized_predictions),
                "metrics": metrics_by_k,
            }
        )

    return scored_rows


def summarize_scored_rows(
    scored_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-show scored rows into a per-window summary."""

    metrics_by_k: dict[str, dict[str, float]] = {}
    for k in (10, 25, 50):
        aggregate = aggregate_metrics(
            [row["metrics"][f"k{k}"] for row in scored_rows],
            k,
        )
        metrics_by_k[f"k{k}"] = {
            "hit_rate": aggregate.hit_rate,
            "avg_matches": aggregate.avg_matches,
            "precision": aggregate.precision,
            "recall": aggregate.recall,
            "f1": aggregate.f1,
        }

    return {
        "shows_evaluated": len(scored_rows),
        "metrics": metrics_by_k,
    }


def build_cross_band_summary(
    metrics_by_band: dict[str, dict[str, dict[str, Any]]],
    *,
    model_slugs: Iterable[str],
) -> dict[str, Any]:
    """Average per-band model metrics so each band has equal weight."""

    summary: dict[str, Any] = {}
    for model_slug in model_slugs:
        band_summaries = [
            band_result[model_slug]
            for band_result in metrics_by_band.values()
            if model_slug in band_result
        ]
        if not band_summaries:
            continue

        metrics: dict[str, dict[str, float]] = {}
        for k_key in ("k10", "k25", "k50"):
            metrics[k_key] = {}
            for metric_name in (
                "hit_rate",
                "avg_matches",
                "precision",
                "recall",
                "f1",
            ):
                metrics[k_key][metric_name] = sum(
                    band_summary["metrics"][k_key][metric_name]
                    for band_summary in band_summaries
                ) / len(band_summaries)

        summary[model_slug] = {
            "bands_evaluated": len(band_summaries),
            "shows_evaluated": sum(
                band_summary["shows_evaluated"] for band_summary in band_summaries
            ),
            "metrics": metrics,
        }

    return summary


def build_delta_summary(
    metrics_by_band: dict[str, dict[str, dict[str, Any]]],
    *,
    candidate_slug: str,
    baseline_slug: str,
    cross_band_summary: dict[str, Any],
) -> dict[str, Any]:
    """Compute candidate-minus-baseline deltas by band and cross-band."""

    by_band: dict[str, Any] = {}
    for band, band_metrics in metrics_by_band.items():
        candidate = band_metrics.get(candidate_slug)
        baseline = band_metrics.get(baseline_slug)
        if not candidate or not baseline:
            continue
        by_band[band] = {}
        for k_key in ("k10", "k25", "k50"):
            by_band[band][k_key] = {
                metric_name: (
                    candidate["metrics"][k_key][metric_name]
                    - baseline["metrics"][k_key][metric_name]
                )
                for metric_name in (
                    "hit_rate",
                    "avg_matches",
                    "precision",
                    "recall",
                    "f1",
                )
            }

    cross_band: dict[str, Any] = {}
    candidate_summary = cross_band_summary.get(candidate_slug)
    baseline_summary = cross_band_summary.get(baseline_slug)
    if candidate_summary and baseline_summary:
        for k_key in ("k10", "k25", "k50"):
            cross_band[k_key] = {
                metric_name: (
                    candidate_summary["metrics"][k_key][metric_name]
                    - baseline_summary["metrics"][k_key][metric_name]
                )
                for metric_name in (
                    "hit_rate",
                    "avg_matches",
                    "precision",
                    "recall",
                    "f1",
                )
            }

    return {
        "baseline_model": baseline_slug,
        "cross_band": cross_band,
        "by_band": by_band,
    }


def build_promotion_gate(
    *,
    metrics_by_band: dict[str, dict[str, dict[str, Any]]],
    cross_band_summary: dict[str, Any],
    candidate_slug: str,
    baseline_slug: str = PRIMARY_BASELINE_SLUG,
) -> dict[str, Any]:
    """Return the standard promotion gate against the primary baseline."""

    candidate_summary = cross_band_summary.get(candidate_slug)
    baseline_summary = cross_band_summary.get(baseline_slug)
    if not candidate_summary or not baseline_summary:
        return {
            "candidate_model": candidate_slug,
            "baseline_model": baseline_slug,
            "passes": False,
            "reason": "missing_summary",
        }

    candidate_k10_recall = candidate_summary["metrics"]["k10"]["recall"]
    baseline_k10_recall = baseline_summary["metrics"]["k10"]["recall"]
    candidate_k25_recall = candidate_summary["metrics"]["k25"]["recall"]
    baseline_k25_recall = baseline_summary["metrics"]["k25"]["recall"]

    recall_k10_wins = 0
    worst_k25_regression = 0.0
    for band_metrics in metrics_by_band.values():
        candidate_band = band_metrics.get(candidate_slug)
        baseline_band = band_metrics.get(baseline_slug)
        if not candidate_band or not baseline_band:
            continue

        candidate_band_k10 = candidate_band["metrics"]["k10"]["recall"]
        baseline_band_k10 = baseline_band["metrics"]["k10"]["recall"]
        if candidate_band_k10 > baseline_band_k10:
            recall_k10_wins += 1

        k25_delta = (
            candidate_band["metrics"]["k25"]["recall"]
            - baseline_band["metrics"]["k25"]["recall"]
        )
        worst_k25_regression = min(worst_k25_regression, k25_delta)

    bands_evaluated = min(
        candidate_summary["bands_evaluated"],
        baseline_summary["bands_evaluated"],
    )
    required_band_wins = min(4, bands_evaluated)

    checks = {
        "avg_recall_k10_beats_ckplus": candidate_k10_recall > baseline_k10_recall,
        "avg_recall_k25_beats_ckplus": candidate_k25_recall > baseline_k25_recall,
        "wins_at_least_required_bands_on_recall_k10": (
            recall_k10_wins >= required_band_wins
        ),
        "no_band_regresses_more_than_0_02_on_recall_k25": worst_k25_regression >= -0.02,
    }

    return {
        "candidate_model": candidate_slug,
        "candidate_model_version": get_model_definition(candidate_slug).version,
        "baseline_model": baseline_slug,
        "metric": PRIMARY_PROMOTION_METRIC,
        "required_band_wins": required_band_wins,
        "bands_evaluated": bands_evaluated,
        "recall_k10_band_wins": recall_k10_wins,
        "worst_recall_k25_delta_by_band": worst_k25_regression,
        "checks": checks,
        "passes": all(checks.values()),
    }
