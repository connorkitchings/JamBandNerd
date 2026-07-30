"""Shared ingestion preflight decisions for local runs and GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import (
    completed_show_window,
    fetch_column_values_for_ids,
    fetch_table_rows,
)
from src.jambandnerd.config.bands import (
    get_collection_policy,
    get_runtime_band_id_column,
)
from src.jambandnerd.db.connection import get_supabase_client


@dataclass(frozen=True)
class CollectionPreflight:
    band: str
    collection_mode: str
    execution_mode: str
    should_run_collection: bool
    recent_completed_show_count: int
    missing_recent_setlist_count: int
    upcoming_show_count: int
    has_upcoming_show_soon: bool
    has_upcoming_show: bool
    last_successful_collection_at: str | None
    supports_upstream_update_timestamp: bool
    skip_existing_setlists: bool
    recent_window_start: str
    recent_window_end: str
    lookahead_end: str

    def as_github_outputs(self) -> dict[str, str]:
        payload = asdict(self)
        return {
            key: (
                ""
                if value is None
                else str(value).lower() if isinstance(value, bool) else str(value)
            )
            for key, value in payload.items()
        }


def decide_collection_execution_mode(
    *,
    collection_mode: str,
    recent_completed_show_count: int,
    missing_recent_setlist_count: int,
    upcoming_show_count: int,
    allows_verify_only_when_idle: bool,
) -> tuple[str, bool]:
    """Choose the execution mode from policy and recent activity."""
    has_recent_activity = (
        recent_completed_show_count > 0
        or missing_recent_setlist_count > 0
        or upcoming_show_count > 0
    )

    if collection_mode == "always_refresh":
        return "full_refresh", True

    if collection_mode == "verify_only_when_idle":
        return (
            ("bounded_refresh", True) if has_recent_activity else ("verify_only", False)
        )

    if collection_mode == "window_refresh":
        if has_recent_activity or not allows_verify_only_when_idle:
            return "bounded_refresh", True
        return "verify_only", False

    return "full_refresh", True


def _fetch_last_successful_collection_at(*, client, band: str) -> str | None:
    try:
        rows = (
            client.table("collection_runs")
            .select("created_at")
            .eq("band", band)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return None

    if not rows:
        return None
    created_at = rows[0].get("created_at")
    return str(created_at) if created_at else None


def compute_band_preflight(
    band: str,
    *,
    today: date | None = None,
    recent_days: int = 7,
    client=None,
) -> CollectionPreflight:
    """Compute the per-band ingestion preflight decision."""
    today = today or date.today()
    client = client or get_supabase_client()
    policy = get_collection_policy(band)
    id_column = get_runtime_band_id_column(band)

    recent_start, recent_end = completed_show_window(today=today, days=recent_days)
    recent_rows = fetch_table_rows(
        f"{band}_shows_raw",
        select=f"{id_column}, show_date",
        filters=[("gte", "show_date", recent_start), ("lte", "show_date", recent_end)],
        client=client,
    )
    recent_show_ids = [
        row.get(id_column) for row in recent_rows if row.get(id_column) is not None
    ]
    setlist_ids = fetch_column_values_for_ids(
        f"{band}_setlists_raw",
        id_column=id_column,
        ids=recent_show_ids,
        client=client,
    )
    recent_show_id_strings = {str(show_id) for show_id in recent_show_ids}
    missing_recent_setlist_count = len(recent_show_id_strings - setlist_ids)

    lookahead_end = (today + timedelta(days=policy.upcoming_lookahead_days)).isoformat()
    upcoming_rows = fetch_table_rows(
        f"{band}_shows_raw",
        select=f"{id_column}, show_date",
        filters=[
            ("gte", "show_date", today.isoformat()),
            ("lte", "show_date", lookahead_end),
        ],
        client=client,
    )

    execution_mode, should_run_collection = decide_collection_execution_mode(
        collection_mode=policy.collection_mode,
        recent_completed_show_count=len(recent_show_id_strings),
        missing_recent_setlist_count=missing_recent_setlist_count,
        upcoming_show_count=len(upcoming_rows),
        allows_verify_only_when_idle=policy.allows_verify_only_when_idle,
    )

    # Unbounded "any future show" signal for the prediction gate. Distinct from
    # the lookahead-bounded has_upcoming_show_soon: a band can legitimately have
    # a show beyond the window but no show inside it. For UM, allthings only
    # archives played shows, so fall back to the Seated-backed um_upcoming_shows
    # table (mirrors scripts/validate_prediction_tables.py:_has_upcoming_show).
    if upcoming_rows:
        has_upcoming_show = True
    else:
        future_rows = fetch_table_rows(
            f"{band}_shows_raw",
            select=id_column,
            filters=[("gte", "show_date", today.isoformat())],
            limit=1,
            client=client,
        )
        has_upcoming_show = bool(future_rows)
        if not has_upcoming_show and band == "um":
            um_future = fetch_table_rows(
                "um_upcoming_shows",
                select="starts_at_local",
                filters=[("gte", "starts_at_local", today.isoformat())],
                limit=1,
                client=client,
            )
            has_upcoming_show = bool(um_future)

    return CollectionPreflight(
        band=band,
        collection_mode=policy.collection_mode,
        execution_mode=execution_mode,
        should_run_collection=should_run_collection,
        recent_completed_show_count=len(recent_show_id_strings),
        missing_recent_setlist_count=missing_recent_setlist_count,
        upcoming_show_count=len(upcoming_rows),
        has_upcoming_show_soon=bool(upcoming_rows),
        has_upcoming_show=has_upcoming_show,
        last_successful_collection_at=_fetch_last_successful_collection_at(
            client=client, band=band
        ),
        supports_upstream_update_timestamp=policy.supports_upstream_update_timestamp,
        skip_existing_setlists=policy.skip_existing_setlists,
        recent_window_start=recent_start,
        recent_window_end=recent_end,
        lookahead_end=lookahead_end,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute band ingestion preflight.")
    parser.add_argument("--band", required=False, help="Band slug")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format for stdout",
    )
    args = parser.parse_args()

    band = args.band or os.environ.get("BAND")
    if not band:
        raise SystemExit("--band or BAND environment variable is required")

    preflight = compute_band_preflight(band)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            for key, value in preflight.as_github_outputs().items():
                handle.write(f"{key}={value}\n")

    if args.format == "json":
        print(json.dumps(asdict(preflight)))
        return

    print(
        f"[{preflight.band}] mode={preflight.collection_mode} "
        f"execution={preflight.execution_mode} "
        f"run_collection={preflight.should_run_collection} "
        f"recent_completed={preflight.recent_completed_show_count} "
        f"missing_recent_setlists={preflight.missing_recent_setlist_count} "
        f"upcoming_soon={preflight.upcoming_show_count}"
    )


if __name__ == "__main__":
    main()
