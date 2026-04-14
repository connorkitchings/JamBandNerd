#!/usr/bin/env python3
"""Rebuild the prediction_songs derived projection from canonical prediction tables.

Usage:
    uv run python scripts/rebuild_prediction_songs.py
    uv run python scripts/rebuild_prediction_songs.py --band goose
    uv run python scripts/rebuild_prediction_songs.py --band goose --model notebook
    uv run python scripts/rebuild_prediction_songs.py --band goose --model notebook --reference-date-from 2026-04-01 --reference-date-to 2026-04-22
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.operations import replace_prediction_projection
from src.jambandnerd.models.registry import get_model_definition, list_pipeline_models


def _validate_reference_date(value: str | None, *, flag_name: str) -> str | None:
    if value is None:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise SystemExit(f"Invalid {flag_name}: {value}. Use YYYY-MM-DD.") from exc


def _load_prediction_rows(
    *,
    band: str,
    model_slug: str,
    reference_date_from: str | None,
    reference_date_to: str | None,
) -> tuple[str, list[dict[str, Any]]]:
    model_definition = get_model_definition(model_slug)
    table_name = model_definition.prediction_table
    model_version = model_definition.version

    client = get_supabase_client()
    query = (
        client.table(table_name)
        .select("reference_date, predicted_at, predictions, top_k")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
    )

    if reference_date_from:
        query = query.gte("reference_date", reference_date_from)
    if reference_date_to:
        query = query.lte("reference_date", reference_date_to)

    if reference_date_from or reference_date_to:
        query = query.order("reference_date")
    else:
        query = query.order("predicted_at", desc=True).limit(1)

    rows = query.execute().data or []
    return model_version, rows


def _clear_projection_window(
    *,
    band: str,
    model_slug: str,
    reference_date_from: str,
    reference_date_to: str,
) -> None:
    client = get_supabase_client()
    (
        client.table("prediction_songs")
        .delete()
        .eq("band", band)
        .eq("model_slug", model_slug)
        .gte("reference_date", reference_date_from)
        .lte("reference_date", reference_date_to)
        .execute()
    )


def _rebuild_band_model(
    *,
    band: str,
    model_slug: str,
    reference_date_from: str | None,
    reference_date_to: str | None,
) -> bool:
    refresh_projection_timestamps = bool(reference_date_from and reference_date_to)
    model_version, rows = _load_prediction_rows(
        band=band,
        model_slug=model_slug,
        reference_date_from=reference_date_from,
        reference_date_to=reference_date_to,
    )

    if not rows:
        if reference_date_from or reference_date_to:
            print(
                "  "
                f"[{model_slug}] no canonical rows found in window "
                f"{reference_date_from or '*'}..{reference_date_to or '*'} — skipping"
            )
        else:
            print(f"  [{model_slug}] no canonical rows found — skipping")
        return False

    if refresh_projection_timestamps:
        _clear_projection_window(
            band=band,
            model_slug=model_slug,
            reference_date_from=reference_date_from,
            reference_date_to=reference_date_to,
        )
        projection_predicted_at = datetime.now(timezone.utc).isoformat()
    else:
        projection_predicted_at = None

    rebuilt_count = 0
    rebuilt_refs: list[str] = []
    rebuilt_song_count = 0
    for row in rows:
        predictions_blob = row.get("predictions")
        parsed = (
            json.loads(predictions_blob)
            if isinstance(predictions_blob, str)
            else predictions_blob
        )

        if not parsed:
            print(
                f"  [{model_slug}] empty predictions blob for ref={row['reference_date']} — skipping"
            )
            continue

        replace_prediction_projection(
            band=band,
            model_slug=model_slug,
            model_version=model_version,
            reference_date=row["reference_date"],
            predicted_at=projection_predicted_at or row["predicted_at"],
            predictions=parsed,
        )
        rebuilt_count += 1
        rebuilt_refs.append(row["reference_date"])
        rebuilt_song_count = len(parsed)

    if rebuilt_count == 0:
        print(f"  [{model_slug}] no projection rows rebuilt")
        return False

    if rebuilt_count == 1:
        print(
            f"  [{model_slug}] rebuilt {rebuilt_song_count} songs (ref={rebuilt_refs[0]})"
        )
    else:
        print(
            f"  [{model_slug}] rebuilt {rebuilt_count} reference dates "
            f"({rebuilt_refs[0]}..{rebuilt_refs[-1]})"
        )
    return True


def rebuild_prediction_songs(
    *,
    band: str | None,
    model: str | None,
    reference_date_from: str | None = None,
    reference_date_to: str | None = None,
) -> None:
    bands = [band] if band else list(get_active_bands())
    models = [get_model_definition(model)] if model else list_pipeline_models()
    model_slugs = [m.slug for m in models]

    for b in bands:
        print(f"\n== {b.upper()} ==")
        for slug in model_slugs:
            _rebuild_band_model(
                band=b,
                model_slug=slug,
                reference_date_from=reference_date_from,
                reference_date_to=reference_date_to,
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild prediction_songs from canonical prediction tables."
    )
    parser.add_argument(
        "--band",
        help="Band to rebuild (default: all active bands).",
    )
    parser.add_argument(
        "--model",
        help="Model slug to rebuild (default: all pipeline models).",
    )
    parser.add_argument(
        "--reference-date-from",
        help="Rebuild only rows on/after YYYY-MM-DD.",
    )
    parser.add_argument(
        "--reference-date-to",
        help="Rebuild only rows on/before YYYY-MM-DD.",
    )
    args = parser.parse_args()

    if args.band and args.band not in get_active_bands():
        raise SystemExit(f"Unknown band: {args.band}")

    if args.model:
        try:
            get_model_definition(args.model)
        except ValueError as exc:
            raise SystemExit(str(exc))

    reference_date_from = _validate_reference_date(
        args.reference_date_from,
        flag_name="--reference-date-from",
    )
    reference_date_to = _validate_reference_date(
        args.reference_date_to,
        flag_name="--reference-date-to",
    )

    if bool(reference_date_from) != bool(reference_date_to):
        raise SystemExit(
            "--reference-date-from and --reference-date-to must be provided together."
        )
    if (
        reference_date_from
        and reference_date_to
        and reference_date_from > reference_date_to
    ):
        raise SystemExit(
            "--reference-date-from must be on or before --reference-date-to."
        )

    rebuild_prediction_songs(
        band=args.band,
        model=args.model,
        reference_date_from=reference_date_from,
        reference_date_to=reference_date_to,
    )


if __name__ == "__main__":
    main()
