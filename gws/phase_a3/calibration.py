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
from sklearn.metrics import brier_score_loss, roc_auc_score


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


def calibration_decay(raw_probs, calibrated_probs, y, *, auc_floor: float = 0.55) -> dict:
    """Calibration-masking monitor (critique keeper).

    A static calibration transform can cosmetically reshape probabilities into a pleasing
    ranked/calibrated curve while the underlying DISCRIMINATION degrades (e.g. when the
    regime shifts). The two are separable: a calibration transform is monotone, so it
    CANNOT change ranking — discrimination is captured entirely by AUC. Therefore a model
    whose AUC has fallen to chance is producing no edge no matter how good its calibrated
    Brier looks; the transform is doing the heavy lifting. The alarm fires on weak
    discrimination (auc < auc_floor); `brier_share` is reported as supporting context —
    the fraction of raw Brier the transform removes (high share + low AUC = pure cosmetics).

    Intended to run per walk-forward fold (and per regime bucket) so a falling AUC is
    caught even while calibrated Brier stays flat.

    Returns {auc, brier_raw, brier_calibrated, brier_share, alarm}.
    """
    raw = np.asarray(raw_probs, float)
    cal = np.asarray(calibrated_probs, float)
    y = np.asarray(y, int)
    auc = float(roc_auc_score(y, raw)) if len(np.unique(y)) > 1 else float("nan")
    b_raw = brier(raw, y)
    b_cal = brier(cal, y)
    brier_share = float((b_raw - b_cal) / b_raw) if b_raw > 1e-12 else float("nan")
    alarm = bool(auc == auc and auc < auc_floor)   # NaN-safe: no alarm if AUC undefined
    return {"auc": auc, "brier_raw": b_raw, "brier_calibrated": b_cal,
            "brier_share": brier_share, "alarm": alarm}
