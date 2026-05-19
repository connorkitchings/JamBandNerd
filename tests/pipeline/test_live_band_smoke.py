from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.jambandnerd.models.registry import list_active_bands

from .live_helpers import (
    assert_accuracy_publish_fresh,
    assert_prediction_publish_fresh,
    ensure_live_env,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
