"""Shared model comparison helpers."""

from __future__ import annotations

from datetime import timezone
from typing import Any, Iterable, Sequence

import pandas as pd

from jambandnerd.config import (
    DEAL_MIN_TRAINING_SHOWS,
    DEAL_TRAINING_WINDOW_SHOWS,
    HISTORICAL_PREDICTION_RUNS_TABLE,
)
from jambandnerd.db.operations import upsert_historical_prediction_run
from jambandnerd.models.accuracy import aggregate_metrics, compute_per_show_metrics
from jambandnerd.models.evaluation import get_evaluation_reference_date
from jambandnerd.models.model_test_cache import LocalModelTestCache
from jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    serialize_model_predictions,
)
from jambandnerd.transformations.gaps import generate_model_data

PRIMARY_BASELINE_SLUG = "ckplus"
PRIMARY_PROMOTION_METRIC = "recall"
PROBABILITY_STD_FLOOR = 0.03
PROBABILITY_RANGE_FLOOR = 0.10
TOP_10_MASS_SHARE_FLOOR = 0.30
TRAINING_PROBABILITY_GAP_FLOOR = 0.05
EXPECTED_CALIBRATION_ERROR_CEILING = 0.12
CANARY_MAX_RECALL_K10_REGRESSION = -0.01


def build_evaluation_predictor(
    model_slug: str,
    *,
    band: str,
    fresh_training: bool = False,
    candidate_overrides: dict[str, Any] | None = None,
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
    if candidate_overrides:
        kwargs.update(candidate_overrides)
    return build_predictor(model_slug, band=band, **kwargs)


def extract_experiment_metadata(
    *,
    model_slug: str,
    predictor: Any,
    feature_set_label: str,
    exclusion_window: int,
    window_labels: Sequence[str],
    fresh_training: bool,
    candidate_overrides: dict[str, Any] | None = None,
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

    metadata: dict[str, Any] = {
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
    if candidate_overrides:
        metadata["candidate_overrides"] = dict(candidate_overrides)
    return metadata


def maybe_build_model_diagnostics(
    *,
    band: str,
    model_slug: str,
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date,
    exclusion_window: int,
    fresh_training: bool,
    candidate_overrides: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build optional candidate diagnostics when the predictor supports it."""

    predictor = build_evaluation_predictor(
        model_slug,
        band=band,
        fresh_training=fresh_training,
        candidate_overrides=candidate_overrides,
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


def build_metrics_bundle(
    predicted_song_names: Sequence[str],
    actual_songs: Sequence[str],
) -> dict[str, dict[str, float]]:
    """Compute the standard per-show metric bundle."""

    metrics_by_k: dict[str, dict[str, float]] = {}
    for k in (10, 25, 50):
        metrics_by_k[f"k{k}"] = compute_per_show_metrics(
            list(predicted_song_names),
            list(actual_songs),
            k,
        )
    return metrics_by_k


def build_scored_run_record(
    *,
    band: str,
    model_slug: str,
    model_version: str,
    show_id: str,
    target_show_date: str,
    reference_date: str,
    actual_songs: Sequence[str],
    predictions: Sequence[dict[str, Any]],
    generated_at: str,
    experiment_context: dict[str, Any] | None = None,
    prediction_run_id: int | None = None,
) -> dict[str, Any]:
    """Build one reusable historical scored-run record."""

    predicted_song_names = [str(prediction["song_name"]) for prediction in predictions]
    record = {
        "band": band,
        "model_slug": model_slug,
        "model_version": model_version,
        "show_id": show_id,
        "target_show_date": target_show_date,
        "reference_date": reference_date,
        "actual_songs": list(actual_songs),
        "actual_song_count": len(actual_songs),
        "predictions": list(predictions),
        "prediction_count": len(predictions),
        "generated_at": generated_at,
        "metrics": build_metrics_bundle(predicted_song_names, actual_songs),
    }
    if experiment_context is not None:
        record["experiment_context"] = dict(experiment_context)
    if prediction_run_id is not None:
        record["prediction_run_id"] = int(prediction_run_id)
    return record


def publish_scored_run_record(record: dict[str, Any]) -> int:
    """Publish a scored-run record into canonical historical lineage storage."""

    prediction_run_id = upsert_historical_prediction_run(
        band=str(record["band"]),
        model_slug=str(record["model_slug"]),
        model_version=str(record["model_version"]),
        reference_date=str(record["reference_date"]),
        target_show_id=str(record["show_id"]),
        target_show_date=str(record["target_show_date"]),
        generated_at=str(record["generated_at"]),
        predictions=list(record["predictions"]),
        actual_songs=list(record["actual_songs"]),
        table_name=HISTORICAL_PREDICTION_RUNS_TABLE,
    )
    return int(prediction_run_id)


def score_model_on_target_shows(
    *,
    band: str,
    model_slug: str,
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    target_shows: pd.DataFrame,
    exclusion_window: int,
    fresh_training: bool = False,
    candidate_overrides: dict[str, Any] | None = None,
    progress_callback: Any | None = None,
    local_cache: LocalModelTestCache | None = None,
    publish_historical_runs: bool = False,
    experiment_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Score a model across a target completed-show window."""

    definition = get_model_definition(model_slug)
    predictor = build_evaluation_predictor(
        model_slug,
        band=band,
        fresh_training=fresh_training,
        candidate_overrides=candidate_overrides,
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
        reference_date_str = reference_date.isoformat()
        if local_cache is not None:
            cached_record = local_cache.load_scored_run(
                band=band,
                model_slug=model_slug,
                reference_date=reference_date_str,
                target_show_id=show_id,
            )
            if cached_record is not None:
                if (
                    publish_historical_runs
                    and cached_record.get("prediction_run_id") is None
                ):
                    cached_record["prediction_run_id"] = publish_scored_run_record(
                        cached_record
                    )
                    local_cache.write_scored_run(cached_record)
                scored_rows.append(cached_record)
                continue

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
        except (ValueError, AttributeError, KeyError, TypeError):
            continue
        except Exception:
            continue

        scored_record = build_scored_run_record(
            band=band,
            model_slug=model_slug,
            model_version=definition.version,
            show_id=show_id,
            target_show_date=target_show_date.isoformat(),
            reference_date=reference_date_str,
            actual_songs=actual_songs,
            predictions=serialized_predictions,
            generated_at=pd.Timestamp.now(tz=timezone.utc).isoformat(),
            experiment_context=experiment_context,
        )
        if publish_historical_runs:
            scored_record["prediction_run_id"] = publish_scored_run_record(
                scored_record
            )
        if local_cache is not None:
            local_cache.write_scored_run(scored_record)
        scored_rows.append(scored_record)

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


def build_candidate_weak_show_summary(
    *,
    candidate_rows: Sequence[dict[str, Any]],
    baseline_rows: Sequence[dict[str, Any]],
    limit: int = 3,
) -> dict[str, Any]:
    """Summarize the shows where the candidate loses most to the baseline."""

    baseline_by_show = {str(row["show_id"]): row for row in baseline_rows}
    compared_shows: list[dict[str, Any]] = []
    for candidate_row in candidate_rows:
        show_id = str(candidate_row["show_id"])
        baseline_row = baseline_by_show.get(show_id)
        if baseline_row is None:
            continue

        candidate_k10 = float(candidate_row["metrics"]["k10"]["recall"])
        baseline_k10 = float(baseline_row["metrics"]["k10"]["recall"])
        candidate_k25 = float(candidate_row["metrics"]["k25"]["recall"])
        baseline_k25 = float(baseline_row["metrics"]["k25"]["recall"])
        compared_shows.append(
            {
                "show_id": show_id,
                "target_show_date": str(candidate_row["target_show_date"]),
                "actual_song_count": int(candidate_row["actual_song_count"]),
                "top_prediction": (
                    str(candidate_row["predictions"][0]["song_name"])
                    if candidate_row.get("predictions")
                    else None
                ),
                "candidate_recall_k10": candidate_k10,
                "baseline_recall_k10": baseline_k10,
                "recall_k10_delta": candidate_k10 - baseline_k10,
                "candidate_recall_k25": candidate_k25,
                "baseline_recall_k25": baseline_k25,
                "recall_k25_delta": candidate_k25 - baseline_k25,
            }
        )

    compared_shows.sort(
        key=lambda item: (
            item["recall_k10_delta"],
            item["recall_k25_delta"],
            item["candidate_recall_k10"],
            item["candidate_recall_k25"],
            item["target_show_date"],
        )
    )
    return {
        "shows_compared": len(compared_shows),
        "worst_shows": compared_shows[:limit],
    }


def _safe_nested_float(payload: dict[str, Any] | None, *path: str) -> float | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if isinstance(current, (int, float)):
        return float(current)
    return None


def assess_probability_quality(
    diagnostics: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify whether diagnostics show a probability-quality concern."""

    if not diagnostics:
        return {
            "status": "missing",
            "has_concern": False,
            "reasons": [],
            "signals": {},
        }

    probability_std = _safe_nested_float(
        diagnostics,
        "current_candidate_probability_distribution",
        "std",
    )
    probability_range = _safe_nested_float(
        diagnostics,
        "current_candidate_probability_quality",
        "probability_range",
    )
    top_10_mass_share = _safe_nested_float(
        diagnostics,
        "current_candidate_probability_quality",
        "top_10_mass_share",
    )
    training_gap = _safe_nested_float(
        diagnostics,
        "training_separation_summary",
        "probability_gap",
    )
    expected_calibration_error = _safe_nested_float(
        diagnostics,
        "calibration_error_summary",
        "expected_calibration_error",
    )

    reasons: list[str] = []
    if probability_std is not None and probability_std < PROBABILITY_STD_FLOOR:
        reasons.append("low_probability_std")
    if probability_range is not None and probability_range < PROBABILITY_RANGE_FLOOR:
        reasons.append("narrow_probability_range")
    if top_10_mass_share is not None and top_10_mass_share < TOP_10_MASS_SHARE_FLOOR:
        reasons.append("diffuse_top_10_mass")
    if training_gap is not None and training_gap < TRAINING_PROBABILITY_GAP_FLOOR:
        reasons.append("weak_training_separation")
    if (
        expected_calibration_error is not None
        and expected_calibration_error > EXPECTED_CALIBRATION_ERROR_CEILING
    ):
        reasons.append("high_expected_calibration_error")

    severe_calibration = (
        expected_calibration_error is not None
        and expected_calibration_error > EXPECTED_CALIBRATION_ERROR_CEILING
    )
    has_concern = severe_calibration or len(reasons) >= 2

    return {
        "status": "concern" if has_concern else "healthy",
        "has_concern": has_concern,
        "reasons": reasons,
        "signals": {
            "probability_std": probability_std,
            "probability_range": probability_range,
            "top_10_mass_share": top_10_mass_share,
            "training_probability_gap": training_gap,
            "expected_calibration_error": expected_calibration_error,
        },
    }


def build_replacement_readiness_summary(
    *,
    metrics_by_band: dict[str, dict[str, dict[str, Any]]],
    cross_band_summary: dict[str, Any],
    candidate_slug: str,
    baseline_slug: str = PRIMARY_BASELINE_SLUG,
    diagnostics_by_band: dict[str, Any] | None = None,
    weak_show_summaries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a decision-oriented readiness summary for one comparison window."""

    promotion_gate = build_promotion_gate(
        metrics_by_band=metrics_by_band,
        cross_band_summary=cross_band_summary,
        candidate_slug=candidate_slug,
        baseline_slug=baseline_slug,
    )
    delta_summary = build_delta_summary(
        metrics_by_band,
        candidate_slug=candidate_slug,
        baseline_slug=baseline_slug,
        cross_band_summary=cross_band_summary,
    )

    weak_band_summaries: list[dict[str, Any]] = []
    driver_counts = {
        "healthy": 0,
        "ranking_accuracy": 0,
        "probability_quality": 0,
        "both": 0,
    }
    probability_concern_bands = 0
    bands_meeting_recall_k10 = 0
    bands_meeting_recall_k25 = 0

    for band in sorted(metrics_by_band):
        band_metrics = metrics_by_band[band]
        candidate_metrics = band_metrics.get(candidate_slug)
        baseline_metrics = band_metrics.get(baseline_slug)
        if not candidate_metrics or not baseline_metrics:
            continue

        recall_k10_delta = (
            float(candidate_metrics["metrics"]["k10"]["recall"])
            - float(baseline_metrics["metrics"]["k10"]["recall"])
        )
        recall_k25_delta = (
            float(candidate_metrics["metrics"]["k25"]["recall"])
            - float(baseline_metrics["metrics"]["k25"]["recall"])
        )
        if recall_k10_delta >= 0:
            bands_meeting_recall_k10 += 1
        if recall_k25_delta >= 0:
            bands_meeting_recall_k25 += 1

        probability_quality = assess_probability_quality(
            (diagnostics_by_band or {}).get(band)
        )
        probability_concern = probability_quality["has_concern"]
        if probability_concern:
            probability_concern_bands += 1

        ranking_concern = recall_k10_delta < 0 or recall_k25_delta < 0
        if ranking_concern and probability_concern:
            failure_driver = "both"
        elif ranking_concern:
            failure_driver = "ranking_accuracy"
        elif probability_concern:
            failure_driver = "probability_quality"
        else:
            failure_driver = "healthy"
        driver_counts[failure_driver] += 1

        weak_band_summaries.append(
            {
                "band": band,
                "status": (
                    "beats_ckplus"
                    if recall_k10_delta >= 0 and recall_k25_delta >= 0
                    else "below_ckplus"
                    if recall_k10_delta < 0 and recall_k25_delta < 0
                    else "mixed"
                ),
                "failure_driver": failure_driver,
                "recall_k10_delta": recall_k10_delta,
                "recall_k25_delta": recall_k25_delta,
                "probability_quality": probability_quality,
                "weak_show_summary": (weak_show_summaries or {}).get(
                    band,
                    {"shows_compared": 0, "worst_shows": []},
                ),
            }
        )

    weak_band_summaries.sort(
        key=lambda item: (
            item["recall_k10_delta"],
            item["recall_k25_delta"],
            0 if item["failure_driver"] == "both" else 1,
            item["band"],
        )
    )

    cross_band_recall_k10_delta = float(
        delta_summary.get("cross_band", {}).get("k10", {}).get("recall", 0.0)
    )
    bands_evaluated = int(promotion_gate.get("bands_evaluated", 0))
    if diagnostics_by_band:
        canary_checks = {
            "no_severe_recall_k25_regression": (
                float(promotion_gate.get("worst_recall_k25_delta_by_band", -1.0))
                >= -0.02
            ),
            "cross_band_recall_k10_not_more_than_0_01_below_ckplus": (
                cross_band_recall_k10_delta >= CANARY_MAX_RECALL_K10_REGRESSION
            ),
            "probability_quality_not_broken_for_majority_of_bands": (
                probability_concern_bands <= max(1, bands_evaluated // 2)
            ),
        }
        canary_status = "safe" if all(canary_checks.values()) else "unsafe"
    else:
        canary_checks = {
            "no_severe_recall_k25_regression": (
                float(promotion_gate.get("worst_recall_k25_delta_by_band", -1.0))
                >= -0.02
            ),
            "cross_band_recall_k10_not_more_than_0_01_below_ckplus": (
                cross_band_recall_k10_delta >= CANARY_MAX_RECALL_K10_REGRESSION
            ),
        }
        canary_status = "ranking_only"

    return {
        "candidate_model": candidate_slug,
        "baseline_model": baseline_slug,
        "gate_passes": bool(promotion_gate.get("passes", False)),
        "promotion_gate": promotion_gate,
        "cross_band_delta_vs_baseline": delta_summary.get("cross_band", {}),
        "bands_evaluated": bands_evaluated,
        "bands_meeting_or_beating_ckplus_recall_k10": bands_meeting_recall_k10,
        "bands_meeting_or_beating_ckplus_recall_k25": bands_meeting_recall_k25,
        "failure_driver_summary": driver_counts,
        "internal_canary": {
            "status": canary_status,
            "checks": canary_checks,
        },
        "weak_bands": weak_band_summaries,
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
