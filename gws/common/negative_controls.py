"""Negative-control harness — the mirror of the synthetic oracle.

The oracle asks "does the pipeline find the signal we PLANTED?" Negative controls ask the
complementary question: "does the pipeline correctly find NOTHING in deliberately useless
data?" If a model scores above chance on shuffled/permuted/misaligned inputs, something is
leaking or overfitting — caught before the expensive real run.

Corruption primitives (each destroys real signal while preserving marginal structure, so a
correctly-built pipeline must drop to chance):
  - shuffle_labels: permute y globally (breaks any feature->label relationship)
  - permute_features_within_date: permute feature rows within each date (kills cross-sectional
    signal but keeps each day's feature distribution intact — the strongest leakage probe)
  - shift_labels_by: misalign labels by a fixed offset (temporal misalignment)
  - gaussian_noise_feature: a pure-noise column that must never become important

All are deterministic under `seed`.
"""
from __future__ import annotations

import numpy as np


def shuffle_labels(y, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.permutation(np.asarray(y))


def permute_features_within_date(X, dates, seed: int = 0) -> np.ndarray:
    """Permute feature ROWS within each date group. Preserves each day's cross-sectional
    feature distribution but destroys the row-to-label correspondence."""
    X = np.asarray(X, float)
    dates = np.asarray(dates)
    rng = np.random.default_rng(seed)
    out = X.copy()
    for d in np.unique(dates):
        idx = np.where(dates == d)[0]
        out[idx] = X[rng.permutation(idx)]
    return out


def shift_labels_by(y, offset: int) -> np.ndarray:
    """Roll labels by `offset` positions (temporal misalignment red-team)."""
    return np.roll(np.asarray(y), offset)


def gaussian_noise_feature(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0, 1, n)


def negative_control_report(X, y, t, fit_score_fn, *, seed: int = 0) -> dict:
    """Run `fit_score_fn(X, y, t) -> score` (e.g. an OOS AUC) on the real data and under each
    corruption. Returns the real score plus each negative-control score. A correct pipeline
    yields real >> ~chance and every control ~chance.

    `fit_score_fn` must be a callable taking (X, y, t) and returning a scalar discrimination
    metric (0.5 = chance for AUC). It is supplied by the caller (e.g. a thin wrapper around
    run_walk_forward) so this module stays dependency-light.
    """
    X = np.asarray(X, float)
    y = np.asarray(y)
    return {
        "real": float(fit_score_fn(X, y, t)),
        "shuffled_labels": float(fit_score_fn(X, shuffle_labels(y, seed), t)),
        "permuted_features": float(fit_score_fn(permute_features_within_date(X, t, seed), y, t)),
        "shifted_labels": float(fit_score_fn(X, shift_labels_by(y, max(1, len(y) // 7)), t)),
    }


def passes_negative_controls(report: dict, *, chance: float = 0.5, margin: float = 0.05) -> bool:
    """True iff the real score beats chance and every control is within `margin` of chance.
    A control meaningfully above chance => leakage/overfitting => investigate."""
    controls = [v for k, v in report.items() if k != "real"]
    real_ok = report["real"] > chance + margin
    controls_ok = all(abs(c - chance) <= margin for c in controls)
    return bool(real_ok and controls_ok)
