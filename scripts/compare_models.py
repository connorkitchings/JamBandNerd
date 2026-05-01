"""Compare a candidate prediction model against fixed baseline models."""

from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data, resolve_reference_date
from src.jambandnerd.config.bands import get_repo_supported_bands
from src.jambandnerd.models.comparison import (
    build_cross_band_summary,
    build_delta_summary,
    build_evaluation_predictor,
    build_promotion_gate,
    extract_experiment_metadata,
    maybe_build_model_diagnostics,
    score_model_on_target_shows,
    summarize_scored_rows,
)
from src.jambandnerd.models.evaluation import list_completed_shows, select_target_shows
from src.jambandnerd.models.registry import (
    get_model_definition,
    list_backtest_models,
)

DEFAULT_BASELINES = ("deal", "notebook")
DEFAULT_WINDOWS = ("50",)


@dataclass
class BandComparisonContext:
    band: str
    shows_df: pd.DataFrame
    setlists_df: pd.DataFrame
    completed_shows: pd.DataFrame
    upcoming_df: pd.DataFrame | None = None
    reference_date: Any | None = None


def _log_progress(message: str) -> None:
    """Write progress updates to stderr so stdout stays valid JSON."""

    print(message, file=sys.stderr, flush=True)


def _parse_bands(raw_band: str) -> list[str]:
    if raw_band == "all":
        return list(get_repo_supported_bands())
    return [band.strip() for band in raw_band.split(",") if band.strip()]


def _parse_window_specs(raw_windows: list[str]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for raw_window in raw_windows:
        normalized = raw_window.strip().lower()
        try:
            window_size = int(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported window spec: {raw_window}") from exc
        if window_size <= 0:
            raise ValueError(f"Window must be a positive integer: {raw_window}")

        specs.append(
            {
                "label": f"last_{window_size}",
                "shows": window_size,
            }
        )
    return specs


def _serialize_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def _write_json_report(output_path: Path, report: dict[str, Any]) -> None:
    payload = _serialize_report(report)
    if not payload.strip():
        raise RuntimeError(f"Refusing to write an empty report to {output_path}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temp_path.write_text(payload + "\n")

    written_payload = temp_path.read_text()
    if not written_payload.strip():
        raise RuntimeError(f"Wrote an empty report payload to {temp_path}.")
    try:
        json.loads(written_payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Wrote invalid JSON while saving report to {temp_path}."
        ) from exc

    temp_path.replace(output_path)
    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise RuntimeError(f"Expected a non-empty report artifact at {output_path}.")


def _window_labels(windows: list[dict[str, Any]]) -> list[str]:
    return [window["label"] for window in windows]


def _build_empty_window_report() -> dict[str, Any]:
    return {
        "metrics_by_band": {},
        "cross_band_summary": {},
        "deltas": {},
        "promotion_gate": {
            "candidate_model": "",
            "baseline_model": "",
            "passes": False,
            "reason": "missing_summary",
        },
    }


def _build_base_report(
    *,
    candidate_model: str,
    baseline_models: list[str],
    requested_bands: list[str],
    windows: list[dict[str, Any]],
    exclusion_window: int,
    feature_set_label: str,
    fresh_training: bool,
    candidate_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_definition = get_model_definition(candidate_model)
    candidate_predictor = build_evaluation_predictor(
        candidate_model,
        band=requested_bands[0],
        fresh_training=fresh_training,
        candidate_overrides=candidate_overrides,
    )

    return {
        "candidate_model": {
            "slug": candidate_definition.slug,
            "version": candidate_definition.version,
        },
        "baseline_models": [
            {
                "slug": get_model_definition(model_slug).slug,
                "version": get_model_definition(model_slug).version,
            }
            for model_slug in baseline_models
        ],
        "experiment_metadata": extract_experiment_metadata(
            model_slug=candidate_model,
            predictor=candidate_predictor,
            feature_set_label=feature_set_label,
            exclusion_window=exclusion_window,
            window_labels=_window_labels(windows),
            fresh_training=fresh_training,
            candidate_overrides=candidate_overrides,
        ),
        "requested_bands": list(requested_bands),
        "completed_bands": [],
        "report_status": "partial",
        "windows": {
            window["label"]: _build_empty_window_report() for window in windows
        },
    }


def _load_resumable_report(
    output_path: Path,
    *,
    candidate_model: str,
    baseline_models: list[str],
    requested_bands: list[str],
    windows: list[dict[str, Any]],
    exclusion_window: int,
    feature_set_label: str,
    fresh_training: bool,
    candidate_overrides: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not output_path.exists():
        return None

    try:
        existing_report = json.loads(output_path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Existing comparison report is invalid JSON: {output_path}"
        ) from exc

    if not isinstance(existing_report, dict):
        raise RuntimeError(
            f"Existing comparison report has an unsupported shape: {output_path}"
        )

    if existing_report.get("report_status") != "partial":
        return None

    candidate_payload = existing_report.get("candidate_model", {})
    if candidate_payload.get("slug") != candidate_model:
        raise RuntimeError(f"Cannot resume {output_path}: candidate model mismatch.")

    existing_baselines = [
        entry.get("slug") for entry in existing_report.get("baseline_models", [])
    ]
    if existing_baselines != baseline_models:
        raise RuntimeError(f"Cannot resume {output_path}: baseline model mismatch.")

    if existing_report.get("requested_bands") != requested_bands:
        raise RuntimeError(f"Cannot resume {output_path}: requested bands mismatch.")

    metadata = existing_report.get("experiment_metadata", {})
    if metadata.get("evaluation_windows") != _window_labels(windows):
        raise RuntimeError(f"Cannot resume {output_path}: evaluation window mismatch.")
    if metadata.get("exclusion_window") != exclusion_window:
        raise RuntimeError(f"Cannot resume {output_path}: exclusion window mismatch.")
    if metadata.get("feature_set_label") != feature_set_label:
        raise RuntimeError(f"Cannot resume {output_path}: feature set mismatch.")
    if metadata.get("fresh_training") != fresh_training:
        raise RuntimeError(f"Cannot resume {output_path}: training mode mismatch.")
    if metadata.get("candidate_overrides") != (candidate_overrides or None):
        raise RuntimeError(
            f"Cannot resume {output_path}: candidate overrides mismatch."
        )

    completed_bands = existing_report.get("completed_bands", [])
    if not isinstance(completed_bands, list) or any(
        band not in requested_bands for band in completed_bands
    ):
        raise RuntimeError(f"Cannot resume {output_path}: completed band list invalid.")

    for window in windows:
        if window["label"] not in existing_report.get("windows", {}):
            raise RuntimeError(
                f"Cannot resume {output_path}: missing window {window['label']}."
            )

    return deepcopy(existing_report)


def _load_band_contexts(
    *,
    bands: list[str],
    include_candidate_diagnostics: bool,
) -> list[BandComparisonContext]:
    contexts: list[BandComparisonContext] = []
    for band in bands:
        _log_progress(f"[compare] Loading raw tables for {band}...")
        shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
        setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))
        upcoming_df: pd.DataFrame | None = None
        if band == "um":
            try:
                upcoming_df = pd.DataFrame(fetch_table("um_upcoming_shows"))
            except Exception:
                upcoming_df = None

        if shows_df.empty or setlists_df.empty:
            _log_progress(
                f"[compare] Skipping {band}: missing raw data after fetch/prepare."
            )
            continue

        _log_progress(
            f"[compare] Preparing normalized inputs for {band} "
            f"(shows={len(shows_df)}, setlists={len(setlists_df)})..."
        )
        prepared_shows, prepared_setlists = prepare_band_data(
            shows_df,
            setlists_df,
            band=band,
        )
        completed_shows = list_completed_shows(prepared_shows, prepared_setlists)
        if completed_shows.empty:
            _log_progress(f"[compare] Skipping {band}: no completed shows.")
            continue

        reference_date = None
        if include_candidate_diagnostics:
            reference_date = resolve_reference_date(
                None,
                prepared_shows,
                upcoming_df=upcoming_df,
            )

        contexts.append(
            BandComparisonContext(
                band=band,
                shows_df=prepared_shows,
                setlists_df=prepared_setlists,
                completed_shows=completed_shows,
                upcoming_df=upcoming_df,
                reference_date=reference_date,
            )
        )
    return contexts


def _extract_diagnostics_by_band(report: dict[str, Any]) -> dict[str, Any]:
    diagnostics_by_band: dict[str, Any] = {}
    for window_report in report.get("windows", {}).values():
        diagnostics_by_band.update(window_report.get("candidate_diagnostics", {}))
    return diagnostics_by_band


def _refresh_window_reports(
    *,
    report: dict[str, Any],
    candidate_model: str,
    baseline_models: list[str],
    diagnostics_by_band: dict[str, Any],
) -> None:
    model_slugs = [candidate_model, *baseline_models]
    for window_report in report["windows"].values():
        metrics_by_band = window_report.get("metrics_by_band", {})
        cross_band_summary = build_cross_band_summary(
            metrics_by_band,
            model_slugs=model_slugs,
        )
        window_report["cross_band_summary"] = cross_band_summary
        window_report["deltas"] = {
            f"vs_{baseline_slug}": build_delta_summary(
                metrics_by_band,
                candidate_slug=candidate_model,
                baseline_slug=baseline_slug,
                cross_band_summary=cross_band_summary,
            )
            for baseline_slug in baseline_models
        }
        window_report["promotion_gate"] = build_promotion_gate(
            metrics_by_band=metrics_by_band,
            cross_band_summary=cross_band_summary,
            candidate_slug=candidate_model,
            baseline_slug=baseline_models[0] if baseline_models else None,
        )
        if diagnostics_by_band:
            window_report["candidate_diagnostics"] = dict(diagnostics_by_band)
        else:
            window_report.pop("candidate_diagnostics", None)


def _mark_band_completed(report: dict[str, Any], band: str) -> None:
    completed_bands = report.setdefault("completed_bands", [])
    if band not in completed_bands:
        completed_bands.append(band)
    requested_bands = report.get("requested_bands", [])
    report["report_status"] = (
        "complete" if completed_bands == requested_bands else "partial"
    )


def generate_report(
    *,
    candidate_model: str,
    baseline_models: list[str],
    bands: list[str],
    windows: list[dict[str, Any]],
    exclusion_window: int,
    feature_set_label: str,
    fresh_training: bool,
    include_candidate_diagnostics: bool,
    output_path: Path | None = None,
    existing_report: dict[str, Any] | None = None,
    candidate_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requested_bands = list(bands)
    report = (
        deepcopy(existing_report)
        if existing_report is not None
        else _build_base_report(
            candidate_model=candidate_model,
            baseline_models=baseline_models,
            requested_bands=requested_bands,
            windows=windows,
            exclusion_window=exclusion_window,
            feature_set_label=feature_set_label,
            fresh_training=fresh_training,
            candidate_overrides=candidate_overrides,
        )
    )
    diagnostics_by_band = _extract_diagnostics_by_band(report)
    completed_bands = report.get("completed_bands", [])
    pending_bands = [band for band in requested_bands if band not in completed_bands]

    if not pending_bands:
        _refresh_window_reports(
            report=report,
            candidate_model=candidate_model,
            baseline_models=baseline_models,
            diagnostics_by_band=diagnostics_by_band,
        )
        report["report_status"] = "complete"
        if output_path is not None:
            _write_json_report(output_path, report)
        return report

    band_contexts = _load_band_contexts(
        bands=pending_bands,
        include_candidate_diagnostics=include_candidate_diagnostics,
    )
    _log_progress(
        f"[compare] Loaded {len(band_contexts)} band contexts for "
        f"{candidate_model} vs {', '.join(baseline_models)}."
    )
    if not band_contexts:
        raise RuntimeError(
            "No band contexts were loaded. Check Supabase connectivity, credentials, "
            "and raw-table availability before generating a baseline report."
        )
    model_slugs = [candidate_model, *baseline_models]

    for context in band_contexts:
        if include_candidate_diagnostics and context.band not in diagnostics_by_band:
            _log_progress(
                f"[compare] Building candidate diagnostics for {context.band}..."
            )
            diagnostics = maybe_build_model_diagnostics(
                band=context.band,
                model_slug=candidate_model,
                shows_df=context.shows_df,
                setlists_df=context.setlists_df,
                reference_date=context.reference_date,
                exclusion_window=exclusion_window,
                fresh_training=fresh_training,
                candidate_overrides=candidate_overrides,
            )
            if diagnostics is not None:
                diagnostics_by_band[context.band] = diagnostics

        band_scored = False
        for window in windows:
            window_label = window["label"]
            window_report = report["windows"].setdefault(
                window_label, _build_empty_window_report()
            )
            target_shows = select_target_shows(
                context.completed_shows,
                shows=window["shows"],
            )
            if target_shows.empty:
                _log_progress(
                    f"[compare] {context.band} has no target shows for {window_label}."
                )
                continue

            _log_progress(
                f"[compare] {context.band}: scoring {len(target_shows)} shows for {window_label}."
            )
            metrics_by_band = window_report.setdefault("metrics_by_band", {})
            metrics_by_band[context.band] = {}
            for model_slug in model_slugs:
                _log_progress(
                    f"[compare] {context.band} {window_label}: running {model_slug}..."
                )
                scored_rows = score_model_on_target_shows(
                    band=context.band,
                    model_slug=model_slug,
                    shows_df=context.shows_df,
                    setlists_df=context.setlists_df,
                    target_shows=target_shows,
                    exclusion_window=exclusion_window,
                    fresh_training=fresh_training and model_slug == candidate_model,
                    candidate_overrides=(
                        candidate_overrides if model_slug == candidate_model else None
                    ),
                    progress_callback=lambda **progress: _log_progress(
                        "[compare] "
                        f"{context.band} {window_label} {progress['model_slug']}: "
                        f"show {progress['show_index']}/{progress['total_shows']} "
                        f"({progress['target_show_date'].isoformat()}, "
                        f"id={progress['show_id']})"
                    ),
                )
                metrics_by_band[context.band][model_slug] = summarize_scored_rows(
                    scored_rows
                )
                band_scored = True

        if not band_scored:
            _log_progress(
                f"[compare] {context.band} produced no scored rows for the requested windows."
            )
            continue

        _mark_band_completed(report, context.band)
        _refresh_window_reports(
            report=report,
            candidate_model=candidate_model,
            baseline_models=baseline_models,
            diagnostics_by_band=diagnostics_by_band,
        )
        if output_path is not None:
            _write_json_report(output_path, report)

    if not any(
        window_report.get("metrics_by_band")
        for window_report in report["windows"].values()
    ):
        raise RuntimeError(
            "No scored windows were produced. Check raw data availability and comparison inputs."
        )

    _refresh_window_reports(
        report=report,
        candidate_model=candidate_model,
        baseline_models=baseline_models,
        diagnostics_by_band=diagnostics_by_band,
    )
    report["report_status"] = (
        "complete"
        if report.get("completed_bands", []) == requested_bands
        else "partial"
    )
    if output_path is not None:
        _write_json_report(output_path, report)

    for window in windows:
        window_report = report["windows"][window["label"]]
        if not window_report.get("metrics_by_band"):
            raise RuntimeError(
                f"No scored windows were produced for {window['label']}. "
                "Check raw data availability and comparison inputs."
            )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a candidate model against fixed baseline models."
    )
    parser.add_argument(
        "--candidate-model",
        required=True,
        choices=[definition.slug for definition in list_backtest_models()],
    )
    parser.add_argument(
        "--band",
        default="all",
        help="Band slug, comma-separated band slugs, or 'all' (default).",
    )
    parser.add_argument(
        "--baseline-model",
        dest="baseline_models",
        action="append",
        help="Optional baseline override. Repeat to set multiple baselines.",
    )
    parser.add_argument(
        "--window",
        dest="windows",
        action="append",
        help="Comparison window as a positive integer show count. Defaults to 50.",
    )
    parser.add_argument(
        "--exclusion-window",
        type=int,
        default=3,
        help="Number of recent shows to exclude when generating comparison predictions.",
    )
    parser.add_argument(
        "--feature-set-label",
        default="shared_core_v1",
        help="Human-readable label for the feature set under test.",
    )
    parser.add_argument(
        "--fresh-training",
        action="store_true",
        help="Disable persisted artifacts for training-capable candidate models.",
    )
    parser.add_argument(
        "--include-candidate-diagnostics",
        action="store_true",
        help="Include optional candidate diagnostics when supported by the model.",
    )
    parser.add_argument("--output", help="Optional path to write the JSON report.")
    parser.add_argument(
        "--deal-overrides",
        default=None,
        help=(
            "JSON string of keyword arguments forwarded to the candidate Deal predictor. "
            "Example: '{\"min_plays_threshold\": 3}'"
        ),
    )
    args = parser.parse_args()

    band_list = _parse_bands(args.band)
    baseline_models = args.baseline_models or list(DEFAULT_BASELINES)
    window_specs = _parse_window_specs(args.windows or list(DEFAULT_WINDOWS))
    output_path = Path(args.output) if args.output else None

    candidate_overrides: dict[str, Any] | None = None
    if args.deal_overrides:
        try:
            candidate_overrides = json.loads(args.deal_overrides)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"--deal-overrides must be valid JSON. Got: {args.deal_overrides!r}"
            ) from exc
        if not isinstance(candidate_overrides, dict):
            raise ValueError("--deal-overrides must be a JSON object.")

    existing_report = None
    if output_path is not None:
        existing_report = _load_resumable_report(
            output_path,
            candidate_model=args.candidate_model,
            baseline_models=baseline_models,
            requested_bands=band_list,
            windows=window_specs,
            exclusion_window=args.exclusion_window,
            feature_set_label=args.feature_set_label,
            fresh_training=args.fresh_training,
            candidate_overrides=candidate_overrides,
        )
        if existing_report is not None:
            _log_progress(
                "[compare] Resuming partial report from "
                f"{output_path} with completed bands: "
                f"{', '.join(existing_report.get('completed_bands', [])) or 'none'}."
            )

    report = generate_report(
        candidate_model=args.candidate_model,
        baseline_models=baseline_models,
        bands=band_list,
        windows=window_specs,
        exclusion_window=args.exclusion_window,
        feature_set_label=args.feature_set_label,
        fresh_training=args.fresh_training,
        include_candidate_diagnostics=args.include_candidate_diagnostics,
        output_path=output_path,
        existing_report=existing_report,
        candidate_overrides=candidate_overrides,
    )
    output = _serialize_report(report)
    print(output)


if __name__ == "__main__":
    main()
