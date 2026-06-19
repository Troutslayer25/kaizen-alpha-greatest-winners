"""Monte-Carlo robustness (Phase B2).

Generates equity-curve paths by resampling the EMPIRICAL period-return distribution
(no normality assumption), supporting i.i.d. or block bootstrap (block preserves
autocorrelation). Reports expected CAGR/terminal with confidence intervals, expected
and tail max-drawdown — the distribution of outcomes across resampled histories rather
than a single point estimate.
"""
from __future__ import annotations

import numpy as np


def bootstrap_equity_paths(returns, *, n_paths: int = 10_000, horizon: int | None = None,
                           block: int = 1, seed: int = 0) -> np.ndarray:
    """Return an (n_paths, horizon) array of equity curves (starting capital = 1.0).

    returns: empirical per-period simple returns. block>1 uses a moving-block bootstrap
    of length `block` to preserve short-run autocorrelation."""
    returns = np.asarray(returns, float)
    n = len(returns)
    horizon = horizon or n
    rng = np.random.default_rng(seed)

    if block <= 1:
        idx = rng.integers(0, n, size=(n_paths, horizon))
    else:
        n_blocks = int(np.ceil(horizon / block))
        starts = rng.integers(0, n - block + 1, size=(n_paths, n_blocks))
        offsets = np.arange(block)
        idx = (starts[:, :, None] + offsets[None, None, :]).reshape(n_paths, n_blocks * block)[:, :horizon]

    sampled = returns[idx]
    return np.cumprod(1.0 + sampled, axis=1)


def summarize_paths(equity: np.ndarray, *, periods_per_year: int = 252, ci: float = 0.90) -> dict:
    """Distributional summary of bootstrapped equity curves."""
    lo_q, hi_q = (1 - ci) / 2, 1 - (1 - ci) / 2
    terminal = equity[:, -1]
    horizon = equity.shape[1]
    cagr = terminal ** (periods_per_year / horizon) - 1.0
    running_max = np.maximum.accumulate(equity, axis=1)
    max_dd = ((running_max - equity) / running_max).max(axis=1)
    return {
        "terminal_median": float(np.median(terminal)),
        "terminal_ci": (float(np.quantile(terminal, lo_q)), float(np.quantile(terminal, hi_q))),
        "cagr_median": float(np.median(cagr)),
        "cagr_ci": (float(np.quantile(cagr, lo_q)), float(np.quantile(cagr, hi_q))),
        "expected_max_drawdown": float(np.mean(max_dd)),
        "max_drawdown_95": float(np.quantile(max_dd, 0.95)),
        "n_paths": int(equity.shape[0]),
    }
