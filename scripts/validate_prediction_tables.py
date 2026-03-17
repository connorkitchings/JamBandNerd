"""Utility to validate prediction table freshness and JSON integrity."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from jambandnerd.db.connection import get_supabase_client


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # Supabase stores timestamps in ISO8601 with timezone
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _latest_prediction_row(client, *, table: str, band: str, model_version: str):
    """Fetch the most recently written prediction row for a band/model."""
    resp = (
        client.table(table)
        .select("band, reference_date, predicted_at, predictions")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("predicted_at", desc=True)
        .order("reference_date", desc=True)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, str]] = resp.data or []
    return rows[0] if rows else None


def validate_predictions(bands: Iterable[str], max_age_hours: int) -> int:
    client = get_supabase_client()

    band_list = list(bands)
    if not band_list:
        band_list = ["goose", "eggy", "phish", "wsp", "billy", "um"]
    tables = {
        "predictions_notebook": "notebook_v1",
        "predictions_ckplus": "ckplus_v1",
    }

    now = datetime.now(timezone.utc)
    failures = 0

    for table, model_version in tables.items():
        print(f"\n== Validating {table} ({model_version}) ==")
        for band in band_list:
            row = _latest_prediction_row(
                client, table=table, band=band, model_version=model_version
            )
            if not row:
                print(f"[FAIL] {band}: no rows found")
                failures += 1
                continue

            predicted_at = _parse_timestamp(row.get("predicted_at"))
            age_hrs = None
            if predicted_at:
                age_hrs = (now - predicted_at).total_seconds() / 3600

            try:
                predictions_blob = row.get("predictions")
                parsed = (
                    json.loads(predictions_blob)
                    if isinstance(predictions_blob, str)
                    else predictions_blob
                )
                top_song = parsed[0]["song_name"] if parsed else "<empty>"
            except Exception as exc:
                print(f"[FAIL] {band}: invalid JSON payload ({exc})")
                failures += 1
                continue

            if predicted_at is None:
                print(
                    f"[WARN] {band}: missing predicted_at timestamp; latest reference_date={row.get('reference_date')}"
                )
                failures += 1
                continue

            freshness_ok = age_hrs is not None and age_hrs <= max_age_hours
            status = "OK" if freshness_ok else "STALE"
            if not freshness_ok:
                failures += 1

            age_display = f"{age_hrs:.1f}h" if age_hrs is not None else "unknown age"
            print(
                f"[{status}] {band}: reference_date={row.get('reference_date')} predicted_at={predicted_at.isoformat()} age={age_display} top_song={top_song}"
            )

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate prediction tables for freshness and JSON integrity"
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
        default=48,
        help="Maximum allowed staleness (hours) for predicted_at timestamps.",
    )
    args = parser.parse_args()

    failures = validate_predictions(
        bands=args.bands or [], max_age_hours=args.max_age_hours
    )
    if failures:
        raise SystemExit(f"Validation failed with {failures} issue(s)")


if __name__ == "__main__":
    main()
