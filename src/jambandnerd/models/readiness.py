"""Shared model readiness helpers for backend validation and promotion reports.

Phase B promotion gate (``is_band_promotion_eligible``) lives here alongside
the legacy per-slug readiness report used by the daily CI audit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from jambandnerd.config.bands import get_repo_supported_bands
from jambandnerd.config.database import (
    COMPLETED_SHOW_ACCURACY_TABLE,
    COMPLETED_SHOW_PREDICTION_RUNS_TABLE,
    NEXT_SHOW_PREDICTION_RUNS_TABLE,
    NEXT_SHOW_PREDICTION_SONGS_TABLE,
)
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.models.accuracy import BacktestSummary
from jambandnerd.models.registry import (
    get_model_definition,
    list_promoted_web_models,
)


@dataclass(frozen=True)
class BandReadinessStatus:
    """Backend readiness status for one band/model pair."""

    band: str
    model_slug: str
    model_version: str
    required_window: int
    prediction_rows: int
    projection_rows: int
    latest_reference_date: str | None
    latest_prediction_top_k: int | None
    latest_projection_rows: int
    historical_runs: int
    unique_historical_target_dates: int
    per_show_rows: int
    aggregate_windows: dict[str, bool]
    replay_overlap: dict[str, int]
    blockers: list[str]
    ready: bool


def _row_count(query) -> int:
    response = query.execute()
    return int(response.count or 0)


def _latest_prediction_row(
    client,
    *,
    table: str,
    band: str,
    model_slug: str,
    model_version: str,
) -> dict[str, Any] | None:
    response = (
        client.table(table)
        .select("reference_date, top_k, generated_at")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
        .order("generated_at", desc=True)
        .order("reference_date", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def _projection_row_count_for_reference_date(
    client,
    *,
    band: str,
    model_slug: str,
    model_version: str,
    reference_date: str | None,
) -> int:
    if not reference_date:
        return 0

    response = (
        client.table(NEXT_SHOW_PREDICTION_SONGS_TABLE)
        .select("id", count="exact")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
        .eq("reference_date", reference_date)
        .execute()
    )
    return int(response.count or 0)


def _recent_unique_target_dates(
    client,
    *,
    band: str,
    model_slug: str,
    model_version: str,
    limit: int,
) -> list[str]:
    response = (
        client.table(COMPLETED_SHOW_PREDICTION_RUNS_TABLE)
        .select("target_show_date")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
        .order("target_show_date", desc=True)
        .order("generated_at", desc=True)
        .limit(max(limit * 4, 100))
        .execute()
    )

    unique_dates: list[str] = []
    seen: set[str] = set()
    for row in response.data or []:
        target_show_date = row.get("target_show_date")
        if not isinstance(target_show_date, str) or target_show_date in seen:
            continue
        seen.add(target_show_date)
        unique_dates.append(target_show_date)
        if len(unique_dates) >= limit:
            break
    return unique_dates


def build_model_readiness_report(
    model_slug: str,
    *,
    bands: list[str] | None = None,
    client=None,
) -> dict[str, Any]:
    """Build a backend readiness report for one model across the requested bands."""

    definition = get_model_definition(model_slug)
    selected_bands = bands or list(get_repo_supported_bands())
    if client is None:
        client = get_supabase_client()

    required_window = max(definition.readiness_windows or (50,))
    overlap_models = [
        baseline
        for baseline in definition.readiness_baselines
        if baseline != model_slug
    ]
    for promoted in list_promoted_web_models():
        if promoted.slug != model_slug and promoted.slug not in overlap_models:
            overlap_models.append(promoted.slug)

    band_statuses: list[BandReadinessStatus] = []
    for band in selected_bands:
        latest_prediction_row = _latest_prediction_row(
            client,
            table=NEXT_SHOW_PREDICTION_RUNS_TABLE,
            band=band,
            model_slug=definition.slug,
            model_version=definition.version,
        )
        latest_reference_date = (
            str(latest_prediction_row.get("reference_date"))
            if latest_prediction_row and latest_prediction_row.get("reference_date")
            else None
        )
        latest_prediction_top_k = (
            int(latest_prediction_row["top_k"])
            if latest_prediction_row and latest_prediction_row.get("top_k") is not None
            else None
        )
        prediction_rows = _row_count(
            client.table(NEXT_SHOW_PREDICTION_RUNS_TABLE)
            .select("reference_date", count="exact")
            .eq("band", band)
            .eq("model_version", definition.version)
        )
        projection_rows = _row_count(
            client.table(NEXT_SHOW_PREDICTION_SONGS_TABLE)
            .select("reference_date", count="exact")
            .eq("band", band)
            .eq("model_slug", definition.slug)
            .eq("model_version", definition.version)
        )
        latest_projection_rows = _projection_row_count_for_reference_date(
            client,
            band=band,
            model_slug=definition.slug,
            model_version=definition.version,
            reference_date=latest_reference_date,
        )
        historical_runs = _row_count(
            client.table(COMPLETED_SHOW_PREDICTION_RUNS_TABLE)
            .select("id", count="exact")
            .eq("band", band)
            .eq("model_slug", definition.slug)
            .eq("model_version", definition.version)
        )
        per_show_rows = _row_count(
            client.table(COMPLETED_SHOW_ACCURACY_TABLE)
            .select("show_id", count="exact")
            .eq("band", band)
            .eq("model_slug", definition.slug)
            .eq("model_version", definition.version)
        )

        aggregate_windows: dict[str, bool] = {}
        for window in definition.readiness_windows:
            aggregate_windows[str(window)] = True

        replay_overlap: dict[str, int] = {}
        candidate_dates = _recent_unique_target_dates(
            client,
            band=band,
            model_slug=definition.slug,
            model_version=definition.version,
            limit=required_window,
        )
        unique_historical_target_dates = len(candidate_dates)
        candidate_date_set = set(candidate_dates)
        for overlap_model in overlap_models:
            overlap_definition = get_model_definition(overlap_model)
            baseline_dates = _recent_unique_target_dates(
                client,
                band=band,
                model_slug=overlap_definition.slug,
                model_version=overlap_definition.version,
                limit=required_window,
            )
            replay_overlap[overlap_model] = len(
                candidate_date_set.intersection(baseline_dates)
            )

        blockers: list[str] = []
        if prediction_rows <= 0:
            blockers.append("canonical_predictions_missing")
        if definition.supports_live_predictions and projection_rows <= 0:
            blockers.append("prediction_projection_missing")
        if (
            definition.supports_backtest
            and unique_historical_target_dates < required_window
        ):
            blockers.append(
                "historical_unique_target_dates_below_window:"
                f"{unique_historical_target_dates}/{required_window}"
            )
        if definition.supports_backtest and historical_runs < required_window:
            blockers.append(
                f"historical_runs_below_window:{historical_runs}/{required_window}"
            )
        if definition.supports_backtest and per_show_rows < required_window:
            blockers.append(
                f"per_show_accuracy_below_window:{per_show_rows}/{required_window}"
            )
        for overlap_model, overlap_count in replay_overlap.items():
            if overlap_count < required_window:
                blockers.append(
                    f"replay_overlap_below_window:{overlap_model}:{overlap_count}/{required_window}"
                )

        band_statuses.append(
            BandReadinessStatus(
                band=band,
                model_slug=definition.slug,
                model_version=definition.version,
                required_window=required_window,
                prediction_rows=prediction_rows,
                projection_rows=projection_rows,
                latest_reference_date=latest_reference_date,
                latest_prediction_top_k=latest_prediction_top_k,
                latest_projection_rows=latest_projection_rows,
                historical_runs=historical_runs,
                unique_historical_target_dates=unique_historical_target_dates,
                per_show_rows=per_show_rows,
                aggregate_windows=aggregate_windows,
                replay_overlap=replay_overlap,
                blockers=blockers,
                ready=not blockers,
            )
        )

    ready_band_count = sum(1 for status in band_statuses if status.ready)
    return {
        "model": {
            "slug": definition.slug,
            "version": definition.version,
            "lifecycle_stage": definition.lifecycle_stage,
            "web_visibility": definition.web_visibility,
            "readiness_windows": list(definition.readiness_windows),
            "readiness_baselines": list(definition.readiness_baselines),
        },
        "required_bands": selected_bands,
        "required_window": required_window,
        "ready_for_backend": ready_band_count == len(selected_bands),
        "ready_for_web_promotion": ready_band_count == len(selected_bands)
        and definition.web_visibility == "hidden"
        and definition.enabled_for_web,
        "ready_band_count": ready_band_count,
        "band_count": len(selected_bands),
        "bands": [asdict(status) for status in band_statuses],
    }


# ── Phase B dual-objective promotion gate ─────────────────────────────────────


@dataclass(frozen=True)
class PromotionDecision:
    """Result of evaluating whether a candidate model should replace the incumbent."""

    eligible: bool
    candidate_version: str
    incumbent_version: str
    n_shows: int
    p10_delta: float
    p25_delta: float
    r50_delta: float
    f1_25_delta: float
    blockers: list[str]


def is_band_promotion_eligible(
    *,
    candidate: BacktestSummary,
    incumbent: BacktestSummary,
    min_p10_delta: float = 0.02,
    min_r50_delta: float = 0.02,
    min_f1_25_delta: float = 0.02,
    max_p25_regression: float = 0.01,
    min_shows: int = 100,
) -> PromotionDecision:
    """Gate whether a Phase B candidate should replace the incumbent model.

    The candidate must improve F1@25 and p@10 without regressing p@25
    beyond ``max_p25_regression``, evaluated across at least ``min_shows``
    shows.  The legacy p@10/r@50 dual-objective checks are retained
    side-by-side during the metric transition period.
    """
    if candidate.band != incumbent.band:
        raise ValueError(
            f"Band mismatch: candidate={candidate.band} incumbent={incumbent.band}"
        )

    p10_delta = candidate.p10 - incumbent.p10
    r50_delta = candidate.r50 - incumbent.r50
    f1_25_delta = candidate.f1_25 - incumbent.f1_25
    p25_delta = candidate.p25 - incumbent.p25
    blockers: list[str] = []

    if candidate.n_shows < min_shows:
        blockers.append(f"insufficient_shows:{candidate.n_shows}<{min_shows}")
    if f1_25_delta < min_f1_25_delta:
        blockers.append(
            f"f1_25_delta_below_threshold:{f1_25_delta:.4f}<{min_f1_25_delta}"
        )
    if p25_delta < -max_p25_regression:
        blockers.append(
            f"p25_regression_exceeds_threshold:{p25_delta:.4f}<-{max_p25_regression}"
        )
    if p10_delta < min_p10_delta:
        blockers.append(f"p10_delta_below_threshold:{p10_delta:.4f}<{min_p10_delta}")
    if r50_delta < min_r50_delta:
        blockers.append(f"r50_delta_below_threshold:{r50_delta:.4f}<{min_r50_delta}")

    return PromotionDecision(
        eligible=not blockers,
        candidate_version=candidate.model_version,
        incumbent_version=incumbent.model_version,
        n_shows=candidate.n_shows,
        p10_delta=p10_delta,
        p25_delta=p25_delta,
        r50_delta=r50_delta,
        f1_25_delta=f1_25_delta,
        blockers=blockers,
    )
