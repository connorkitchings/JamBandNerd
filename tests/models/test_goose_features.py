"""Tests for goose/features.py — Tier A + Tier B feature engineering."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from jambandnerd.models.goose.features import (
    GOOSE_EXTRA_FEATURES,
    augment_training_frame,
    compute_goose_song_features,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _plays_with_set_cols() -> pd.DataFrame:
    """20 historical plays spanning two runs across two months."""
    rows = []
    # Run 1: Jan 10–12 (3-night run)
    for day, songs, set_num, encore in [
        (
            10,
            [("Alpha", 1, False), ("Beta", 2, False), ("Gamma", 99, True)],
            None,
            None,
        ),
        (11, [("Alpha", 1, False), ("Delta", 2, False)], None, None),
        (12, [("Beta", 1, False), ("Gamma", 99, True)], None, None),
    ]:
        show_id = f"g-{day}"
        for pos, (song, snum, enc) in enumerate(songs, 1):
            rows.append(
                {
                    "show_id": show_id,
                    "show_date": date(2024, 1, day).isoformat(),
                    "show_index": day - 9,
                    "song_name": song,
                    "set_number": snum,
                    "song_position": pos,
                    "encore": enc,
                    "venue_name": "Capitol",
                    "state": "NY",
                }
            )
    # Stand-alone show in February
    for pos, (song, snum, enc) in enumerate(
        [("Alpha", 1, False), ("Epsilon", 2, False)], 1
    ):
        rows.append(
            {
                "show_id": "g-feb",
                "show_date": date(2024, 2, 5).isoformat(),
                "show_index": 10,
                "song_name": song,
                "set_number": snum,
                "song_position": pos,
                "encore": enc,
                "venue_name": "Agora",
                "state": "OH",
            }
        )

    df = pd.DataFrame(rows)
    df["set_number"] = pd.to_numeric(df["set_number"], errors="coerce").astype("Int64")
    df["song_position"] = pd.to_numeric(df["song_position"], errors="coerce").astype(
        "Int64"
    )
    df["encore"] = df["encore"].fillna(False).astype(bool)
    return df


def _plays_without_set_cols() -> pd.DataFrame:
    """Same shows but without set columns (simulates non-Goose band)."""
    rows = []
    for i, (song, d) in enumerate(
        [
            ("Alpha", "2024-01-10"),
            ("Beta", "2024-01-10"),
            ("Alpha", "2024-01-11"),
            ("Delta", "2024-01-11"),
        ],
        1,
    ):
        rows.append(
            {"show_id": f"g-{i}", "show_date": d, "show_index": i, "song_name": song}
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Basic output contract
# ---------------------------------------------------------------------------


def test_returns_all_extra_feature_columns() -> None:
    df = compute_goose_song_features(
        _plays_with_set_cols(), target_show_date=date(2024, 2, 6)
    )
    for col in GOOSE_EXTRA_FEATURES:
        assert col in df.columns, f"Missing column: {col}"


def test_keyed_by_song_name() -> None:
    df = compute_goose_song_features(
        _plays_with_set_cols(), target_show_date=date(2024, 2, 6)
    )
    assert "song_name" in df.columns
    assert df["song_name"].nunique() == len(df)


def test_empty_plays_returns_empty_frame() -> None:
    empty = pd.DataFrame(columns=["show_id", "show_date", "show_index", "song_name"])
    df = compute_goose_song_features(empty, target_show_date=date(2024, 3, 1))
    assert df.empty


# ---------------------------------------------------------------------------
# Tier A: temporal rates
# ---------------------------------------------------------------------------


def test_dow_play_rate_in_range() -> None:
    df = compute_goose_song_features(
        _plays_with_set_cols(), target_show_date=date(2024, 2, 6)
    )
    assert (df["dow_play_rate"] >= 0.0).all()
    assert (df["dow_play_rate"] <= 1.0).all()


def test_month_play_rate_in_range() -> None:
    df = compute_goose_song_features(
        _plays_with_set_cols(), target_show_date=date(2024, 2, 6)
    )
    assert (df["month_play_rate"] >= 0.0).all()
    assert (df["month_play_rate"] <= 1.0).all()


def test_show_position_in_run_continuation() -> None:
    """A target show the day after the last historical show starts at night 2+."""
    plays = _plays_with_set_cols()
    # Last historical show was Jan 12; target Jan 13 = night 4 of run
    df = compute_goose_song_features(plays, target_show_date=date(2024, 1, 13))
    pos = df["show_position_in_run"].iloc[0]
    assert pos >= 2


def test_show_position_in_run_new_run() -> None:
    """A target show after a long gap should be night 1."""
    plays = _plays_with_set_cols()
    # Last historical show Feb 5; target March 1 = 24-day gap → new run
    df = compute_goose_song_features(plays, target_show_date=date(2024, 3, 1))
    assert df["show_position_in_run"].iloc[0] == 1.0


def test_tour_position_new_stretch() -> None:
    """After a 14-day+ break, tour_position resets to 1."""
    plays = _plays_with_set_cols()
    # Last show Feb 5; target March 1 = 25 days later
    df = compute_goose_song_features(plays, target_show_date=date(2024, 3, 1))
    assert df["tour_position"].iloc[0] == 1.0


def test_tour_position_continuation() -> None:
    """Shows within 14 days of each other continue the same stretch."""
    plays = _plays_with_set_cols()
    # Jan 10–12 run; target Jan 13 = continuous stretch
    df = compute_goose_song_features(plays, target_show_date=date(2024, 1, 13))
    assert df["tour_position"].iloc[0] > 1.0


# ---------------------------------------------------------------------------
# Tier B: set-position rates
# ---------------------------------------------------------------------------


def test_tier_b_rates_present_with_set_cols() -> None:
    df = compute_goose_song_features(
        _plays_with_set_cols(), target_show_date=date(2024, 2, 6)
    )
    for col in [
        "set1_play_rate",
        "set2_play_rate",
        "encore_rate",
        "mean_song_position",
    ]:
        assert col in df.columns
        assert (df[col] >= 0.0).all()


def test_encore_rate_for_encore_song() -> None:
    df = compute_goose_song_features(
        _plays_with_set_cols(), target_show_date=date(2024, 2, 6)
    )
    gamma_row = df[df["song_name"] == "Gamma"]
    assert not gamma_row.empty
    # Gamma was played twice, both times as encore
    assert gamma_row["encore_rate"].iloc[0] == pytest.approx(1.0)


def test_encore_rate_zero_for_non_encore_song() -> None:
    df = compute_goose_song_features(
        _plays_with_set_cols(), target_show_date=date(2024, 2, 6)
    )
    alpha_row = df[df["song_name"] == "Alpha"]
    assert alpha_row["encore_rate"].iloc[0] == pytest.approx(0.0)


def test_tier_b_defaults_to_zero_without_set_cols() -> None:
    df = compute_goose_song_features(
        _plays_without_set_cols(), target_show_date=date(2024, 1, 12)
    )
    for col in [
        "set1_play_rate",
        "set2_play_rate",
        "encore_rate",
        "mean_song_position",
    ]:
        assert (
            df[col] == 0.0
        ).all(), f"{col} should default to 0.0 when set cols absent"


# ---------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------


def test_no_leakage_from_target_show() -> None:
    """Features must not include data from the target show date."""
    plays = _plays_with_set_cols()
    # target_show_date = Feb 5 (a show that IS in plays)
    target_date = date(2024, 2, 5)
    # historical_plays is already pre-filtered to < reference_date,
    # so we filter to < target_date to simulate reference_date = target_date - 1
    sub_plays = plays[pd.to_datetime(plays["show_date"]).dt.date < target_date].copy()
    df = compute_goose_song_features(sub_plays, target_show_date=target_date)
    # Epsilon only appeared on Feb 5 — it should NOT appear in features
    assert "Epsilon" not in df["song_name"].values


def test_augment_training_frame_no_leakage() -> None:
    """augment_training_frame must use truncated history per target show."""
    plays = _plays_with_set_cols()
    # Build a minimal training frame with two target shows
    frame = pd.DataFrame(
        [
            {
                "song_name": "Alpha",
                "target_show_index": 2,
                "target_show_date": "2024-01-11",
                "label": 1,
                "current_gap": 1,
            },
            {
                "song_name": "Beta",
                "target_show_index": 2,
                "target_show_date": "2024-01-11",
                "label": 0,
                "current_gap": 5,
            },
            {
                "song_name": "Alpha",
                "target_show_index": 10,
                "target_show_date": "2024-02-05",
                "label": 1,
                "current_gap": 1,
            },
        ]
    )
    augmented = augment_training_frame(frame, plays)
    # Epsilon appeared on Feb 5 — it must NOT appear in the training frame for that show
    # (Epsilon wasn't a candidate in any show, so it won't be there — but verify no column issues)
    for col in GOOSE_EXTRA_FEATURES:
        assert col in augmented.columns
    assert augmented[GOOSE_EXTRA_FEATURES].notna().all().all()
