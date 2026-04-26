"""Read-only rollout checks for single-model setlist prediction tables."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.config import (
    SETLIST_ACCURACY_TABLE,
    SETLIST_PREDICTION_SONGS_TABLE,
    SETLIST_PREDICTIONS_TABLE,
    SETLIST_RESULTS_TABLE,
)
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.db.operations import get_table_schema
from jambandnerd.models.registry import get_band_metadata, list_active_bands
from scripts.audit_supabase_tables import run_supabase_audit

ExpectedState = Literal["any", "empty", "populated"]

TABLE_REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    SETLIST_PREDICTIONS_TABLE: (
        "id",
        "band",
        "target_show_key",
        "target_show_date",
        "reference_date",
        "model_version",
        "generated_at",
        "top_k",
        "predictions",
    ),
    SETLIST_PREDICTION_SONGS_TABLE: (
        "id",
        "prediction_run_id",
        "band",
        "model_version",
        "target_show_key",
        "rank",
        "song_name",
        "score",
        "prediction_payload",
    ),
    SETLIST_RESULTS_TABLE: (
        "id",
        "band",
        "target_show_key",
        "target_show_date",
        "reference_date",
        "model_version",
        "generated_at",
        "top_k",
        "predictions",
        "actual_songs",
        "actual_song_count",
    ),
    SETLIST_ACCURACY_TABLE: (
        "id",
        "band",
        "model_version",
        "show_id",
        "target_show_key",
        "show_date",
        "target_show_date",
        "reference_date",
        "prediction_run_id",
        "actual_song_count",
        "evaluated_at",
        "p10",
        "p25",
        "p50",
        "recall_10",
        "recall_25",
        "recall_50",
        "weighted_precision_score",
    ),
}


@dataclass(frozen=True)
class TableRolloutStatus:
    table: str
    readable: bool
    row_count: int | None
    schema_checked: bool
    missing_columns: tuple[str, ...]
    error: str | None


@dataclass(frozen=True)
class BandModelRolloutStatus:
    band: str
    model_version: str
    setlist_predictions: int | None
    setlist_prediction_songs: int | None
    setlist_results: int | None
    setlist_accuracy: int | None


@dataclass(frozen=True)
class PredictionStorageRolloutReport:
    state: str
    expected_state: ExpectedState
    bands: tuple[str, ...]
    model_versions: tuple[str, ...]
    tables: tuple[TableRolloutStatus, ...]
    band_models: tuple[BandModelRolloutStatus, ...]
    production_audit_state: str | None
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _count_rows(client, table: str, *, filters: dict[str, object] | None = None) -> int:
    query = client.table(table).select("id", count="exact")
    for column, value in (filters or {}).items():
        query = query.eq(column, value)
    response = query.limit(1).execute()
    return int(response.count or 0)


def _table_status(client, table: str) -> TableRolloutStatus:
    try:
        row_count = _count_rows(client, table)
    except Exception as exc:
        return TableRolloutStatus(
            table=table,
            readable=False,
            row_count=None,
            schema_checked=False,
            missing_columns=(),
            error=str(exc),
        )

    schema = get_table_schema(table)
    if not schema:
        return TableRolloutStatus(
            table=table,
            readable=True,
            row_count=row_count,
            schema_checked=False,
            missing_columns=(),
            error=None,
        )

    present_columns = {str(row.get("column_name")) for row in schema}
    missing = tuple(
        column
        for column in TABLE_REQUIRED_COLUMNS[table]
        if column not in present_columns
    )
    return TableRolloutStatus(
        table=table,
        readable=True,
        row_count=row_count,
        schema_checked=True,
        missing_columns=missing,
        error=None,
    )


def _band_model_status(
    client,
    *,
    band: str,
    model_version: str,
) -> BandModelRolloutStatus:
    filters = {
        "band": band,
        "model_version": model_version,
    }
    return BandModelRolloutStatus(
        band=band,
        model_version=model_version,
        setlist_predictions=_count_rows(
            client, SETLIST_PREDICTIONS_TABLE, filters=filters
        ),
        setlist_prediction_songs=_count_rows(
            client, SETLIST_PREDICTION_SONGS_TABLE, filters=filters
        ),
        setlist_results=_count_rows(client, SETLIST_RESULTS_TABLE, filters=filters),
        setlist_accuracy=_count_rows(client, SETLIST_ACCURACY_TABLE, filters=filters),
    )


def check_prediction_storage_rollout(
    *,
    bands: list[str] | None = None,
    expected_state: ExpectedState = "any",
    client=None,
) -> PredictionStorageRolloutReport:
    selected_bands = tuple(bands or list_active_bands())
    model_versions = tuple(
        get_band_metadata(band).model_version for band in selected_bands
    )
    client = client or get_supabase_client()
    blockers: list[str] = []
    warnings: list[str] = []

    tables = tuple(_table_status(client, table) for table in TABLE_REQUIRED_COLUMNS)
    for status in tables:
        if not status.readable:
            blockers.append(f"{status.table}:not_readable:{status.error}")
        if status.missing_columns:
            missing = ",".join(status.missing_columns)
            blockers.append(f"{status.table}:schema_missing_columns:{missing}")

    band_model_statuses: list[BandModelRolloutStatus] = []
    if not blockers:
        for band in selected_bands:
            band_model_statuses.append(
                _band_model_status(
                    client,
                    band=band,
                    model_version=get_band_metadata(band).model_version,
                )
            )

    if expected_state == "empty":
        for status in tables:
            if status.row_count not in (0, None):
                blockers.append(f"{status.table}:expected_empty:{status.row_count}")

    production_audit_state: str | None = None
    if expected_state == "populated" and not blockers:
        audit = run_supabase_audit(bands=list(selected_bands))
        production_audit_state = audit.state
        if audit.state == "failed":
            blockers.extend(f"production_audit:{item}" for item in audit.blockers)
        elif audit.state == "warning":
            warnings.extend(f"production_audit:{item}" for item in audit.warnings)

    state = "failed" if blockers else ("warning" if warnings else "ok")
    return PredictionStorageRolloutReport(
        state=state,
        expected_state=expected_state,
        bands=selected_bands,
        model_versions=model_versions,
        tables=tables,
        band_models=tuple(band_model_statuses),
        production_audit_state=production_audit_state,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def _write_report(path: str, report: PredictionStorageRolloutReport) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _print_report(report: PredictionStorageRolloutReport) -> None:
    print(
        f"Prediction storage rollout state={report.state} "
        f"expected_state={report.expected_state} "
        f"bands={','.join(report.bands)} "
        f"model_versions={','.join(report.model_versions)}"
    )
    for table in report.tables:
        schema = "checked" if table.schema_checked else "not checked"
        count = "unknown" if table.row_count is None else str(table.row_count)
        print(
            f"- {table.table}: readable={table.readable} rows={count} "
            f"schema={schema}"
        )
    for status in report.band_models:
        print(
            f"- {status.band}/{status.model_version}: "
            f"predictions={status.setlist_predictions} "
            f"songs={status.setlist_prediction_songs} "
            f"results={status.setlist_results} "
            f"accuracy={status.setlist_accuracy}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check single-model setlist prediction storage rollout readiness."
    )
    parser.add_argument(
        "--band",
        dest="bands",
        action="append",
        choices=list_active_bands(),
        help="Band to check (repeat for multiple). Defaults to all supported bands.",
    )
    parser.add_argument(
        "--expected-state",
        choices=("any", "empty", "populated"),
        default="any",
        help="Expected rollout state for the checked tables.",
    )
    parser.add_argument("--output", help="Optional path for JSON report output.")
    args = parser.parse_args()

    report = check_prediction_storage_rollout(
        bands=args.bands,
        expected_state=args.expected_state,
    )
    if args.output:
        _write_report(args.output, report)
    _print_report(report)
    if report.state == "failed":
        raise SystemExit(
            f"Prediction storage rollout check failed with {len(report.blockers)} blocker(s)"
        )


if __name__ == "__main__":
    main()
