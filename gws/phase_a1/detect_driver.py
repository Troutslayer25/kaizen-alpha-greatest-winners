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
                       scales=(2.0, 6.0, 15.0), atr_period: int = 21, min_duration: int = 1,
                       data_valid=None):
    """Clean the series, then run the multi-scale detector. Returns
    (dates_c, close_c, high_c, low_c, volume_c, {trail_atr: [MoveMFE]}) — the CLEANED arrays are
    returned so characterization runs on the same bars the detector saw (review M-4).

    Cleaning (reviews C-2/C-3): a bar is untradeable if volume<=0, it falls in an exception span,
    OR any of its OHLC is non-finite (a NaN high would otherwise poison the recursive Wilder ATR
    forever and the trailing stop would never fire). Untradeable bars are forward-filled to the
    last good value; LEADING untradeable bars (phantom-zero series starts — no prior good value)
    are TRIMMED, because forward-fill cannot repair them and a close of ~0 seeds an infinite move.

    `data_valid` (Gate 0.5 Decision D, 2026-07-24): optional per-bar validity mask from the
    caller — the driver passes the ratified $1 RAW-close data-validity floor (Phase-0 semantics,
    penny-spread artifact guard). The pilot audit caught 46 phantom mega-moves (999x/9999x round
    ratios, mae=0) seeded on sub-penny prints; detection never consumed the floor that eligibility
    already enforced. Invalid bars are treated exactly like untradeable ones."""
    high = np.asarray(high, float); low = np.asarray(low, float)
    close = np.asarray(close, float); volume = np.asarray(volume, float)
    finite = np.isfinite(close) & np.isfinite(high) & np.isfinite(low)
    mask = tradeable_mask(dates, volume, exception_spans) & finite
    if data_valid is not None:
        mask &= np.asarray(data_valid, bool)

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
                            scales=(2.0, 6.0, 15.0), atr_period: int = 21,
                            max_date=None, unlock: bool = False) -> tuple:
    """Load a ticker's adjusted series + its (same-domain) exclusion spans and detect on the
    cleaned series. Returns (dates_c, close_c, high_c, low_c, volume_c, {trail_atr: [MoveMFE]}) —
    the cleaned arrays feed persistence so descriptors match what the detector saw. `source`
    selects both the price table AND the exclusion ID domain (review C-1).

    LOCKBOX (wired 2026-07-24 per LOCKBOX_PRECOMMIT): bars on/after LOCKBOX_START are never
    loaded unless `unlock=True` — the sealed holdout cannot even reach the detector. `max_date`
    (exclusive) additionally caps the window; the effective cap is the earlier of the two."""
    from gws.phase0.exclusions import excluded_ids, load_exception_spans  # lazy
    from gws.phase0.lockbox import LOCKBOX_START, assert_not_in_lockbox  # lazy
    if source == "fmp":
        table, key, span_sources = "public.eod_prices", "ticker_id", ["fmp", "completeness_audit"]
    else:
        table, key, span_sources = ("ka_history.eod_history", "entity_id",
                                    ["norgate", "backfill_norgate_adjusted", "assert_adjustment_fresh"])
    # whole-entity exclusion (stale-adjustment / unfetchable): emit zero moves (review C2)
    if ticker_id in excluded_ids(conn, sources=span_sources):
        return [], np.array([]), np.array([]), np.array([]), np.array([]), {k: [] for k in scales}
    cap = max_date
    if not unlock and (cap is None or cap > LOCKBOX_START):
        cap = LOCKBOX_START
    rows = conn.execute(
        f"SELECT date, high, low, close AS raw_close, adjusted_close AS close, volume "
        f"FROM {table} "
        f"WHERE {key}=%s AND adjusted_close IS NOT NULL AND date < %s ORDER BY date",
        (ticker_id, cap)).fetchall()
    if not unlock:
        assert_not_in_lockbox([r["date"] for r in rows])     # belt-and-suspenders
    dates = [r["date"] for r in rows]
    spans = load_exception_spans(conn, ticker_id, sources=span_sources)
    close = np.array([r["close"] for r in rows], float)
    raw_close = np.array([r["raw_close"] for r in rows], float)
    # High/low are stored RAW in both tables; pairing them with adjusted close poisons ATR and
    # the trailing stop across every split (found 2026-07-24, pre-pilot). Scale each bar's H/L
    # by that bar's own adjustment factor so intrabar geometry is preserved in adjusted space.
    with np.errstate(divide="ignore", invalid="ignore"):
        factor = np.where(np.isfinite(raw_close) & (raw_close > 0), close / raw_close, np.nan)
    high = np.array([r["high"] for r in rows], float) * factor
    low = np.array([r["low"] for r in rows], float) * factor
    volume = np.array([r["volume"] for r in rows], float)
    # ratified $1 data-validity floor on the RAW traded price (universe.MIN_PRICE — adjusted
    # close would deflate deep history below any floor and erase the pre-split eras)
    from gws.phase0.universe import MIN_PRICE  # lazy — single source of the floor
    data_valid = np.isfinite(raw_close) & (raw_close >= MIN_PRICE)
    return detect_moves_clean(high, low, close, volume, dates, spans,
                              scales=scales, atr_period=atr_period, data_valid=data_valid)
