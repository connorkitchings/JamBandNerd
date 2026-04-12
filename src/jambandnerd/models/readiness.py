"""Shared model readiness helpers for backend validation and promotion reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from jambandnerd.config.bands import get_active_bands
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.models.registry import (
    get_model_definition,
    list_promoted_web_models,
)


@dataclass(frozen=True)
class BandReadinessStatus:
    """Backend readiness status for one band/model pair."""

    band: str
    required_window: int
    prediction_rows: int
    projection_rows: int
    historical_runs: int
    per_show_rows: int
    aggregate_windows: dict[str, bool]
    replay_overlap: dict[str, int]
    blockers: list[str]
    ready: bool


def _row_count(query) -> int:
    response = query.execute()
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
        client.table("historical_prediction_runs")
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
    selected_bands = bands or list(get_active_bands())
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
        prediction_rows = _row_count(
            client.table(definition.prediction_table)
            .select("reference_date", count="exact")
            .eq("band", band)
            .eq("model_version", definition.version)
        )
        projection_rows = _row_count(
            client.table("prediction_songs")
            .select("reference_date", count="exact")
            .eq("band", band)
            .eq("model_slug", definition.slug)
            .eq("model_version", definition.version)
        )
        historical_runs = _row_count(
            client.table("historical_prediction_runs")
            .select("id", count="exact")
            .eq("band", band)
            .eq("model_slug", definition.slug)
            .eq("model_version", definition.version)
        )
        per_show_rows = _row_count(
            client.table("accuracy_per_show")
            .select("show_id", count="exact")
            .eq("band", band)
            .eq("model_version", definition.version)
        )

        aggregate_windows: dict[str, bool] = {}
        if definition.aggregate_accuracy_table:
            for window in definition.readiness_windows:
                has_window = (
                    _row_count(
                        client.table(definition.aggregate_accuracy_table)
                        .select("window_end", count="exact")
                        .eq("band", band)
                        .eq("model_version", definition.version)
                        .eq("num_shows", window)
                    )
                    > 0
                )
                aggregate_windows[str(window)] = has_window

        replay_overlap: dict[str, int] = {}
        candidate_dates = _recent_unique_target_dates(
            client,
            band=band,
            model_slug=definition.slug,
            model_version=definition.version,
            limit=required_window,
        )
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
        if definition.supports_backtest and historical_runs < required_window:
            blockers.append(
                f"historical_runs_below_window:{historical_runs}/{required_window}"
            )
        if definition.supports_backtest and per_show_rows < required_window:
            blockers.append(
                f"per_show_accuracy_below_window:{per_show_rows}/{required_window}"
            )
        missing_aggregate_windows = [
            window for window, present in aggregate_windows.items() if not present
        ]
        if missing_aggregate_windows:
            blockers.append(
                "aggregate_windows_missing:" + ",".join(missing_aggregate_windows)
            )
        for overlap_model, overlap_count in replay_overlap.items():
            if overlap_count < required_window:
                blockers.append(
                    f"replay_overlap_below_window:{overlap_model}:{overlap_count}/{required_window}"
                )

        band_statuses.append(
            BandReadinessStatus(
                band=band,
                required_window=required_window,
                prediction_rows=prediction_rows,
                projection_rows=projection_rows,
                historical_runs=historical_runs,
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
