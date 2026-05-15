from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

import scripts.diagnose_phase_b_features as diagnostics
from jambandnerd.models.billy.fast_predictor import (
    BILLY_FAST_CANDIDATE_CONTEXT_COLS,
    BILLY_FAST_FEATURE_COLS,
    BillyFastPredictor,
)

_SONGS_DF = pd.DataFrame(
    [
        {"song_name": "Dust in a Baggie", "original_artist": None},
        {"song_name": "Away From the Mire", "original_artist": None},
        {"song_name": "Midnight Rider", "original_artist": "Allman Brothers Band"},
        {"song_name": "Shady Grove", "original_artist": "Traditional"},
        {"song_name": "Taking Water", "original_artist": None},
        {"song_name": "Enough to Leave", "original_artist": None},
    ]
)


def _billy_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    shows: list[dict] = []
    setlists: list[dict] = []
    start = date(2024, 1, 1)
    rotation = [
        "Dust in a Baggie",
        "Away From the Mire",
        "Midnight Rider",
        "Shady Grove",
        "Taking Water",
        "Enough to Leave",
    ]
    for index in range(24):
        show_id = f"show-{index}"
        shows.append(
            {
                "show_id": show_id,
                "show_date": (start + timedelta(days=index * 2)).isoformat(),
                "venue_name": "Ryman Auditorium" if index % 2 == 0 else "Red Rocks",
                "city": "Nashville" if index % 2 == 0 else "Morrison",
                "state": "TN" if index % 2 == 0 else "CO",
                "country": "USA",
            }
        )
        for position, offset in enumerate(range(4), start=1):
            setlists.append(
                {
                    "show_id": show_id,
                    "song_name": rotation[(index + offset) % len(rotation)],
                    "song_position": position,
                }
            )
    return pd.DataFrame(shows), pd.DataFrame(setlists)


def test_diagnose_writes_markdown_and_json(monkeypatch, tmp_path) -> None:
    shows_df, sets_df = _billy_frames()

    monkeypatch.setattr(
        diagnostics,
        "_load_frames",
        lambda band, snapshot_root: (shows_df, sets_df),
    )
    monkeypatch.setattr(
        diagnostics,
        "_build_predictor",
        lambda predictor_class, band: BillyFastPredictor(
            songs_df=_SONGS_DF,
            persist_artifacts=False,
        ),
    )

    markdown_path, json_path = diagnostics.diagnose(
        band="billy",
        predictor_path="jambandnerd.models.billy.fast_predictor.BillyFastPredictor",
        shows=3,
        snapshot_root=None,
        out_dir=tmp_path,
    )

    assert markdown_path.exists()
    assert json_path.exists()
    payload = json.loads(json_path.read_text())
    assert payload["band"] == "billy"
    assert payload["model_version"] == "billy_fast_gbm_v1"
    assert payload["training_rows"] > 0
    assert set(BILLY_FAST_FEATURE_COLS).issubset(payload["feature_columns"])
    assert set(BILLY_FAST_CANDIDATE_CONTEXT_COLS).issubset(payload["feature_columns"])
    assert "Per-feature summary" in markdown_path.read_text()
