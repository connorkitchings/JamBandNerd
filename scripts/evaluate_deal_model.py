"""Produce an explainability-first evaluation report for the Deal model."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data, resolve_reference_date
from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.models.accuracy import aggregate_metrics, compute_per_show_metrics
from src.jambandnerd.models.registry import build_predictor, get_model_definition
from src.jambandnerd.transformations.gaps import generate_model_data


def load_legacy_reference() -> dict[str, float] | None:
    session_log = Path("session_logs/2026-03-27/50_show_backfill.md")
    if not session_log.exists():
        return None

    text = session_log.read_text()
    matches = re.findall(r"\|\s*(Notebook|CK\+|Deal)\s*\|\s*([0-9.]+)\s*\|", text)
    if not matches:
        return None

    return {
        label.lower().replace("+", "plus"): float(value) for label, value in matches
    }


def build_evaluation_predictor(model_slug: str, band: str):
    kwargs: dict[str, Any] = {}
    if model_slug == "deal":
        kwargs["persist_artifacts"] = False
    return build_predictor(model_slug, band=band, **kwargs)


def evaluate_model_window(
    *,
    band: str,
    model_slug: str,
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    show_rows: pd.DataFrame,
) -> dict[str, float]:
    model_definition = get_model_definition(model_slug)
    predictor = build_evaluation_predictor(model_slug, band)
    per_show: list[dict[str, float]] = []

    for _, show_row in show_rows.iterrows():
        reference_date = pd.Timestamp(show_row["show_date"]).date()
        model_data = generate_model_data(
            shows_df, setlists_df, reference_date, band=band
        )

        if model_definition.supports_training:
            predictor.train(model_data)

        predictions = predictor.predict(
            model_data=model_data,
            top_k=model_definition.default_top_k,
        )
        if isinstance(predictions, tuple):
            predictions = predictions[0]

        predicted_song_names = [prediction.song_name for prediction in predictions]
        actual_songs = (
            setlists_df[setlists_df["show_id"] == show_row["show_id"]]["song_name"]
            .astype(str)
            .tolist()
        )
        per_show.append(
            compute_per_show_metrics(predicted_song_names, actual_songs, 10)
        )

    metrics = aggregate_metrics(per_show, 10)
    return {
        "hit_rate": metrics.hit_rate,
        "avg_matches": metrics.avg_matches,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "shows": float(len(per_show)),
    }


def generate_report(band: str, shows: int) -> dict[str, Any]:
    shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
    setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))
    upcoming_df: pd.DataFrame | None = None
    if band == "um":
        try:
            upcoming_df = pd.DataFrame(fetch_table("um_upcoming_shows"))
        except Exception:
            upcoming_df = None

    shows_df, setlists_df = prepare_band_data(shows_df, setlists_df, band=band)
    reference_date = resolve_reference_date(None, shows_df, upcoming_df=upcoming_df)
    current_model_data = generate_model_data(
        shows_df, setlists_df, reference_date, band=band
    )
    deal_definition = get_model_definition("deal")
    deal_predictor = build_evaluation_predictor("deal", band)
    deal_predictor.train(current_model_data)
    report = deal_predictor.build_evaluation_report(current_model_data)

    completed_show_rows = (
        shows_df[
            pd.to_datetime(shows_df["show_date"], errors="coerce").dt.date
            < reference_date
        ]
        .sort_values("show_date")
        .tail(shows)
    )

    comparison = {
        model_slug: evaluate_model_window(
            band=band,
            model_slug=model_slug,
            shows_df=shows_df,
            setlists_df=setlists_df,
            show_rows=completed_show_rows,
        )
        for model_slug in ["deal", "ckplus", "notebook"]
    }

    deal_hit_rate = comparison["deal"]["hit_rate"]
    ckplus_hit_rate = comparison["ckplus"]["hit_rate"]
    legacy_reference = load_legacy_reference()

    report["comparison_window"] = {
        "shows": int(len(completed_show_rows)),
        "metrics": comparison,
        "deltas": {
            "deal_minus_ckplus": deal_hit_rate - ckplus_hit_rate,
            "deal_minus_notebook": deal_hit_rate - comparison["notebook"]["hit_rate"],
            "deal_minus_legacy_reference": (
                None
                if legacy_reference is None or "deal" not in legacy_reference
                else deal_hit_rate - legacy_reference["deal"]
            ),
        },
    }
    report["promotion_gate"] = {
        "model_slug": deal_definition.slug,
        "model_version": deal_definition.version,
        "enabled_for_web": deal_definition.enabled_for_web,
        "beats_legacy_deal_by_0_05": (
            False
            if legacy_reference is None or "deal" not in legacy_reference
            else deal_hit_rate >= legacy_reference["deal"] + 0.05
        ),
        "matches_or_beats_ckplus": deal_hit_rate >= ckplus_hit_rate,
    }
    report["legacy_reference"] = legacy_reference
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the Deal model and emit a JSON report."
    )
    parser.add_argument("--band", required=True, choices=get_active_bands())
    parser.add_argument("--shows", type=int, default=50)
    parser.add_argument("--output", help="Optional path to write the JSON report.")
    args = parser.parse_args()

    report = generate_report(args.band, args.shows)
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)

    if args.output:
        Path(args.output).write_text(output + "\n")


if __name__ == "__main__":
    main()
