"""Canonical Supabase audit for website-facing prediction and replay surfaces."""

from __future__ import annotations

import argparse
import json
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jambandnerd.config.bands import get_active_bands
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.db.operations import fetch_prediction_songs_for_date
from jambandnerd.models.readiness import build_model_readiness_report
from jambandnerd.models.registry import list_promoted_web_models
from scripts.check_supported_model_freshness import audit_supported_model_freshness
from scripts.validate_accuracy_tables import (
    _recent_replay_eligible_rows,
)
from scripts.validate_prediction_tables import (
    _latest_prediction_row,
    list_stale_projection_reference_dates,
)
from scripts.validate_prediction_tables import (
    _parse_timestamp as _parse_prediction_timestamp,
)
from scripts.verify_data_freshness import (
    audit_recent_setlist_completeness,
)


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


@dataclass(frozen=True)
class SupabaseModelAudit:
    band: str
    model_slug: str
    model_version: str
    required_window: int
    expected_top_k: int
    canonical_prediction_rows: int
    latest_reference_date: str | None
    latest_prediction_top_k: int | None
    latest_prediction_age_hours: float | None
    latest_prediction_top_song: str | None
    latest_projection_rows: int
    latest_projection_top_song: str | None
    historical_run_rows: int
    unique_historical_target_dates: int
    per_show_accuracy_rows: int
    replay_overlap: dict[str, int]
    replay_lineage_rows_checked: int
    replay_lineage_missing_dates: tuple[str, ...]
    stale_projection_reference_dates: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "band": self.band,
            "model_slug": self.model_slug,
            "model_version": self.model_version,
            "required_window": self.required_window,
            "expected_top_k": self.expected_top_k,
            "canonical_prediction_rows": self.canonical_prediction_rows,
            "latest_reference_date": self.latest_reference_date,
            "latest_prediction_top_k": self.latest_prediction_top_k,
            "latest_prediction_age_hours": self.latest_prediction_age_hours,
            "latest_prediction_top_song": self.latest_prediction_top_song,
            "latest_projection_rows": self.latest_projection_rows,
            "latest_projection_top_song": self.latest_projection_top_song,
            "historical_run_rows": self.historical_run_rows,
            "unique_historical_target_dates": self.unique_historical_target_dates,
            "per_show_accuracy_rows": self.per_show_accuracy_rows,
            "replay_overlap": dict(self.replay_overlap),
            "replay_lineage_rows_checked": self.replay_lineage_rows_checked,
            "replay_lineage_missing_dates": list(self.replay_lineage_missing_dates),
            "stale_projection_reference_dates": list(
                self.stale_projection_reference_dates
            ),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SupabaseBandAudit:
    band: str
    state: str
    freshness: dict[str, object]
    raw_data: dict[str, object]
    models: tuple[SupabaseModelAudit, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "band": self.band,
            "state": self.state,
            "freshness": dict(self.freshness),
            "raw_data": dict(self.raw_data),
            "models": [model.as_dict() for model in self.models],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SupabaseAuditReport:
    state: str
    max_age_hours: int
    replay_window_override: int | None
    promoted_models: tuple[str, ...]
    bands: tuple[SupabaseBandAudit, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "max_age_hours": self.max_age_hours,
            "replay_window_override": self.replay_window_override,
            "promoted_models": list(self.promoted_models),
            "bands": [band.as_dict() for band in self.bands],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def _load_readiness_reports(
    *,
    bands: list[str],
    client,
) -> dict[str, dict[str, dict[str, Any]]]:
    reports: dict[str, dict[str, dict[str, Any]]] = {}
    for definition in list_promoted_web_models():
        report = build_model_readiness_report(
            definition.slug,
            bands=bands,
            client=client,
        )
        reports[definition.slug] = {
            str(status["band"]): status for status in report["bands"]
        }
    return reports


def _parse_predictions_blob(value: object) -> tuple[list[dict[str, Any]], str | None]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except Exception as exc:  # pragma: no cover - exercised through caller tests
        return [], str(exc)
    if parsed is None:
        return [], None
    if not isinstance(parsed, list):
        return [], "predictions payload is not a list"
    normalized = [item for item in parsed if isinstance(item, dict)]
    if len(normalized) != len(parsed):
        return [], "predictions payload contains non-object rows"
    return normalized, None


def _derive_model_audit(
    *,
    band: str,
    definition,
    readiness_status: dict[str, Any],
    client,
    max_age_hours: int,
    replay_window_override: int | None,
    freshness_result,
    skip_accuracy: bool,
) -> SupabaseModelAudit:
    blockers: list[str] = []
    warnings: list[str] = []
    latest_prediction_age_hours: float | None = None
    latest_prediction_top_song: str | None = None
    latest_projection_top_song: str | None = None

    required_window = replay_window_override or int(readiness_status["required_window"])
    latest_reference_date = readiness_status.get("latest_reference_date")
    latest_prediction_top_k = readiness_status.get("latest_prediction_top_k")
    latest_projection_rows = int(readiness_status.get("latest_projection_rows", 0))
    historical_run_rows = int(readiness_status["historical_runs"])
    unique_historical_target_dates = int(
        readiness_status.get("unique_historical_target_dates", 0)
    )
    per_show_accuracy_rows = int(readiness_status["per_show_rows"])
    replay_overlap = {
        str(slug): int(count)
        for slug, count in readiness_status.get("replay_overlap", {}).items()
    }

    latest_prediction_row = _latest_prediction_row(
        client,
        table=definition.prediction_table,
        band=band,
        model_slug=definition.slug,
        model_version=definition.version,
    )
    parsed_predictions: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    if latest_prediction_row is None:
        _append_unique(blockers, "canonical_predictions_missing")
    else:
        parsed_predictions, parse_error = _parse_predictions_blob(
            latest_prediction_row.get("predictions")
        )
        if parse_error:
            _append_unique(blockers, "canonical_predictions_invalid_json")
        else:
            latest_prediction_top_song = (
                str(parsed_predictions[0].get("song_name"))
                if parsed_predictions and parsed_predictions[0].get("song_name")
                else None
            )

        raw_top_k = latest_prediction_row.get("top_k")
        try:
            latest_prediction_top_k = int(raw_top_k)
        except (TypeError, ValueError):
            latest_prediction_top_k = None
            _append_unique(blockers, "canonical_predictions_top_k_mismatch")
        else:
            # Canonical rows may legitimately contain fewer than the registry default
            # when the model produces a smaller unique candidate set. The audit should
            # enforce self-consistency between the stored top_k, JSON payload, and
            # flattened projection rows rather than forcing the registry default.
            if latest_prediction_top_k <= 0 or (
                parsed_predictions
                and latest_prediction_top_k != len(parsed_predictions)
            ):
                _append_unique(blockers, "canonical_predictions_top_k_mismatch")

        predicted_at = _parse_prediction_timestamp(
            latest_prediction_row.get("predicted_at")
        )
        if predicted_at is None:
            _append_unique(blockers, "canonical_predictions_missing_predicted_at")
        else:
            latest_prediction_age_hours = (
                datetime.now(timezone.utc) - predicted_at
            ).total_seconds() / 3600
            if latest_prediction_age_hours > max_age_hours:
                _append_unique(blockers, "canonical_predictions_stale")

        if latest_reference_date:
            projection_rows = fetch_prediction_songs_for_date(
                band=band,
                model_slug=definition.slug,
                reference_date=str(latest_reference_date),
            )
        latest_projection_rows = len(projection_rows)
        latest_projection_top_song = (
            str(projection_rows[0].get("song_name"))
            if projection_rows and projection_rows[0].get("song_name")
            else None
        )

        expected_projection_rows = (
            int(latest_prediction_top_k)
            if latest_prediction_top_k is not None
            else len(parsed_predictions)
        )
        if latest_projection_rows != expected_projection_rows:
            _append_unique(blockers, "prediction_projection_count_mismatch")
        if (
            latest_prediction_top_song is not None
            and latest_projection_top_song != latest_prediction_top_song
        ):
            _append_unique(blockers, "prediction_projection_top_song_mismatch")

    stale_projection_reference_dates = tuple(
        list_stale_projection_reference_dates(
            band=band,
            model_slug=definition.slug,
            model_version=definition.version,
            max_age_hours=max_age_hours,
            client=client,
        )
    )
    if stale_projection_reference_dates:
        _append_unique(blockers, "prediction_projection_recent_stale_rows")

    if historical_run_rows < required_window:
        _append_unique(blockers, "historical_run_rows_below_window")
    if unique_historical_target_dates < required_window:
        _append_unique(blockers, "historical_unique_target_dates_below_window")
    if per_show_accuracy_rows < required_window:
        _append_unique(blockers, "per_show_accuracy_rows_below_window")

    replay_rows = _recent_replay_eligible_rows(
        client,
        table="accuracy_per_show",
        band=band,
        model_version=definition.version,
        limit=required_window,
    )
    if len(replay_rows) < required_window:
        _append_unique(blockers, "replay_eligible_rows_below_window")
    replay_lineage_missing_dates = tuple(
        str(row.get("show_date") or "unknown")
        for row in replay_rows
        if row.get("prediction_run_id") is None
    )
    if replay_lineage_missing_dates:
        _append_unique(blockers, "replay_lineage_missing_prediction_run_id")

    for overlap_slug, overlap_count in replay_overlap.items():
        if overlap_count < required_window:
            _append_unique(blockers, f"replay_overlap_below_window:{overlap_slug}")

    if definition.slug in freshness_result.stale_prediction_models:
        _append_unique(blockers, "supported_prediction_freshness_stale")
    if definition.slug in freshness_result.stale_accuracy_models:
        target = warnings if skip_accuracy else blockers
        _append_unique(
            target,
            (
                "supported_accuracy_freshness_warning"
                if skip_accuracy
                else "supported_accuracy_freshness_stale"
            ),
        )

    return SupabaseModelAudit(
        band=band,
        model_slug=definition.slug,
        model_version=definition.version,
        required_window=required_window,
        expected_top_k=definition.default_top_k,
        canonical_prediction_rows=int(readiness_status["prediction_rows"]),
        latest_reference_date=(
            str(latest_reference_date) if latest_reference_date else None
        ),
        latest_prediction_top_k=(
            int(latest_prediction_top_k)
            if latest_prediction_top_k is not None
            else None
        ),
        latest_prediction_age_hours=latest_prediction_age_hours,
        latest_prediction_top_song=latest_prediction_top_song,
        latest_projection_rows=latest_projection_rows,
        latest_projection_top_song=latest_projection_top_song,
        historical_run_rows=historical_run_rows,
        unique_historical_target_dates=unique_historical_target_dates,
        per_show_accuracy_rows=per_show_accuracy_rows,
        replay_overlap=replay_overlap,
        replay_lineage_rows_checked=len(replay_rows),
        replay_lineage_missing_dates=replay_lineage_missing_dates,
        stale_projection_reference_dates=stale_projection_reference_dates,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def run_supabase_audit(
    *,
    bands: list[str] | None = None,
    max_age_hours: int = 72,
    replay_window: int | None = None,
    skip_accuracy: bool = False,
) -> SupabaseAuditReport:
    selected_bands = bands or list(get_active_bands())
    promoted_models = list_promoted_web_models()
    client = get_supabase_client()
    readiness_reports = _load_readiness_reports(bands=selected_bands, client=client)

    band_audits: list[SupabaseBandAudit] = []
    all_blockers: list[str] = []
    all_warnings: list[str] = []

    for band in selected_bands:
        freshness_result = audit_supported_model_freshness(
            band=band,
            max_age_hours=max_age_hours,
            skip_accuracy=skip_accuracy,
            emit_text=False,
            client=client,
        )
        raw_result = audit_recent_setlist_completeness(
            band,
            client=client,
            emit_text=False,
        )

        model_results = tuple(
            _derive_model_audit(
                band=band,
                definition=definition,
                readiness_status=readiness_reports[definition.slug][band],
                client=client,
                max_age_hours=max_age_hours,
                replay_window_override=replay_window,
                freshness_result=freshness_result,
                skip_accuracy=skip_accuracy,
            )
            for definition in promoted_models
        )

        band_blockers: list[str] = []
        band_warnings: list[str] = []
        if raw_result.missing_show_count > 0:
            _append_unique(band_warnings, "recent_completed_shows_missing_setlists")

        for model_result in model_results:
            for blocker in model_result.blockers:
                _append_unique(
                    band_blockers,
                    f"{model_result.model_slug}:{blocker}",
                )
            for warning in model_result.warnings:
                _append_unique(
                    band_warnings,
                    f"{model_result.model_slug}:{warning}",
                )

        if freshness_result.freshness_state == "warning":
            _append_unique(
                band_warnings,
                "supported_model_freshness_warning",
            )

        if band_blockers:
            state = "failed"
        elif band_warnings:
            state = "warning"
        else:
            state = "ok"

        band_audits.append(
            SupabaseBandAudit(
                band=band,
                state=state,
                freshness=freshness_result.as_dict(),
                raw_data=raw_result.as_dict(),
                models=model_results,
                blockers=tuple(band_blockers),
                warnings=tuple(band_warnings),
            )
        )

        for blocker in band_blockers:
            _append_unique(all_blockers, f"{band}:{blocker}")
        for warning in band_warnings:
            _append_unique(all_warnings, f"{band}:{warning}")

    if all_blockers:
        state = "failed"
    elif all_warnings:
        state = "warning"
    else:
        state = "ok"

    return SupabaseAuditReport(
        state=state,
        max_age_hours=max_age_hours,
        replay_window_override=replay_window,
        promoted_models=tuple(definition.slug for definition in promoted_models),
        bands=tuple(band_audits),
        blockers=tuple(all_blockers),
        warnings=tuple(all_warnings),
    )


def _write_report(path: str, report: SupabaseAuditReport) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _print_report(report: SupabaseAuditReport) -> None:
    print(
        f"Supabase audit state={report.state} "
        f"bands={len(report.bands)} promoted_models={','.join(report.promoted_models)}"
    )
    for band in report.bands:
        print(
            f"- {band.band}: state={band.state} "
            f"blockers={len(band.blockers)} warnings={len(band.warnings)}"
        )
        for model in band.models:
            print(
                f"  - {model.model_slug}: predictions={model.canonical_prediction_rows} "
                f"projection_rows={model.latest_projection_rows} "
                f"historical_dates={model.unique_historical_target_dates} "
                f"accuracy_rows={model.per_show_accuracy_rows}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit website-facing Supabase prediction and replay tables."
    )
    parser.add_argument(
        "--band",
        dest="bands",
        action="append",
        help="Band to audit (repeat for multiple). Defaults to all active bands.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=72,
        help="Maximum allowed staleness in hours for website-facing surfaces.",
    )
    parser.add_argument(
        "--replay-window",
        type=int,
        default=None,
        help="Optional replay window override. Defaults to each model's readiness window.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the JSON audit report.",
    )
    parser.add_argument(
        "--skip-accuracy",
        action="store_true",
        help="Treat stale accuracy freshness as a warning for this run.",
    )
    args = parser.parse_args()

    report = run_supabase_audit(
        bands=args.bands or None,
        max_age_hours=args.max_age_hours,
        replay_window=args.replay_window,
        skip_accuracy=args.skip_accuracy,
    )
    if args.output:
        _write_report(args.output, report)
    _print_report(report)
    if report.state == "failed":
        raise SystemExit(
            f"Supabase audit failed with {len(report.blockers)} blocker(s)"
        )


if __name__ == "__main__":
    main()
