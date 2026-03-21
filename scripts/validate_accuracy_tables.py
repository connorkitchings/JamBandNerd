"""Validate accuracy table freshness and aggregate-presence expectations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from jambandnerd.config import ACCURACY_TABLES, MODEL_VERSIONS
from jambandnerd.db.connection import get_supabase_client


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


def validate_accuracy(
    bands: Iterable[str], max_age_hours: int, *, validate_aggregate: bool = True
) -> int:
    client = get_supabase_client()

    band_list = list(bands) or ["goose", "eggy", "phish", "wsp", "billy", "um"]
    failures = 0

    for model_slug in ("notebook", "ckplus"):
        model_version = MODEL_VERSIONS[model_slug]
        per_show_table = ACCURACY_TABLES["per_show"]
        aggregate_table = ACCURACY_TABLES[model_slug]
        print(f"\n== Validating {model_slug} accuracy ({model_version}) ==")

        for band in band_list:
            per_show_row = _latest_row(
                client,
                table=per_show_table,
                band=band,
                model_version=model_version,
            )
            failures += _validate_row(
                band=band,
                label="per-show accuracy",
                row=per_show_row,
                max_age_hours=max_age_hours,
                required_fields=("show_date",),
            )

            if not validate_aggregate:
                continue

            aggregate_row = _latest_row(
                client,
                table=aggregate_table,
                band=band,
                model_version=model_version,
            )
            failures += _validate_row(
                band=band,
                label="aggregate accuracy",
                row=aggregate_row,
                max_age_hours=max_age_hours,
                required_fields=("window_start", "window_end"),
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
        "--skip-aggregate-check",
        action="store_true",
        help="Skip validation of aggregate accuracy tables.",
    )
    args = parser.parse_args()

    failures = validate_accuracy(
        bands=args.bands or [],
        max_age_hours=args.max_age_hours,
        validate_aggregate=not args.skip_aggregate_check,
    )
    if failures:
        raise SystemExit(f"Accuracy validation failed with {failures} issue(s)")


if __name__ == "__main__":
    main()
