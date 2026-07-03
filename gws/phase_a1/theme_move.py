"""Theme's OWN move + rs-vs-theme (review, thematic comparison).

`MoveQuery.tickers_in(members)` slices moves by a theme's members, but "compare a move to a
THEMATIC move" needs the theme's own price action to compare against. This builds an equal- or
weight-ed composite index from member series, so the theme's own moves can be detected/characterized
with the same machinery, and a member move can be compared to its theme (rs-vs-theme, PIT).

Pure and testable; wiring theme membership (curated_lists / sector tables) is the caller's job."""
from __future__ import annotations

import numpy as np


def theme_composite(member_closes, weights=None) -> np.ndarray:
    """Composite index from aligned member close series (list of equal-length arrays). Each member
    is rebased to 100 at the start, then weight-averaged (equal weight by default) into one index —
    the theme's own 'price'. NaNs in a member are ignored per-date (renormalized)."""
    m = np.asarray([np.asarray(c, float) for c in member_closes], float)
    base = m[:, :1]
    rebased = np.where(base > 0, m / base * 100.0, np.nan)
    w = np.ones(len(m)) if weights is None else np.asarray(weights, float)
    w = w[:, None]
    num = np.nansum(rebased * w, axis=0)
    den = np.nansum(np.where(np.isfinite(rebased), w, 0.0), axis=0)
    return np.where(den > 0, num / den, np.nan)


def rs_vs_theme(member_close, theme_close, i, lb: int = 63) -> float:
    """Member's return vs the theme composite's return over `lb` trading days, as of i (PIT)."""
    member_close = np.asarray(member_close, float)
    theme_close = np.asarray(theme_close, float)
    if i - lb < 0 or member_close[i - lb] <= 0 or theme_close[i] <= 0 or theme_close[i - lb] <= 0:
        return np.nan
    return float((member_close[i] / member_close[i - lb]) / (theme_close[i] / theme_close[i - lb]) - 1.0)


def theme_moves(member_closes, weights=None, *, scales=(2.0, 6.0, 15.0), atr_period: int = 21):
    """Detect the THEME's own multi-scale moves on its composite index (reuses the canonical
    detector). Returns (composite, {trail_atr: [MoveMFE]}); high/low approximated from the index."""
    from gws.phase_a1.move_detector_mfe import detect_moves_multiscale
    comp = theme_composite(member_closes, weights)
    return comp, detect_moves_multiscale(comp * 1.005, comp * 0.995, comp, scales=scales,
                                         atr_period=atr_period)
