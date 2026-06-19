"""Purged, embargoed, expanding-window walk-forward splitter (blueprint T6/OQ-7).

The binding validation scheme for the production classifier:
  - TRAINING windows expand and therefore overlap across folds (correct, by design).
  - TEST periods are non-overlapping and strictly sequential.
  - PURGE: training observations whose forward-label window (length K) reaches into
    the test period are removed (López de Prado purged CV).
  - EMBARGO: a buffer after each test period is excluded from training (matters only
    when training could include post-test observations; included for generality).

Ticker non-independence is handled in inference (ticker-clustered SEs / block
bootstrap), NOT by forcing every ticker into one fold — that is incompatible with an
expanding temporal split. A ticker-disjoint GroupKFold is provided only as a separate
robustness leakage probe.

Observations are addressed by an integer trading-day ordinal `t` (the production
pipeline maps calendar dates -> ordinals via the trading calendar). This keeps the
splitter calendar-agnostic and unambiguous.
"""
from __future__ import annotations

from typing import Iterator

import numpy as np


def expanding_splits(
    t,
    test_boundaries,
    label_horizon: int,
    embargo: int = 0,
    drop_incomplete_labels: bool = True,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Yield (train_idx, test_idx) for each expanding fold.

    Parameters
    ----------
    t : array of int trading-day ordinals, one per observation.
    test_boundaries : sorted ordinals; fold k tests [boundaries[k], boundaries[k+1]).
        The final fold tests [boundaries[-1], max(t)+1).
    label_horizon : K, the forward-label window length in trading days (purge size).
    embargo : trading days excluded from training after each test period.
    drop_incomplete_labels : if True (default), test observations whose forward-label
        window extends past the last available day (t + label_horizon > max(t)) are
        dropped. Without this the most recent K days score forming setups as negatives,
        deflating recent-period metrics. Empty input yields no folds.
    """
    t = np.asarray(t)
    if t.size == 0:
        return
    bounds = list(test_boundaries)
    tmax = int(t.max())
    last = tmax + 1
    for k, ts in enumerate(bounds):
        te = bounds[k + 1] if k + 1 < len(bounds) else last
        test_mask = (t >= ts) & (t < te)
        if drop_incomplete_labels:
            test_mask &= (t + label_horizon) <= tmax
        test_idx = np.where(test_mask)[0]
        if len(test_idx) == 0:
            continue
        train_mask = t < ts
        # purge: keep a training obs only if its label window finishes before test start
        train_mask &= (t + label_horizon) < ts
        if embargo > 0:
            train_mask &= ~((t >= te) & (t < te + embargo))
        train_idx = np.where(train_mask)[0]
        yield train_idx, test_idx


def ticker_disjoint_folds(tickers, n_splits: int = 5) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Deterministic ticker-disjoint folds — robustness probe only (not the primary scheme).

    Every observation of a given ticker falls entirely in one fold's test set.
    """
    tickers = np.asarray(tickers)
    _, inv = np.unique(tickers, return_inverse=True)
    assignment = inv % n_splits
    for f in range(n_splits):
        test_idx = np.where(assignment == f)[0]
        train_idx = np.where(assignment != f)[0]
        if len(test_idx) == 0:
            continue
        yield train_idx, test_idx
