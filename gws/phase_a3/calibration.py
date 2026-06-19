"""Probability calibration (Part X).

The production output is a probability used as a ranking engine, so a
well-discriminating but miscalibrated model misranks. Calibration is assessed
(Brier + reliability curve) and, where needed, a transform (isotonic or Platt) is
fit on a HELD-OUT calibration split — never the test set.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


def fit_calibrator(probs, y, method: str = "isotonic"):
    """Fit a calibration transform on (probs, y). Returns a callable p -> calibrated p.
    Fit this on a held-out calibration split only."""
    probs = np.asarray(probs, float)
    y = np.asarray(y, int)
    if method == "isotonic":
        ir = IsotonicRegression(out_of_bounds="clip").fit(probs, y)
        return lambda p: ir.predict(np.asarray(p, float))
    lr = LogisticRegression().fit(probs.reshape(-1, 1), y)        # Platt scaling
    return lambda p: lr.predict_proba(np.asarray(p, float).reshape(-1, 1))[:, 1]


def reliability_table(probs, y, n_bins: int = 10) -> list[dict]:
    """Per-bin mean predicted probability vs observed frequency (reliability curve)."""
    probs = np.asarray(probs, float)
    y = np.asarray(y, int)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(probs, edges) - 1, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = idx == b
        if m.any():
            rows.append({"bin": b, "mean_pred": float(probs[m].mean()),
                         "frac_pos": float(y[m].mean()), "n": int(m.sum())})
    return rows


def brier(probs, y) -> float:
    return float(brier_score_loss(np.asarray(y, int), np.asarray(probs, float)))
