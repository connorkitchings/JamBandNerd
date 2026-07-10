from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.models.registry import list_active_bands

from .live_helpers import (
    assert_accuracy_publish_fresh,
    assert_prediction_publish_fresh,
    ensure_live_env,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIVE_PIPELINE_TIMEOUT_SECONDS = 900


@pytest.mark.live
@pytest.mark.parametrize("band", list_active_bands())
def test_live_band_pipeline_smoke(band):
    try:
        ensure_live_env(band=band)
    except RuntimeError as exc:
        pytest.skip(str(exc))

    started_at = datetime.now(timezone.utc)
    result = subprocess.run(
        [sys.executable, "scripts/run_optimized_pipeline.py", "--band", band],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=LIVE_PIPELINE_TIMEOUT_SECONDS,
    )

    if result.returncode != 0:
        raise AssertionError(
            f"live pipeline failed for {band}\nstdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )

    combined_output = f"{result.stdout}\n{result.stderr}"
    assert "Successfully completed pipeline" in combined_output

    assert_prediction_publish_fresh(
        band=band,
        started_at=started_at,
    )
    assert_accuracy_publish_fresh(
        band=band,
        started_at=started_at,
    )


@pytest.mark.live
@pytest.mark.parametrize("band", list_active_bands())
def test_live_setlist_completeness(band):
    try:
        ensure_live_env(band=band)
    except RuntimeError as exc:
        pytest.skip(str(exc))

    client = get_supabase_client()
    today = datetime.now(timezone.utc).date()
    end_date = (today - timedelta(days=1)).isoformat()
    cutoff = (today - timedelta(days=8)).isoformat()

    shows_response = (
        client.table(f"{band}_shows_raw")
        .select("show_id, show_date")
        .gte("show_date", cutoff)
        .lte("show_date", end_date)
        .order("show_date", desc=True)
        .execute()
    )
    if not shows_response.data:
        pytest.skip(f"No recent completed shows for {band} in {cutoff} to {end_date}")

    show_ids = {str(row["show_id"]) for row in shows_response.data}
    if not show_ids:
        pytest.skip(f"No show_ids found for {band}")

    all_setlist_rows = []
    for chunk in [list(show_ids)[i : i + 50] for i in range(0, len(show_ids), 50)]:
        response = (
            client.table(f"{band}_setlists_raw")
            .select("show_id, song_name")
            .in_("show_id", chunk)
            .execute()
        )
        if response.data:
            all_setlist_rows.extend(response.data)

    setlists_df = pd.DataFrame(all_setlist_rows) if all_setlist_rows else pd.DataFrame()
    missing = show_ids - {str(r["show_id"]) for r in all_setlist_rows}
    partial = []
    if not setlists_df.empty:
        counts = (
            setlists_df.dropna(subset=["show_id", "song_name"])
            .assign(show_id=lambda d: d["show_id"].astype(str))
            .groupby("show_id")["song_name"]
            .nunique()
        )
        partial = [sid for sid in show_ids if counts.get(sid, 0) < 3]

    failures = []
    if missing:
        failures.append(
            f"missing setlist data for {len(missing)} shows: {sorted(missing)}"
        )
    if partial:
        failures.append(
            f"partial setlist data (<3 unique songs) for {len(partial)} shows: {sorted(partial)}"
        )
    assert not failures, f"{band}: " + "; ".join(failures)
