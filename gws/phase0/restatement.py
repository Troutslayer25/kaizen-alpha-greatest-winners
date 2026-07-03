"""Fundamentals restatement check (review PIT 3.4).

`CHECK (available_date <= as_of_date)` guards the TIMING of a fundamental, not its VINTAGE: FMP
standard endpoints serve latest-RESTATED values, so a 2015 quarter can carry a 2018-restated
number the classifier trains on but no contemporaneous trader saw. This compares stored values
against SEC EDGAR as-filed (first-filed) values and reports the restatement incidence, so it is
a documented, measured limitation rather than a silent look-ahead. (EDGAR fetching lives in the
existing SEC-EDGAR integration; this module is the pure comparator + summary.)"""
from __future__ import annotations

import numpy as np


def restatement_incidence(stored, as_filed, *, rel_tol: float = 0.005):
    """Fraction of (stored vs first-filed) value pairs that differ by more than `rel_tol`
    (relative). Returns a summary dict; NaN pairs are ignored."""
    s = np.asarray(stored, float)
    f = np.asarray(as_filed, float)
    m = ~(np.isnan(s) | np.isnan(f))
    s, f = s[m], f[m]
    if s.size == 0:
        return {"n": 0, "n_restated": 0, "incidence": float("nan"), "max_rel_diff": float("nan")}
    denom = np.where(np.abs(f) > 0, np.abs(f), np.nan)
    rel = np.abs(s - f) / denom
    restated = np.nan_to_num(rel, nan=0.0) > rel_tol
    return {"n": int(s.size), "n_restated": int(restated.sum()),
            "incidence": float(restated.mean()),
            "max_rel_diff": float(np.nanmax(rel)) if np.isfinite(rel).any() else float("nan")}
