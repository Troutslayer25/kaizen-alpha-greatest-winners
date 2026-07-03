"""Compute aspect: the parallelized feature-matrix driver is numerically identical to serial."""
import numpy as np
import pandas as pd

from gws.phase_a2.feature_matrix import build_feature_matrix


def _panel(n_tickers=6, n_days=400, seed=0):
    rng = np.random.default_rng(seed)
    series = {}
    for tk in range(n_tickers):
        close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n_days))
        series[tk] = {"close": close, "high": close * 1.01, "low": close * 0.99,
                      "volume": rng.integers(1e6, 5e6, n_days).astype(float)}
    pts = []
    for tk in range(n_tickers):
        for i in range(260, n_days, 5):
            pts.append({"ticker_id": tk, "as_of_index": i})
    return pd.DataFrame(pts), series


def test_serial_and_parallel_agree_exactly():
    points, series = _panel()
    serial = build_feature_matrix(points, series, n_jobs=1)
    parallel = build_feature_matrix(points, series, n_jobs=2)
    pd.testing.assert_frame_equal(serial, parallel)


def test_rows_align_one_to_one_with_points():
    points, series = _panel()
    fm = build_feature_matrix(points, series, n_jobs=1)
    assert list(fm.index) == list(points.index)
    assert len(fm) == len(points)


def test_float32_default_halves_dtype():
    points, series = _panel()
    fm = build_feature_matrix(points, series)
    assert fm.to_numpy().dtype == np.float32
    fm64 = build_feature_matrix(points, series, dtype=np.float64)
    # values agree to float32 precision
    assert np.allclose(fm.to_numpy(), fm64.to_numpy(), rtol=1e-5, atol=1e-6, equal_nan=True)
