from __future__ import annotations

import datetime as dt

import numpy as np

from jambandnerd.models.shared.matrix_features import (
    gap_percentile_array,
    run_position,
    tour_position,
)


def test_run_position_counts_consecutive_prior_shows() -> None:
    dates = [
        dt.date(2026, 7, 7),
        dt.date(2026, 7, 8),
        dt.date(2026, 7, 10),
    ]

    assert run_position(dates, dt.date(2026, 7, 9), gap_days=1) == 3
    assert run_position(dates, dt.date(2026, 7, 11), gap_days=1) == 2


def test_tour_position_resets_after_gap() -> None:
    dates = [
        dt.date(2026, 6, 1),
        dt.date(2026, 6, 3),
        dt.date(2026, 7, 1),
        dt.date(2026, 7, 2),
    ]

    assert tour_position(dates, dt.date(2026, 7, 3), tour_gap_days=14) == 3


def test_gap_percentile_array_handles_missing_and_observed_distributions() -> None:
    result = gap_percentile_array(
        eligible_songs=["A", "B"],
        gap_e=np.array([3.0, 10.0]),
        gap_distributions={"A": np.array([1.0, 3.0, 5.0])},
    )

    np.testing.assert_allclose(result, np.array([2.0 / 3.0, 0.0]))
