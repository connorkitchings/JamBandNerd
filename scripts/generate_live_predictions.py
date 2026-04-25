"""Generate active next-show predictions into the live prediction tables."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data
from src.jambandnerd.config import (
    NEXT_SHOW_PREDICTION_RUNS_TABLE,
    NEXT_SHOW_PREDICTION_SONGS_TABLE,
)
from src.jambandnerd.config.bands import get_repo_supported_bands
from src.jambandnerd.db.operations import (
    replace_next_show_prediction_projection,
    upsert_next_show_prediction_run,
)
from src.jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    list_pipeline_models,
    serialize_model_predictions,
)
from src.jambandnerd.transformations.gaps import generate_model_data


class NpEncoder(json.JSONEncoder):
    """Convert numpy/date values to JSON-safe Python values."""

    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def _first_string(row: pd.Series | dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key) if isinstance(row, dict) else row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _resolve_next_show(
    band: str,
    shows_df: pd.DataFrame,
    *,
    upcoming_df: pd.DataFrame | None = None,
    today: date | None = None,
) -> dict[str, str] | None:
    """Return the next show target, or None when no future show is known."""
    today = today or date.today()
    shows = shows_df.copy()
    shows["_show_date_dt"] = pd.to_datetime(shows["show_date"], errors="coerce").dt.date
    future = shows[shows["_show_date_dt"] >= today].sort_values(
        by=["_show_date_dt", "show_id"]
    )
    if not future.empty:
        row = future.iloc[0]
        show_date = row["_show_date_dt"]
        if isinstance(show_date, date):
            return {
                "target_show_key": str(row["show_id"]),
                "target_show_date": show_date.isoformat(),
                "reference_date": show_date.isoformat(),
            }

    if band == "um" and upcoming_df is not None and not upcoming_df.empty:
        upcoming = upcoming_df.copy()
        for column in ("show_date", "starts_at_local", "starts_at"):
            if column not in upcoming.columns:
                continue
            upcoming["_candidate_date"] = pd.to_datetime(
                upcoming[column], errors="coerce"
            ).dt.date
            future_upcoming = upcoming[
                upcoming["_candidate_date"].notna()
                & (upcoming["_candidate_date"] >= today)
            ].sort_values(by=["_candidate_date"])
            if future_upcoming.empty:
                continue
            row = future_upcoming.iloc[0]
            show_date = row["_candidate_date"]
            target_key = _first_string(
                row,
                (
                    "show_id",
                    "event_id",
                    "id",
                    "source_url",
                    "url",
                    "starts_at",
                    "starts_at_local",
                ),
            )
            return {
                "target_show_key": target_key or f"um:{show_date.isoformat()}",
                "target_show_date": show_date.isoformat(),
                "reference_date": show_date.isoformat(),
            }

    return None


def generate_live_predictions(
    *,
    band: str,
    model: str,
    exclusion_window: int | None = None,
    require_output: bool = False,
    today: date | None = None,
) -> bool:
    """Generate and store one active next-show prediction board."""
    band = band.lower()
    model = model.lower()
    log_prefix = f"[{band.upper()}/{model.upper()}]"

    print(f"{log_prefix} Fetching raw data for live next-show prediction...")
    shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
    setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))
    upcoming_df: pd.DataFrame | None = None
    if band == "um":
        try:
            upcoming_df = pd.DataFrame(fetch_table("um_upcoming_shows"))
        except Exception as exc:  # pragma: no cover - live Supabase connectivity
            print(f"{log_prefix} Warning: could not load UM upcoming shows ({exc}).")

    if shows_df.empty or setlists_df.empty:
        message = f"{log_prefix} Error: could not fetch raw data."
        print(message)
        if require_output:
            raise RuntimeError(message)
        return False

    shows_df, setlists_df = prepare_band_data(shows_df, setlists_df, band=band)
    target = _resolve_next_show(band, shows_df, upcoming_df=upcoming_df, today=today)
    if target is None:
        message = f"{log_prefix} No upcoming show found; no live board written."
        print(message)
        if require_output:
            raise RuntimeError(message)
        return False

    reference_date = datetime.strptime(target["reference_date"], "%Y-%m-%d").date()
    model_definition = get_model_definition(model)
    predictor_kwargs: dict[str, Any] = {}
    if model_definition.supports_training:
        predictor_kwargs["persist_artifacts"] = False
    predictor = build_predictor(model, band=band, **predictor_kwargs)

    model_data = generate_model_data(
        shows_df,
        setlists_df,
        reference_date,
        exclusion_window=exclusion_window,
        band=band,
    )
    if model_definition.supports_training:
        predictor.train(model_data)
    output = predictor.predict(
        model_data=model_data, top_k=model_definition.default_top_k
    )
    predictions = output[0] if isinstance(output, tuple) else output
    if not predictions:
        message = f"{log_prefix} No live predictions were generated."
        print(message)
        if require_output:
            raise RuntimeError(message)
        return False

    predictions_list = json.loads(
        json.dumps(serialize_model_predictions(model, predictions), cls=NpEncoder)
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    run_id = upsert_next_show_prediction_run(
        band=band,
        model_slug=model,
        model_version=model_definition.version,
        target_show_key=target["target_show_key"],
        target_show_date=target["target_show_date"],
        reference_date=target["reference_date"],
        generated_at=generated_at,
        predictions=predictions_list,
        table_name=NEXT_SHOW_PREDICTION_RUNS_TABLE,
    )
    replace_next_show_prediction_projection(
        band=band,
        model_slug=model,
        model_version=model_definition.version,
        target_show_key=target["target_show_key"],
        target_show_date=target["target_show_date"],
        reference_date=target["reference_date"],
        generated_at=generated_at,
        predictions=predictions_list,
        prediction_run_id=run_id,
        table_name=NEXT_SHOW_PREDICTION_SONGS_TABLE,
    )
    print(
        f"{log_prefix} Saved live next-show prediction for {target['target_show_date']}."
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate active live next-show predictions."
    )
    parser.add_argument("--band", required=True, choices=get_repo_supported_bands())
    parser.add_argument(
        "--model",
        required=True,
        choices=[definition.slug for definition in list_pipeline_models()],
    )
    parser.add_argument("--exclusion-window", type=int, default=None)
    parser.add_argument("--require-output", action="store_true")
    args = parser.parse_args()

    generate_live_predictions(
        band=args.band,
        model=args.model,
        exclusion_window=args.exclusion_window,
        require_output=args.require_output,
    )


if __name__ == "__main__":
    main()
