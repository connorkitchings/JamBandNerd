"""Tests for the Platt scaling calibrator."""

from __future__ import annotations

import numpy as np

from jambandnerd.models.calibration import PlattScaler


def test_platt_scaler_maps_monotonic_to_probabilities() -> None:
    raw = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    labels = np.array([0, 0, 0, 1, 1])
    scaler = PlattScaler().fit(raw, labels)
    calibrated = scaler.transform(raw)

    assert calibrated.shape == raw.shape
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)

    diffs = np.diff(calibrated)
    assert np.all(diffs >= 0), "calibrated values should be monotonically increasing"


def test_platt_scaler_fit_transform_matches_fit_then_transform() -> None:
    raw = np.array([0.5, 1.5, 2.5, 3.5])
    labels = np.array([0, 0, 1, 1])
    s1 = PlattScaler().fit(raw, labels)
    result1 = s1.transform(raw)
    result2 = PlattScaler().fit_transform(raw, labels)
    np.testing.assert_allclose(result1, result2)


def test_platt_scaler_empty_input() -> None:
    scaler = PlattScaler().fit(np.array([]), np.array([]))
    result = scaler.transform(np.array([]))
    assert len(result) == 0


def test_platt_scaler_all_positive_labels() -> None:
    raw = np.array([1.0, 2.0, 3.0])
    labels = np.array([1.0, 1.0, 1.0])
    calibrated = PlattScaler().fit_transform(raw, labels)
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)


def test_platt_scaler_all_negative_labels() -> None:
    raw = np.array([1.0, 2.0, 3.0])
    labels = np.array([0.0, 0.0, 0.0])
    calibrated = PlattScaler().fit_transform(raw, labels)
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)


def test_platt_scaler_single_sample() -> None:
    raw = np.array([1.0])
    labels = np.array([1.0])
    calibrated = PlattScaler().fit_transform(raw, labels)
    assert len(calibrated) == 1
    assert 0.0 <= calibrated[0] <= 1.0
