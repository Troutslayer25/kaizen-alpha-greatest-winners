"""Move-detection driver that CONSUMES data-quality exclusions (lineage end-to-end).

Closes the gap where exclusions and the actually-traded-bars rule were only TAGGED, never
enforced at the detector. Before detecting, this builds the tradeable mask (volume > 0 AND not
inside any gws.data_quality_exceptions span) and forward-fills the untradeable bars so they carry
a zero return — the detector then cannot seed a phantom trough/move on corrupted or non-traded
data (Risk #4 enforcement). Detection itself is unchanged (multi-scale MFE).

`detect_moves_clean` is the pure core (tested without a DB); `detect_moves_for_ticker` loads the
series + spans from the DB (lazy ka_lib import) and cleans before detecting."""
from __future__ import annotations

import numpy as np

from gws.phase0.exclusions import forward_fill_excluded, tradeable_mask
from gws.phase_a1.move_detector_mfe import detect_moves_multiscale


def detect_moves_clean(high, low, close, volume, dates, exception_spans=(), *,
                       scales=(2.0, 6.0, 15.0), atr_period: int = 21, min_duration: int = 1):
    """Clean the series, then run the multi-scale detector. Returns
    (dates_c, close_c, high_c, low_c, volume_c, {trail_atr: [MoveMFE]}) — the CLEANED arrays are
    returned so characterization runs on the same bars the detector saw (review M-4).

    Cleaning (reviews C-2/C-3): a bar is untradeable if volume<=0, it falls in an exception span,
    OR any of its OHLC is non-finite (a NaN high would otherwise poison the recursive Wilder ATR
    forever and the trailing stop would never fire). Untradeable bars are forward-filled to the
    last good value; LEADING untradeable bars (phantom-zero series starts — no prior good value)
    are TRIMMED, because forward-fill cannot repair them and a close of ~0 seeds an infinite move."""
    high = np.asarray(high, float); low = np.asarray(low, float)
    close = np.asarray(close, float); volume = np.asarray(volume, float)
    finite = np.isfinite(close) & np.isfinite(high) & np.isfinite(low)
    mask = tradeable_mask(dates, volume, exception_spans) & finite

    c = forward_fill_excluded(close, mask)
    h = forward_fill_excluded(high, mask)
    lo = forward_fill_excluded(low, mask)

    if not mask.any():                                   # nothing tradeable — no moves
        # key by the SAME float scale as detect_moves_multiscale (review m1): the empty path
        # must not return string keys the callers (which do by_scale[6.0]) can't find.
        return list(dates), c, h, lo, volume, {k: [] for k in scales}
    start = int(np.argmax(mask))                         # first tradeable+finite bar
    d = list(dates)[start:]
    c, h, lo, vol = c[start:], h[start:], lo[start:], volume[start:]
    # explicit raise (not assert — survives python -O; review m3): a ~0 close would seed an
    # infinite-magnitude move. The orchestrator must catch this per-ticker, not die the whole run.
    if not (np.isfinite(c).all() and (c > 0).all()):
        raise ValueError("cleaned close must be finite and > 0 for detection (unmasked phantom-zero?)")
    by_scale = detect_moves_multiscale(h, lo, c, scales=scales, atr_period=atr_period,
                                       min_duration=min_duration)
    return d, c, h, lo, vol, by_scale


def detect_moves_for_ticker(conn, ticker_id, *, source: str = "fmp",
                            scales=(2.0, 6.0, 15.0), atr_period: int = 21) -> tuple:
    """Load a ticker's adjusted series + its (same-domain) exclusion spans and detect on the
    cleaned series. Returns (dates_c, close_c, high_c, low_c, volume_c, {trail_atr: [MoveMFE]}) —
    the cleaned arrays feed persistence so descriptors match what the detector saw. `source`
    selects both the price table AND the exclusion ID domain (review C-1)."""
    from gws.phase0.exclusions import excluded_ids, load_exception_spans  # lazy
    if source == "fmp":
        table, key, span_sources = "public.eod_prices", "ticker_id", ["fmp", "completeness_audit"]
    else:
        table, key, span_sources = ("ka_history.eod_history", "entity_id",
                                    ["norgate", "backfill_norgate_adjusted", "assert_adjustment_fresh"])
    # whole-entity exclusion (stale-adjustment / unfetchable): emit zero moves (review C2)
    if ticker_id in excluded_ids(conn, sources=span_sources):
        return [], np.array([]), np.array([]), np.array([]), np.array([]), {k: [] for k in scales}
    rows = conn.execute(
        f"SELECT date, high, low, adjusted_close AS close, volume FROM {table} "
        f"WHERE {key}=%s AND adjusted_close IS NOT NULL ORDER BY date", (ticker_id,)).fetchall()
    dates = [r["date"] for r in rows]
    spans = load_exception_spans(conn, ticker_id, sources=span_sources)
    high = np.array([r["high"] for r in rows], float)
    low = np.array([r["low"] for r in rows], float)
    close = np.array([r["close"] for r in rows], float)
    volume = np.array([r["volume"] for r in rows], float)
    return detect_moves_clean(high, low, close, volume, dates, spans,
                              scales=scales, atr_period=atr_period)
