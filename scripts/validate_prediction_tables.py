"""Utility to validate prediction table freshness and JSON integrity."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Dict, Iterable, List

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.config import NEXT_SHOW_PREDICTION_RUNS_TABLE
from jambandnerd.config.bands import get_repo_supported_bands
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.db.operations import fetch_prediction_songs_for_date
from jambandnerd.models.registry import (
    get_model_definition,
    list_model_slugs,
    list_pipeline_models,
)
from scripts.common import parse_timestamp


def _latest_prediction_row(
    client, *, table: str, band: str, model_slug: str, model_version: str
):
    """Fetch the most recently written prediction row for a band/model."""
    resp = (
        client.table(table)
        .select(
            "band, target_show_date, reference_date, generated_at, predictions, top_k"
        )
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
        .order("generated_at", desc=True)
        .order("target_show_date", desc=True)
        .limit(1)
        .execute()
    )
    rows: List[Dict[str, str]] = resp.data or []
    return rows[0] if rows else None


def _has_upcoming_show(client, *, band: str) -> bool:
    today_iso = date.today().isoformat()
    try:
        response = (
            client.table(f"{band}_shows_raw")
            .select("show_date")
            .gte("show_date", today_iso)
            .limit(1)
            .execute()
        )
    except AttributeError:
        # Lightweight test clients and older operational stubs may not expose
        # range filters. In that case keep validation strict by requiring a
        # live row instead of silently accepting absence.
        return True
    if response.data:
        return True
    if band == "um":
        upcoming = (
            client.table("um_upcoming_shows")
            .select("starts_at_local")
            .gte("starts_at_local", today_iso)
            .limit(1)
            .execute()
        )
        return bool(upcoming.data)
    return False


def _validate_projection(
    *,
    band: str,
    model_slug: str,
    top_k: int,
    parsed_predictions: list[dict],
    reference_date: str | None,
) -> int:
    if not reference_date:
        print(
            f"[FAIL] {band}/{model_slug}: canonical prediction row is missing reference_date"
        )
        return 1

    projection_rows = fetch_prediction_songs_for_date(
        band=band,
        model_slug=model_slug,
        reference_date=reference_date,
        table_name="next_show_prediction_songs",
    )
    if not projection_rows:
        print(
            f"[FAIL] {band}/{model_slug}: no projected song rows found in next_show_prediction_songs for reference_date={reference_date}"
        )
        print(
            f"  → Expected {top_k} rows (top_song={parsed_predictions[0]['song_name'] if parsed_predictions else '<empty>'})"
        )
        return 1

    if len(projection_rows) != top_k:
        print(
            f"[FAIL] {band}/{model_slug}: projection row count {len(projection_rows)} does not match top_k={top_k} for reference_date={reference_date}"
        )
        return 1

    top_song = parsed_predictions[0]["song_name"] if parsed_predictions else "<empty>"
    projected_top_song = (
        projection_rows[0].get("song_name") if projection_rows else "<empty>"
    )
    if projected_top_song != top_song:
        print(
            f"[FAIL] {band}/{model_slug}: projection top_song={projected_top_song!r} does not match canonical {top_song!r} for reference_date={reference_date}"
        )
        return 1

    return 0


def _check_stale_projection_rows(
    *,
    band: str,
    model_slug: str,
    model_version: str,
    max_age_hours: int,
    reference_window_days: int = 7,
) -> int:
    stale = list_stale_projection_reference_dates(
        band=band,
        model_slug=model_slug,
        model_version=model_version,
        max_age_hours=max_age_hours,
        reference_window_days=reference_window_days,
    )
    if not stale:
        return 0

    for ref in stale:
        print(
            f"[STALE] {band}/{model_slug} ({model_version}): next_show_prediction_songs "
            f"reference_date={ref} has generated_at older than {max_age_hours}h cutoff"
        )
    return len(stale)


def list_stale_projection_reference_dates(
    *,
    band: str,
    model_slug: str,
    model_version: str,
    max_age_hours: int,
    reference_window_days: int = 7,
    client=None,
) -> list[str]:
    """Return stale recent reference_date entries in next_show_prediction_songs."""
    from datetime import date, timedelta

    client = client or get_supabase_client()

    resp = (
        client.table("next_show_prediction_songs")
        .select("reference_date, generated_at")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return []

    latest_key = max(
        (
            (
                parse_timestamp(row.get("generated_at"))
                or datetime.min.replace(tzinfo=timezone.utc),
                row.get("reference_date") or "",
            )
            for row in rows
        ),
        default=None,
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    ref_window_start = (
        date.today() - timedelta(days=reference_window_days)
    ).isoformat()
    projected_by_ref: dict[str, datetime] = {}
    for row in rows:
        reference_date = row.get("reference_date")
        predicted_at = parse_timestamp(row.get("generated_at"))
        if not reference_date or predicted_at is None:
            continue
        if reference_date < ref_window_start:
            continue
        current = projected_by_ref.get(reference_date)
        if current is None or predicted_at > current:
            projected_by_ref[reference_date] = predicted_at

    return [
        ref
        for ref, predicted_at in sorted(projected_by_ref.items())
        if predicted_at < cutoff and (predicted_at, ref) != latest_key
    ]


def validate_predictions(
    bands: Iterable[str],
    max_age_hours: int,
    *,
    validate_projection: bool = True,
    models: Iterable[str] | None = None,
) -> int:
    client = get_supabase_client()

    band_list = list(bands)
    if not band_list:
        band_list = list(get_repo_supported_bands())
    selected_models = list(models) if models is not None else []
    definitions = (
        [get_model_definition(model_slug) for model_slug in selected_models]
        if selected_models
        else list_pipeline_models()
    )

    now = datetime.now(timezone.utc)
    failures = 0

    for definition in definitions:
        table = NEXT_SHOW_PREDICTION_RUNS_TABLE
        model_slug = definition.slug
        model_version = definition.version
        print(f"\n== Validating {table} ({model_version}) ==")
        for band in band_list:
            row = _latest_prediction_row(
                client,
                table=table,
                band=band,
                model_slug=model_slug,
                model_version=model_version,
            )
            if not row:
                if _has_upcoming_show(client, band=band):
                    print(f"[FAIL] {band}/{model_slug}: no live next-show rows found")
                    failures += 1
                else:
                    print(
                        f"[OK] {band}/{model_slug}: no upcoming show; live prediction row not required"
                    )
                continue

            predicted_at = parse_timestamp(row.get("generated_at"))
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
                print(f"[FAIL] {band}/{model_slug}: invalid JSON payload ({exc})")
                failures += 1
                continue

            if predicted_at is None:
                print(
                    f"[WARN] {band}/{model_slug}: missing generated_at timestamp; latest target_show_date={row.get('target_show_date')}"
                )
                failures += 1
                continue

            freshness_ok = age_hrs is not None and age_hrs <= max_age_hours
            status = "OK" if freshness_ok else "STALE"
            if not freshness_ok:
                failures += 1

            age_display = f"{age_hrs:.1f}h" if age_hrs is not None else "unknown age"
            print(
                f"[{status}] {band}/{model_slug}: target_show_date={row.get('target_show_date')} reference_date={row.get('reference_date')} generated_at={predicted_at.isoformat()} age={age_display} top_song={top_song}"
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
        help="Maximum allowed staleness (hours) for generated_at timestamps.",
    )
    parser.add_argument(
        "--skip-projection-check",
        action="store_true",
        help="Skip validation of the derived next_show_prediction_songs projection.",
    )
    parser.add_argument(
        "--model",
        dest="models",
        action="append",
        choices=list_model_slugs(),
        help="Model to validate (repeat for multiple). Defaults to pipeline models.",
    )
    args = parser.parse_args()

    failures = validate_predictions(
        bands=args.bands or [],
        max_age_hours=args.max_age_hours,
        validate_projection=not args.skip_projection_check,
        models=args.models or None,
    )
    if failures:
        raise SystemExit(f"Validation failed with {failures} issue(s)")


if __name__ == "__main__":
    main()
