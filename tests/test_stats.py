import numpy as np

from gws.common.stats import benjamini_hochberg, cohens_d, block_bootstrap_by_ticker


def test_benjamini_hochberg_known():
    p = np.array([0.001, 0.008, 0.039, 0.041, 0.9])
    rejected, q = benjamini_hochberg(p, alpha=0.05)
    # crit = [.01,.02,.03,.04,.05]; largest i with p_i<=crit_i is i=2 -> reject two smallest
    assert rejected.tolist() == [True, True, False, False, False]
    assert q.min() >= 0.0 and q.max() <= 1.0


def test_benjamini_hochberg_none_pass():
    p = np.array([0.2, 0.5, 0.9])
    rejected, _ = benjamini_hochberg(p, alpha=0.05)
    assert not rejected.any()


def test_cohens_d_sign_and_symmetry():
    a = np.array([5.0, 6, 7, 6, 5])
    b = np.array([1.0, 2, 3, 2, 1])
    assert cohens_d(a, b) > 0
    assert np.isclose(cohens_d(a, b), -cohens_d(b, a))


def test_block_bootstrap_ci_contains_mean():
    rng = np.random.default_rng(0)
    tickers = np.repeat(np.arange(20), 30)
    values = rng.normal(1.0, 0.5, size=tickers.size)
    point, (lo, hi) = block_bootstrap_by_ticker(values, tickers, n_boot=300, seed=0)
    assert lo <= point <= hi
    assert lo < 1.0 < hi
