"""Validate accuracy table freshness and aggregate-presence expectations."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Iterable, List

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.config import (
    SETLIST_ACCURACY_TABLE,
    SETLIST_RESULTS_TABLE,
)
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.models.registry import (
    get_band_metadata,
    list_active_bands,
)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _latest_row(client, *, table: str, band: str, model_version: str):
    response = (
        client.table(table)
        .select("*")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("evaluated_at", desc=True)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, str]] = response.data or []
    return rows[0] if rows else None


def _recent_rows(
    client, *, table: str, band: str, model_version: str, limit: int
) -> List[Dict[str, object]]:
    response = (
        client.table(table)
        .select("*")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("show_date", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def _recent_replay_eligible_rows(
    client, *, table: str, band: str, model_version: str, limit: int
) -> List[Dict[str, object]]:
    rows = _recent_rows(
        client,
        table=table,
        band=band,
        model_version=model_version,
        limit=max(limit * 3, 150),
    )
    eligible = [row for row in rows if int(row.get("actual_song_count") or 0) > 2]
    eligible.sort(
        key=lambda row: (
            str(row.get("show_date") or ""),
            row.get("prediction_run_id") is not None,
            _parse_timestamp(str(row.get("evaluated_at") or ""))
            or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    deduped: list[Dict[str, object]] = []
    seen_keys: set[str] = set()
    for row in eligible:
        dedupe_key = str(row.get("target_show_key") or row.get("show_date") or "")
        if not dedupe_key or dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        deduped.append(row)
        if len(deduped) >= limit:
            break

    return deduped


def _validate_row(
    *,
    band: str,
    label: str,
    row: dict[str, object] | None,
    max_age_hours: int,
    required_fields: Iterable[str],
) -> int:
    if not row:
        print(f"[FAIL] {band}: no {label} row found")
        return 1

    evaluated_at = _parse_timestamp(str(row.get("evaluated_at") or ""))
    if evaluated_at is None:
        print(f"[FAIL] {band}: {label} row is missing a valid evaluated_at timestamp")
        return 1

    missing = [field for field in required_fields if not row.get(field)]
    if missing:
        print(f"[FAIL] {band}: {label} row missing required fields {missing}")
        return 1

    now = datetime.now(timezone.utc)
    age_hrs = (now - evaluated_at).total_seconds() / 3600
    freshness_ok = age_hrs <= max_age_hours
    status = "OK" if freshness_ok else "STALE"
    age_display = f"{age_hrs:.1f}h"

    print(
        f"[{status}] {band}: {label} evaluated_at={evaluated_at.isoformat()} age={age_display}"
    )
    return 0 if freshness_ok else 1


def _validate_row_skip_freshness(
    *,
    band: str,
    label: str,
    row: dict[str, object] | None,
) -> int:
    if not row:
        print(f"[FAIL] {band}: no {label} row found")
        return 1

    evaluated_at = _parse_timestamp(str(row.get("evaluated_at") or ""))
    if evaluated_at is None:
        print(f"[FAIL] {band}: {label} row is missing a valid evaluated_at timestamp")
        return 1

    age_hrs = (datetime.now(timezone.utc) - evaluated_at).total_seconds() / 3600
    print(
        f"[OK] {band}: {label} evaluated_at={evaluated_at.isoformat()} "
        f"age={age_hrs:.1f}h (freshness check skipped)"
    )
    return 0


def validate_accuracy(
    bands: Iterable[str],
    max_age_hours: int,
    *,
    validate_replay: bool = True,
    replay_window: int | None = None,
    skip_freshness: bool = False,
) -> int:
    client = get_supabase_client()

    band_list = list(bands) or list_active_bands()
    failures = 0

    per_show_table = SETLIST_ACCURACY_TABLE
    print(f"\n== Validating {per_show_table} ==")
    for band in band_list:
        metadata = get_band_metadata(band)
        model_version = metadata.model_version
        required_replay_window = replay_window or 100
        per_show_row = _latest_row(
            client,
            table=per_show_table,
            band=band,
            model_version=model_version,
        )
        if skip_freshness:
            failures += _validate_row_skip_freshness(
                band=band,
                label="per-show accuracy",
                row=per_show_row,
            )
        else:
            failures += _validate_row(
                band=band,
                label="per-show accuracy",
                row=per_show_row,
                max_age_hours=max_age_hours,
                required_fields=("show_date",),
            )

        if validate_replay:
            replay_rows = _recent_replay_eligible_rows(
                client,
                table=per_show_table,
                band=band,
                model_version=model_version,
                limit=required_replay_window,
            )
            if not replay_rows:
                print(f"[FAIL] {band}: no replay lineage rows found")
                failures += 1
            elif len(replay_rows) != required_replay_window:
                print(
                    f"[FAIL] {band}: replay lineage has {len(replay_rows)}/{required_replay_window} retained eligible rows"
                )
                failures += 1
            else:
                missing_links = [
                    str(row.get("show_date") or "unknown")
                    for row in replay_rows
                    if row.get("prediction_run_id") is None
                ]
                if missing_links:
                    preview = ", ".join(missing_links[:3])
                    suffix = "..." if len(missing_links) > 3 else ""
                    print(f"[FAIL] {band}: replay lineage missing on {preview}{suffix}")
                    failures += 1
                else:
                    print(
                        f"[OK] {band}: replay lineage ready across {len(replay_rows)} recent shows via {SETLIST_RESULTS_TABLE}"
                    )

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate accuracy tables for freshness and aggregate presence"
    )
    parser.add_argument(
        "--band",
        dest="bands",
        action="append",
        help="Band to validate (repeat for multiple). Defaults to all bands.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=72,
        help="Maximum allowed staleness (hours) for evaluated_at timestamps.",
    )
    parser.add_argument(
        "--skip-replay-check",
        action="store_true",
        help="Skip validation that recent per-show rows carry replay lineage.",
    )
    parser.add_argument(
        "--replay-window",
        type=int,
        default=None,
        help="Optional override for the required replay lineage window.",
    )
    parser.add_argument(
        "--skip-freshness",
        action="store_true",
        help="Skip the evaluated_at age check. Still validates row presence and replay lineage.",
    )
    args = parser.parse_args()

    failures = validate_accuracy(
        bands=args.bands or [],
        max_age_hours=args.max_age_hours,
        validate_replay=not args.skip_replay_check,
        replay_window=args.replay_window,
        skip_freshness=args.skip_freshness,
    )
    if failures:
        raise SystemExit(f"Accuracy validation failed with {failures} issue(s)")


if __name__ == "__main__":
    main()
