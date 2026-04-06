"""Utility to validate prediction table freshness and JSON integrity."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from jambandnerd.config.bands import get_active_bands
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.db.operations import fetch_latest_prediction_songs
from jambandnerd.models.registry import list_pipeline_models


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
        .select("band, reference_date, predicted_at, predictions, top_k")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("predicted_at", desc=True)
        .order("reference_date", desc=True)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, str]] = resp.data or []
    return rows[0] if rows else None


def _validate_projection(
    *,
    band: str,
    model_slug: str,
    top_k: int,
    parsed_predictions: list[dict],
    reference_date: str | None,
) -> int:
    projection_rows = fetch_latest_prediction_songs(band=band, model_slug=model_slug)
    if not projection_rows:
        print(f"[FAIL] {band}: no projected song rows found")
        return 1

    first_projection = projection_rows[0]
    if reference_date and first_projection.get("reference_date") != reference_date:
        print(
            f"[FAIL] {band}: projection reference_date={first_projection.get('reference_date')} does not match canonical {reference_date}"
        )
        return 1

    if len(projection_rows) != top_k:
        print(
            f"[FAIL] {band}: projection row count {len(projection_rows)} does not match top_k={top_k}"
        )
        return 1

    top_song = parsed_predictions[0]["song_name"] if parsed_predictions else "<empty>"
    projected_top_song = (
        projection_rows[0].get("song_name") if projection_rows else "<empty>"
    )
    if projected_top_song != top_song:
        print(
            f"[FAIL] {band}: projection top_song={projected_top_song} does not match canonical {top_song}"
        )
        return 1

    return 0


def _check_stale_projection_rows(
    *,
    band: str,
    model_slug: str,
    model_version: str,
    max_age_hours: int,
) -> int:
    """Flag stale reference_date entries in prediction_songs."""
    from datetime import timedelta

    client = get_supabase_client()

    resp = (
        client.table("prediction_songs")
        .select("reference_date")
        .eq("band", band)
        .eq("model_version", model_version)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return 0

    distinct_dates = sorted({r["reference_date"] for r in rows})
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).date()

    stale = [d for d in distinct_dates if d < cutoff.isoformat()]
    if not stale:
        return 0

    for ref in stale:
        print(
            f"[STALE] {band}/{model_slug}: prediction_songs reference_date={ref} "
            f"is older than {max_age_hours}h cutoff"
        )
    return len(stale)


def validate_predictions(
    bands: Iterable[str], max_age_hours: int, *, validate_projection: bool = True
) -> int:
    client = get_supabase_client()

    band_list = list(bands)
    if not band_list:
        band_list = list(get_active_bands())
    tables = {
        definition.prediction_table: {
            "model_slug": definition.slug,
            "model_version": definition.version,
        }
        for definition in list_pipeline_models()
    }

    now = datetime.now(timezone.utc)
    failures = 0

    for table, config in tables.items():
        model_slug = config["model_slug"]
        model_version = config["model_version"]
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

            if validate_projection:
                failures += _validate_projection(
                    band=band,
                    model_slug=model_slug,
                    top_k=int(row.get("top_k") or len(parsed)),
                    parsed_predictions=parsed,
                    reference_date=row.get("reference_date"),
                )

            failures += _check_stale_projection_rows(
                band=band,
                model_slug=model_slug,
                model_version=model_version,
                max_age_hours=max_age_hours,
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
    parser.add_argument(
        "--skip-projection-check",
        action="store_true",
        help="Skip validation of the derived prediction_songs projection.",
    )
    args = parser.parse_args()

    failures = validate_predictions(
        bands=args.bands or [],
        max_age_hours=args.max_age_hours,
        validate_projection=not args.skip_projection_check,
    )
    if failures:
        raise SystemExit(f"Validation failed with {failures} issue(s)")


if __name__ == "__main__":
    main()
