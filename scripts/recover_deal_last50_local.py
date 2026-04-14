"""Local-first recovery for missing Deal last_50 historical data."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import timezone
from pathlib import Path
from typing import Any

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import batched_values
from scripts.export_backtest_snapshots import export_backtest_snapshots, parse_bands
from scripts.run_backtest import (
    build_prediction_rows_dataframe,
    build_scored_run_records,
    load_backtest_frames,
    persist_scored_run_records,
)
from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.models.evaluation import list_completed_shows, select_target_shows
from src.jambandnerd.models.model_test_cache import (
    LocalModelTestCache,
    build_default_cache_dir,
    build_experiment_cache_identity,
)
from src.jambandnerd.models.registry import (
    get_model_definition,
)

DEFAULT_RECOVERY_BANDS = ["phish", "billy", "um", "wsp"]
DEFAULT_RECOVERY_ROOT = Path("/tmp/jbn-deal-last50-recovery")
RECOVERY_MANIFEST_NAME = "deal_last50_recovery_manifest.json"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temp_path.replace(path)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid JSON object payload: {path}")
    return payload


def _recovery_manifest_path(recovery_root: Path) -> Path:
    return recovery_root / RECOVERY_MANIFEST_NAME


def _load_recovery_manifest(recovery_root: Path) -> dict[str, Any]:
    path = _recovery_manifest_path(recovery_root)
    if not path.exists():
        return {
            "generated_at": None,
            "bands": {},
        }
    return _load_json(path)


def _save_recovery_manifest(recovery_root: Path, payload: dict[str, Any]) -> None:
    path = _recovery_manifest_path(recovery_root)
    _write_json_atomic(path, payload)


def _bundle_path(results_root: Path, band: str) -> Path:
    return results_root / f"{band}_deal_last50_bundle.json"


def _cache_for_band(recovery_root: Path, band: str) -> LocalModelTestCache:
    identity = build_experiment_cache_identity(
        candidate_model="deal",
        baseline_models=["ckplus", "notebook"],
        bands=[band],
        windows=[{"label": "last_50", "shows": 50}],
        exclusion_window=3,
        feature_set_label="deal_last50_recovery",
        fresh_training=True,
    )
    cache_dir = build_default_cache_dir(
        identity=identity,
        cache_root=recovery_root / "cache",
    )
    return LocalModelTestCache(cache_dir=cache_dir, experiment_identity=identity)


def build_band_bundle(
    *,
    band: str,
    snapshot_root: Path,
    recovery_root: Path,
) -> dict[str, Any]:
    """Build the local scored-run bundle for one band."""

    shows_df, setlists_df = load_backtest_frames(
        band,
        snapshot_root=str(snapshot_root),
    )
    if shows_df.empty or setlists_df.empty:
        raise RuntimeError(f"No snapshot data available for {band}")

    completed_shows = list_completed_shows(shows_df, setlists_df)
    target_shows = select_target_shows(completed_shows, shows=50)
    cache = _cache_for_band(recovery_root, band)
    scored_runs = build_scored_run_records(
        band=band,
        model="deal",
        shows_df=shows_df,
        sets_df=setlists_df,
        target_shows=target_shows,
        exclusion_window=3,
        local_cache=cache,
    )
    prediction_rows_df = build_prediction_rows_dataframe(scored_runs)

    bundle = {
        "band": band,
        "model_slug": "deal",
        "model_version": get_model_definition("deal").version,
        "requested_window": "last_50",
        "shows_selected": len(target_shows),
        "shows_scored": len(scored_runs),
        "reference_dates": (
            prediction_rows_df["reference_date"].tolist()
            if not prediction_rows_df.empty
            else []
        ),
        "target_show_dates": [
            str(value) for value in target_shows["show_date"].tolist()
        ],
        "cache_summary": cache.build_summary(),
        "generated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
        "scored_runs": scored_runs,
    }
    return bundle


def write_band_bundle(results_root: Path, band: str, bundle: dict[str, Any]) -> Path:
    """Persist one band bundle to disk."""

    path = _bundle_path(results_root, band)
    _write_json_atomic(path, bundle)
    return path


def load_band_bundle(results_root: Path, band: str) -> dict[str, Any]:
    """Load one band bundle from disk."""

    path = _bundle_path(results_root, band)
    if not path.exists():
        raise FileNotFoundError(f"Missing bundle for {band}: {path}")
    return _load_json(path)


def validate_band_bundle(bundle: dict[str, Any]) -> None:
    """Validate that a local band bundle has enough structure to upload."""

    scored_runs = bundle.get("scored_runs")
    if not isinstance(scored_runs, list) or not scored_runs:
        raise RuntimeError(f"{bundle.get('band')}: scored_runs bundle is empty")

    band = bundle.get("band")
    model_slug = bundle.get("model_slug")
    model_version = bundle.get("model_version")
    if band is None or model_slug != "deal" or not model_version:
        raise RuntimeError(f"{band}: invalid bundle metadata")

    unique_keys = {
        (str(run["reference_date"]), str(run["show_id"])) for run in scored_runs
    }
    if len(unique_keys) != len(scored_runs):
        raise RuntimeError(f"{band}: duplicate scored run contexts detected")

    for run in scored_runs:
        if not run.get("predictions"):
            raise RuntimeError(f"{band}: empty predictions in scored run bundle")
        if not run.get("actual_songs"):
            raise RuntimeError(f"{band}: empty actual_songs in scored run bundle")
        if "metrics" not in run:
            raise RuntimeError(f"{band}: missing metrics in scored run bundle")


def upload_band_bundle(bundle: dict[str, Any]) -> None:
    """Upload one validated band bundle to Supabase."""

    validate_band_bundle(bundle)

    band = str(bundle["band"])
    model_definition = get_model_definition("deal")
    scored_runs = list(bundle["scored_runs"])
    prediction_rows_df = build_prediction_rows_dataframe(scored_runs)
    if prediction_rows_df.empty:
        raise RuntimeError(f"{band}: no canonical prediction rows to upload")

    upsert_dataframe(
        table_name=model_definition.prediction_table,
        df=prediction_rows_df,
        conflict_columns=["band", "reference_date", "model_version"],
    )
    persist_scored_run_records(scored_runs)


def _count_distinct_matches(
    *,
    table_name: str,
    band: str,
    match_column: str,
    values: list[str],
    extra_eq_filters: list[tuple[str, Any]] | None = None,
) -> int:
    client = get_supabase_client()
    matched: set[str] = set()
    for batch in batched_values(values, batch_size=50):
        query = client.table(table_name).select(match_column).eq("band", band)
        for column, value in extra_eq_filters or []:
            query = query.eq(column, value)
        response = query.in_(match_column, batch).execute()
        matched.update(
            str(row[match_column])
            for row in (response.data or [])
            if row.get(match_column) is not None
        )
    return len(matched)


def verify_uploaded_band(bundle: dict[str, Any]) -> None:
    """Verify that the uploaded bundle is visible in Supabase."""

    band = str(bundle["band"])
    model_version = str(bundle["model_version"])
    scored_runs = list(bundle["scored_runs"])
    prediction_rows_df = build_prediction_rows_dataframe(scored_runs)

    reference_dates = prediction_rows_df["reference_date"].astype(str).tolist()
    show_ids = [str(run["show_id"]) for run in scored_runs]

    prediction_count = _count_distinct_matches(
        table_name=get_model_definition("deal").prediction_table,
        band=band,
        match_column="reference_date",
        values=reference_dates,
        extra_eq_filters=[("model_version", model_version)],
    )
    if prediction_count < len(reference_dates):
        raise RuntimeError(
            f"{band}: expected {len(reference_dates)} prediction rows, found {prediction_count}"
        )

    historical_count = _count_distinct_matches(
        table_name="historical_prediction_runs",
        band=band,
        match_column="target_show_id",
        values=show_ids,
        extra_eq_filters=[
            ("model_slug", "deal"),
            ("model_version", model_version),
        ],
    )
    if historical_count < len(show_ids):
        raise RuntimeError(
            f"{band}: expected {len(show_ids)} replay rows, found {historical_count}"
        )

    accuracy_count = _count_distinct_matches(
        table_name="accuracy_per_show",
        band=band,
        match_column="show_id",
        values=show_ids,
        extra_eq_filters=[("model_version", model_version)],
    )
    if accuracy_count < len(show_ids):
        raise RuntimeError(
            f"{band}: expected {len(show_ids)} accuracy rows, found {accuracy_count}"
        )


def recover_deal_last50_local(
    *,
    bands: list[str],
    recovery_root: Path,
    refresh_snapshots: bool,
    rebuild_bundles: bool,
    dry_run: bool,
    cleanup: bool,
) -> None:
    """Run the local-first Deal last_50 recovery for the requested bands."""

    recovery_root.mkdir(parents=True, exist_ok=True)
    snapshot_root = recovery_root / "snapshots"
    results_root = recovery_root / "results"
    results_root.mkdir(parents=True, exist_ok=True)

    if refresh_snapshots or not snapshot_root.exists():
        export_backtest_snapshots(
            bands=bands,
            snapshot_root=str(snapshot_root),
        )

    manifest = _load_recovery_manifest(recovery_root)
    for band in bands:
        band_state = dict(manifest.get("bands", {}).get(band, {}))
        if band_state.get("complete"):
            print(f"[{band.upper()}] Recovery already complete. Skipping.")
            continue

        if rebuild_bundles or not _bundle_path(results_root, band).exists():
            print(f"[{band.upper()}] Building local scored-run bundle...")
            bundle = build_band_bundle(
                band=band,
                snapshot_root=snapshot_root,
                recovery_root=recovery_root,
            )
            bundle_path = write_band_bundle(results_root, band, bundle)
        else:
            print(f"[{band.upper()}] Reusing existing local bundle...")
            bundle_path = _bundle_path(results_root, band)
            bundle = load_band_bundle(results_root, band)

        validate_band_bundle(bundle)
        band_state.update(
            {
                "bundle_path": str(bundle_path),
                "shows_scored": int(bundle["shows_scored"]),
                "reference_dates": list(bundle["reference_dates"]),
                "local_bundle_ready": True,
            }
        )
        manifest.setdefault("bands", {})[band] = band_state
        _save_recovery_manifest(recovery_root, manifest)

        if dry_run:
            print(
                f"[{band.upper()}] Dry run: built bundle with {bundle['shows_scored']} scored shows."
            )
            continue

        print(f"[{band.upper()}] Uploading local bundle to Supabase...")
        upload_band_bundle(bundle)
        print(f"[{band.upper()}] Verifying uploaded rows...")
        verify_uploaded_band(bundle)

        band_state.update(
            {
                "uploaded": True,
                "aggregate_accuracy_saved": True,
                "complete": True,
            }
        )
        manifest.setdefault("bands", {})[band] = band_state
        _save_recovery_manifest(recovery_root, manifest)

    if cleanup and not dry_run:
        shutil.rmtree(recovery_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recover missing Deal last_50 historical data using local snapshots."
    )
    parser.add_argument(
        "--band",
        default=",".join(DEFAULT_RECOVERY_BANDS),
        help=(
            "Comma-separated band list or 'all'. Defaults to the unresolved Deal "
            "last_50 bands."
        ),
    )
    parser.add_argument(
        "--recovery-root",
        default=str(DEFAULT_RECOVERY_ROOT),
        help="Local working directory for snapshots, caches, bundles, and manifest state.",
    )
    parser.add_argument(
        "--refresh-snapshots",
        action="store_true",
        help="Re-export raw table snapshots before scoring.",
    )
    parser.add_argument(
        "--rebuild-bundles",
        action="store_true",
        help="Ignore existing local bundles and rebuild them from snapshots.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate local bundles without uploading to Supabase.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the local recovery directory after a successful upload run.",
    )
    args = parser.parse_args()

    bands = parse_bands(args.band)
    recover_deal_last50_local(
        bands=bands,
        recovery_root=Path(args.recovery_root),
        refresh_snapshots=args.refresh_snapshots,
        rebuild_bundles=args.rebuild_bundles,
        dry_run=args.dry_run,
        cleanup=args.cleanup,
    )


if __name__ == "__main__":
    main()
