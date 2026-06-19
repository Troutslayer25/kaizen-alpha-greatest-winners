import numpy as np

from gws.common.stats import benjamini_hochberg, cohens_d, block_bootstrap_by_ticker


def test_benjamini_hochberg_known():
    p = np.array([0.001, 0.008, 0.039, 0.041, 0.9])
    rejected, q = benjamini_hochberg(p, alpha=0.05)
    # BH q-values: reject the two smallest only (q3 = .039*5/3 = .065 > .05)
    assert rejected.tolist() == [True, True, False, False, False]
    assert np.all(q[:2] <= 0.05)
    assert q[2] > 0.05
    assert np.isclose(q[0], 0.005)              # 0.001 * 5 / 1


def test_benjamini_hochberg_none_pass():
    rejected, _ = benjamini_hochberg(np.array([0.2, 0.5, 0.9]), alpha=0.05)
    assert not rejected.any()


def test_benjamini_hochberg_handles_nan():
    # NaN p-values are excluded, not counted in n (so they cannot deflate the others).
    rejected, q = benjamini_hochberg(np.array([0.001, np.nan, 0.9]))
    assert rejected[0] and not rejected[2]
    assert np.isnan(q[1])
    assert np.isclose(q[0], 0.002)              # excluded NaN -> n=2: 0.001 * 2 / 1


def test_cohens_d_sign_and_symmetry():
    a = np.array([5.0, 6, 7, 6, 5])
    b = np.array([1.0, 2, 3, 2, 1])
    assert cohens_d(a, b) > 0
    assert np.isclose(cohens_d(a, b), -cohens_d(b, a))


def test_cohens_d_unestimable_is_nan():
    assert np.isnan(cohens_d([1.0], [2.0, 3.0]))     # n<2 in one arm
    assert np.isnan(cohens_d([5.0, 5, 5], [5.0, 5, 5]))  # zero pooled SD


def test_block_bootstrap_ci_contains_mean():
    rng = np.random.default_rng(0)
    tickers = np.repeat(np.arange(20), 30)
    values = rng.normal(1.0, 0.5, size=tickers.size)
    point, (lo, hi) = block_bootstrap_by_ticker(values, tickers, n_boot=300, seed=0)
    assert lo <= point <= hi
    assert lo < 1.0 < hi


def test_block_bootstrap_drops_nan():
    tickers = np.repeat(np.arange(5), 4)
    values = np.ones(tickers.size, float)
    values[0] = np.nan
    point, (lo, hi) = block_bootstrap_by_ticker(values, tickers, n_boot=100, seed=0)
    assert point == 1.0 and not np.isnan(lo) and not np.isnan(hi)
