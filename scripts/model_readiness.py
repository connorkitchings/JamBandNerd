"""Canonical readiness workflow for future model promotion."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timezone
from pathlib import Path
from typing import Any

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.compare_models import generate_report as generate_comparison_report
from scripts.export_backtest_snapshots import export_backtest_snapshots, parse_bands
from scripts.run_backtest import (
    build_prediction_rows_dataframe,
    build_scored_run_records,
    load_backtest_frames,
    persist_scored_run_records,
    summarize_scored_run_records,
)
from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.models.evaluation import list_completed_shows, select_target_shows
from src.jambandnerd.models.model_test_cache import (
    LocalModelTestCache,
    build_default_cache_dir,
    build_experiment_cache_identity,
)
from src.jambandnerd.models.readiness import build_model_readiness_report
from src.jambandnerd.models.registry import (
    get_model_definition,
    list_model_slugs,
)

DEFAULT_ARTIFACT_ROOT = Path("artifacts/model_readiness")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temp_path.replace(path)


def _artifact_root(model_slug: str, artifact_root: Path | None) -> Path:
    root = artifact_root or DEFAULT_ARTIFACT_ROOT
    return root / model_slug


def _cache_for_band(
    *,
    model_slug: str,
    band: str,
    recovery_root: Path,
    windows: tuple[int, ...],
    baselines: tuple[str, ...],
) -> LocalModelTestCache:
    identity = build_experiment_cache_identity(
        candidate_model=model_slug,
        baseline_models=list(baselines),
        bands=[band],
        windows=[{"label": f"last_{window}", "shows": window} for window in windows],
        exclusion_window=3,
        feature_set_label="model_readiness",
        fresh_training=True,
    )
    cache_dir = build_default_cache_dir(
        identity=identity,
        cache_root=recovery_root / "cache",
    )
    return LocalModelTestCache(cache_dir=cache_dir, experiment_identity=identity)


def _build_band_bundle(
    *,
    model_slug: str,
    band: str,
    snapshot_root: Path,
    recovery_root: Path,
) -> dict[str, Any]:
    definition = get_model_definition(model_slug)
    required_window = max(definition.readiness_windows or (50,))
    shows_df, setlists_df = load_backtest_frames(
        band,
        snapshot_root=str(snapshot_root),
    )
    if shows_df.empty or setlists_df.empty:
        raise RuntimeError(f"No snapshot data available for {band}")

    completed_shows = list_completed_shows(shows_df, setlists_df)
    target_shows = select_target_shows(completed_shows, shows=required_window)
    cache = _cache_for_band(
        model_slug=model_slug,
        band=band,
        recovery_root=recovery_root,
        windows=definition.readiness_windows,
        baselines=definition.readiness_baselines,
    )
    scored_runs = build_scored_run_records(
        band=band,
        model=model_slug,
        shows_df=shows_df,
        sets_df=setlists_df,
        target_shows=target_shows,
        exclusion_window=3,
        local_cache=cache,
    )
    prediction_rows_df = build_prediction_rows_dataframe(scored_runs)
    return {
        "band": band,
        "model_slug": model_slug,
        "model_version": definition.version,
        "required_window": required_window,
        "shows_selected": len(target_shows),
        "shows_scored": len(scored_runs),
        "reference_dates": (
            prediction_rows_df["reference_date"].tolist()
            if not prediction_rows_df.empty
            else []
        ),
        "generated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
        "cache_summary": cache.build_summary(),
        "summary": summarize_scored_run_records(scored_runs) if scored_runs else {},
        "scored_runs": scored_runs,
    }


def _bundle_path(recovery_root: Path, model_slug: str, band: str) -> Path:
    return recovery_root / "results" / f"{model_slug}_{band}_readiness_bundle.json"


def _publish_band_bundle(bundle: dict[str, Any]) -> None:
    definition = get_model_definition(str(bundle["model_slug"]))
    scored_runs = list(bundle["scored_runs"])
    prediction_rows_df = build_prediction_rows_dataframe(scored_runs)
    if prediction_rows_df.empty:
        raise RuntimeError(f"{bundle['band']}: no canonical prediction rows to upload")

    upsert_dataframe(
        table_name=definition.prediction_table,
        df=prediction_rows_df,
        conflict_columns=["band", "reference_date", "model_version"],
    )
    persist_scored_run_records(scored_runs)


def _run_compare_phase(
    *,
    model_slug: str,
    bands: list[str],
    artifact_root: Path,
    feature_set_label: str,
) -> dict[str, Any]:
    definition = get_model_definition(model_slug)
    report = generate_comparison_report(
        candidate_model=model_slug,
        baseline_models=list(definition.readiness_baselines),
        bands=bands,
        windows=[
            {"label": f"last_{window}", "shows": window}
            for window in definition.readiness_windows
        ],
        exclusion_window=3,
        feature_set_label=feature_set_label,
        fresh_training=True,
        include_candidate_diagnostics=True,
    )
    report_path = artifact_root / "comparison_report.json"
    _write_json_atomic(report_path, report)
    return {"path": str(report_path), "report": report}


def _run_snapshot_phase(*, bands: list[str], artifact_root: Path) -> dict[str, Any]:
    snapshot_root = artifact_root / "snapshots"
    manifest = export_backtest_snapshots(
        bands=bands,
        snapshot_root=str(snapshot_root),
    )
    manifest_path = artifact_root / "snapshot_manifest.json"
    _write_json_atomic(manifest_path, manifest)
    return {"path": str(manifest_path), "manifest": manifest}


def _run_backfill_history_phase(
    *,
    model_slug: str,
    bands: list[str],
    artifact_root: Path,
    dry_run: bool,
    rebuild_bundles: bool,
) -> dict[str, Any]:
    snapshot_root = artifact_root / "snapshots"
    recovery_root = artifact_root / "recovery"
    recovery_root.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {"bands": {}}

    if not snapshot_root.exists():
        export_backtest_snapshots(bands=bands, snapshot_root=str(snapshot_root))

    for band in bands:
        bundle_path = _bundle_path(recovery_root, model_slug, band)
        if bundle_path.exists() and not rebuild_bundles:
            bundle = json.loads(bundle_path.read_text())
        else:
            bundle = _build_band_bundle(
                model_slug=model_slug,
                band=band,
                snapshot_root=snapshot_root,
                recovery_root=recovery_root,
            )
            _write_json_atomic(bundle_path, bundle)

        if not dry_run:
            _publish_band_bundle(bundle)

        results["bands"][band] = {
            "bundle_path": str(bundle_path),
            "shows_scored": bundle["shows_scored"],
            "uploaded": not dry_run,
        }

    history_path = artifact_root / "history_publish_report.json"
    _write_json_atomic(history_path, results)
    return {"path": str(history_path), "report": results}


def _run_validate_phase(
    *,
    model_slug: str,
    bands: list[str],
    artifact_root: Path,
) -> dict[str, Any]:
    report = build_model_readiness_report(model_slug, bands=bands)
    report_path = artifact_root / "backend_readiness_report.json"
    _write_json_atomic(report_path, report)
    return {"path": str(report_path), "report": report}


def run_model_readiness(
    *,
    model_slug: str,
    bands: list[str],
    phase: str,
    artifact_root: Path | None = None,
    feature_set_label: str = "shared_core_v1",
    dry_run: bool = False,
    rebuild_bundles: bool = False,
) -> dict[str, Any]:
    """Run one readiness phase or the full readiness flow for a model."""

    artifact_dir = _artifact_root(model_slug, artifact_root)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "model_slug": model_slug,
        "bands": bands,
        "phase": phase,
        "artifact_root": str(artifact_dir),
    }

    if phase in {"report-only", "validate", "full-readiness"}:
        result["initial_report"] = build_model_readiness_report(
            model_slug,
            bands=bands,
        )

    if phase in {"compare", "full-readiness"}:
        result["comparison"] = _run_compare_phase(
            model_slug=model_slug,
            bands=bands,
            artifact_root=artifact_dir,
            feature_set_label=feature_set_label,
        )

    if phase in {"snapshot", "full-readiness"}:
        result["snapshots"] = _run_snapshot_phase(
            bands=bands,
            artifact_root=artifact_dir,
        )

    if phase in {"backfill-history", "full-readiness"}:
        result["history_publish"] = _run_backfill_history_phase(
            model_slug=model_slug,
            bands=bands,
            artifact_root=artifact_dir,
            dry_run=dry_run,
            rebuild_bundles=rebuild_bundles,
        )

    if phase in {"report-only", "validate", "full-readiness"}:
        result["validation"] = _run_validate_phase(
            model_slug=model_slug,
            bands=bands,
            artifact_root=artifact_dir,
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the canonical model readiness workflow."
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=list_model_slugs(),
        help="Registered model slug to prepare for readiness/promotion.",
    )
    parser.add_argument(
        "--band",
        default="all",
        help="Band slug, comma-separated list, or 'all' (default).",
    )
    parser.add_argument(
        "--phase",
        choices=[
            "report-only",
            "compare",
            "snapshot",
            "backfill-history",
            "validate",
            "full-readiness",
        ],
        default="report-only",
        help="Readiness phase to execute.",
    )
    parser.add_argument(
        "--artifact-root",
        help="Optional root directory for readiness artifacts.",
    )
    parser.add_argument(
        "--feature-set-label",
        default="shared_core_v1",
        help="Feature-set label recorded in comparison artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build local bundles without publishing historical rows.",
    )
    parser.add_argument(
        "--rebuild-bundles",
        action="store_true",
        help="Force a rebuild of cached local readiness bundles.",
    )
    args = parser.parse_args()

    result = run_model_readiness(
        model_slug=args.model,
        bands=parse_bands(args.band),
        phase=args.phase,
        artifact_root=Path(args.artifact_root) if args.artifact_root else None,
        feature_set_label=args.feature_set_label,
        dry_run=args.dry_run,
        rebuild_bundles=args.rebuild_bundles,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
