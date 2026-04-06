#!/usr/bin/env python3
"""Rebuild the prediction_songs derived projection from canonical prediction tables.

Usage:
    uv run python scripts/rebuild_prediction_songs.py
    uv run python scripts/rebuild_prediction_songs.py --band goose
    uv run python scripts/rebuild_prediction_songs.py --band goose --model notebook
"""

from __future__ import annotations

import argparse
import json
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.operations import replace_prediction_projection
from src.jambandnerd.models.registry import get_model_definition, list_pipeline_models


def _rebuild_band_model(*, band: str, model_slug: str) -> bool:
    model_definition = get_model_definition(model_slug)
    table_name = model_definition.prediction_table
    model_version = model_definition.version

    client = get_supabase_client()
    resp = (
        client.table(table_name)
        .select("reference_date, predicted_at, predictions, top_k")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("predicted_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        print(f"  [{model_slug}] no canonical rows found — skipping")
        return False

    row = rows[0]
    predictions_blob = row.get("predictions")
    parsed = (
        json.loads(predictions_blob)
        if isinstance(predictions_blob, str)
        else predictions_blob
    )

    if not parsed:
        print(f"  [{model_slug}] empty predictions blob — skipping")
        return False

    replace_prediction_projection(
        band=band,
        model_slug=model_slug,
        model_version=model_version,
        reference_date=row["reference_date"],
        predicted_at=row["predicted_at"],
        predictions=parsed,
    )
    print(f"  [{model_slug}] rebuilt {len(parsed)} songs (ref={row['reference_date']})")
    return True


def rebuild_prediction_songs(*, band: str | None, model: str | None) -> None:
    bands = [band] if band else list(get_active_bands())
    models = [get_model_definition(model)] if model else list_pipeline_models()
    model_slugs = [m.slug for m in models]

    for b in bands:
        print(f"\n== {b.upper()} ==")
        for slug in model_slugs:
            _rebuild_band_model(band=b, model_slug=slug)


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
    args = parser.parse_args()

    if args.band and args.band not in get_active_bands():
        raise SystemExit(f"Unknown band: {args.band}")

    if args.model:
        try:
            get_model_definition(args.model)
        except ValueError as exc:
            raise SystemExit(str(exc))

    rebuild_prediction_songs(band=args.band, model=args.model)


if __name__ == "__main__":
    main()
