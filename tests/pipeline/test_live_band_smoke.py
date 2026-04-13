from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from .fixtures import BANDS
from .live_helpers import (
    assert_accuracy_publish_fresh,
    assert_prediction_publish_fresh,
    ensure_live_env,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.live
@pytest.mark.parametrize("band", BANDS)
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

    assert "Successfully completed pipeline" in result.stdout

    for model in ("notebook", "deal"):
        assert_prediction_publish_fresh(
            band=band,
            model=model,
            started_at=started_at,
        )
        assert_accuracy_publish_fresh(
            band=band,
            model=model,
            started_at=started_at,
        )
