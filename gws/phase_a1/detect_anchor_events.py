"""B-anchor-3 — anchor-event detection + outcome labeling + persistence (spec 36a13da).

Six frozen entry families (A base breakout w/ shape tags, B tight-range breakout,
C pullback reclaim, D expectation breaker, E gap-up, F trendline break), uniform outcome
label (+20% MFE before close < entry−2×ATR21, H=126), family-native stop levels recorded.
Primary run_id 'banchor3_pilot'; each robustness variant persists under
'banchor3_pilot:<axis>=<val>'. All events land in gws.anchor_events (permanent catalog).

    python -m gws.phase_a1.detect_anchor_events
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

from gws.phase_a1.run_gate05_detection import RUN_ID as MOVES_RUN_ID  # noqa: E402
from gws.phase_a1.run_gate05_detection import load_pilot              # noqa: E402
from gws.phase_a1.series_guard import assert_series_hash              # noqa: E402
from gws.phase0.exclusions import forward_fill_excluded, tradeable_mask  # noqa: E402
from gws.phase0.lockbox import LOCKBOX_START                          # noqa: E402

RUN = "banchor3_pilot"
H = 126
WIN_PCT = 0.20
STOP_ATR = 2.0
DEDUP = 21

P = dict(a_win=60, a_gap=5, a_depth=0.35, a_vol=1.5,
         b_rng=1.5, b_inside=2,
         c_pull_lo=0.08, c_pull_hi=0.15, c_reclaim=5,
         d_rng=1.5, d_above="open",
         e_gap=0.75, e_vol=1.5, e_prox=15,
         f_touch=3, f_tol=0.02, f_win=90)

VARIANTS = [("a_depth", 0.25), ("a_depth", 0.45), ("a_vol", 1.25), ("a_vol", 2.0),
            ("a_win", 40), ("a_win", 90), ("b_inside", 3), ("b_rng", 2.0),
            ("c_pull_lo", 0.05), ("c_reclaim", 3), ("d_rng", 2.0), ("d_above", "high"),
            ("e_gap", 1.0), ("e_vol", 2.0), ("e_prox", 5),
            ("f_touch", 2), ("f_touch", 4), ("f_tol", 0.01), ("f_tol", 0.03),
            ("f_win", 60), ("f_win", 120)]


def load_series(conn, eid):
    """Replicates the canonical loader's cleaning EXACTLY (mask must match the hash) but
    also carries adjusted OPEN (families D/E need it; canonical loader omits it)."""
    rows = conn.execute(
        "SELECT date, open, high, low, close AS rawc, adjusted_close AS close, volume "
        "FROM ka_history.eod_history WHERE entity_id=%s AND adjusted_close IS NOT NULL "
        "AND date < %s ORDER BY date", (eid, LOCKBOX_START)).fetchall()
    if not rows:
        return None
    d = [r["date"] for r in rows]
    c = np.array([r["close"] for r in rows], float)
    raw = np.array([r["rawc"] for r in rows], float)
    with np.errstate(divide="ignore", invalid="ignore"):
        f = np.where(np.isfinite(raw) & (raw > 0), c / raw, np.nan)
    h = np.array([r["high"] for r in rows], float) * f
    lo = np.array([r["low"] for r in rows], float) * f
    o = np.array([r["open"] for r in rows], float) * f
    v = np.array([r["volume"] for r in rows], float)
    finite = np.isfinite(c) & np.isfinite(h) & np.isfinite(lo)
    mask = tradeable_mask(d, v, ()) & finite & np.isfinite(raw) & (raw >= 1.0)
    if not mask.any():
        return None
    c2 = forward_fill_excluded(c, mask); h2 = forward_fill_excluded(h, mask)
    l2 = forward_fill_excluded(lo, mask); o2 = forward_fill_excluded(o, mask)
    s = int(np.argmax(mask))
    return (d[s:], o2[s:], h2[s:], l2[s:], c2[s:], v[s:])


def atr(h, lo, c, p):
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    return pd.Series(tr).ewm(alpha=1 / p, adjust=False).mean().to_numpy()


def detect_all(d, o, h, lo, c, v, p, fams=frozenset("ABCDEF")):
    n = len(c)
    a21 = atr(h, lo, c, 21); a40 = atr(h, lo, c, 40)
    adv = pd.Series(v).rolling(50).mean().shift(1).to_numpy()
    ema21 = pd.Series(c).ewm(span=21, adjust=False).mean().to_numpy()
    sma50 = pd.Series(c).rolling(50).mean().to_numpy()
    ev = []                                    # (idx, family, tag, native_stop)
    need_a = bool(fams & {"A", "C", "E"})
    W, G = p["a_win"], p["a_gap"]

    hs = pd.Series(h); ls_ = pd.Series(lo)
    winmax = hs.rolling(W).max().shift(G + 1).to_numpy()   # max high over [B-W-G, B-G-1]
    winmin = ls_.rolling(W).min().shift(G + 1).to_numpy()
    a_events = []
    for B in (range(W + G + 1, n) if need_a else ()):
        if not (c[B] > winmax[B] and v[B] >= p["a_vol"] * (adv[B] or np.inf)):
            continue
        depth = (winmax[B] - winmin[B]) / winmax[B]
        if not depth <= p["a_depth"]:
            continue
        s0, s1 = B - W - G, B - G                # base window slice [s0, s1)
        wh, wl, wc = h[s0:s1], lo[s0:s1], c[s0:s1]
        length = len(wc) - int(np.argmax(wh))
        mid_lo = int(np.argmin(wl))
        rounded = len(wc) * 0.2 <= mid_lo <= len(wc) * 0.8
        tag = None
        pole = c[s0] / c[max(0, s0 - 40)] - 1 if s0 >= 40 else 0.0
        if depth <= 0.15 and length >= 25:
            tag = "flat"
        elif 0.15 < depth <= 0.33 and length >= 35 and rounded:
            tag = "cup"
        elif tag is None and 0.15 < depth <= 0.33 and rounded:
            hd = wl[-10:]
            if len(wc) >= 45 and hd.min() >= winmax[B] - 0.5 * (winmax[B] - winmin[B]) \
                    and wc[-1] < wc[-10]:
                tag = "cup_handle"
        if tag is None:
            mins = [i for i in range(2, len(wl) - 2)
                    if wl[i] == wl[max(0, i - 7):i + 8].min()]
            if len(mins) >= 2 and mins[-1] - mins[0] >= 15 and wl[mins[-1]] < wl[mins[0]]:
                tag = "double_bottom"
        if tag is None and pole >= 0.90 and depth <= 0.25 and 15 <= length <= 25:
            tag = "high_tight_flag"
        if tag is None and depth <= 0.20 and length >= 50 and rounded:
            tag = "saucer"
        if "A" in fams:
            ev.append((B, "A", tag, c[B] - STOP_ATR * a21[B]))
        a_events.append(B)

    i = 0 if "B" in fams else n                 # Family B: expansion + inside sessions
    rng = h - lo
    while i < n - 3:
        if (rng[i] >= p["b_rng"] * (a21[i - 1] if i else np.inf)
                and v[i] >= 1.5 * (adv[i] or np.inf)
                and (rng[i] > 0 and (c[i] - lo[i]) / rng[i] >= 0.6)):
            j, inside = i + 1, 0
            while j < n and lo[j] >= lo[i] and h[j] <= h[i]:
                inside += 1; j += 1
            if inside >= p["b_inside"] and j < n and c[j] > h[i]:
                tag = "mini_coil"
                if inside <= 2 and all(rng[k] <= 0.5 * a21[k] and lo[k] >= (h[i] + lo[i]) / 2
                                       for k in range(i + 1, j)):
                    tag = "doji_flag"
                ev.append((j, "B", tag, lo[j - 1]))
                i = j
        i += 1

    wk = pd.DataFrame({"h": h, "lo": lo, "c": c},
                      index=pd.to_datetime(pd.Series(d))).resample("W-FRI").agg(
        {"h": "max", "lo": "min", "c": "last"}).dropna()
    wkc = wk["c"].to_numpy(); wkh = wk["h"].to_numpy()
    wkr = (wk["h"] - wk["lo"]).to_numpy()
    wkatr = pd.Series(wkr).rolling(10).mean().to_numpy()
    didx = {dd: i for i, dd in enumerate(d)}
    wk_end = [min(ts.date(), d[-1]) for ts in wk.index]
    for w in (range(2, len(wk)) if "B" in fams else ()):
        trio = wkc[w - 2:w + 1]
        if trio.min() > 0 and trio.max() / trio.min() <= 1.015:      # three-weeks-tight
            tight_hi = wkh[w - 2:w + 1].max()
            start = didx.get(wk_end[w])
            if start:
                for B in range(start + 1, min(start + 11, n)):
                    if c[B] > tight_hi:
                        ev.append((B, "B", "three_weeks_tight", lo[B - 1])); break
        if w >= 1 and wkr[w - 1] >= 1.5 * (wkatr[w - 2] if w >= 2 else np.inf):
            big = w - 1                                              # short stroke
            if wkr[big] > 0 and (wkc[big] - wk["lo"].to_numpy()[big]) / wkr[big] >= 0.8 \
                    and wkh[w] <= wkh[big] and wkc[w] >= wkc[big] * 0.99:
                two_hi = max(wkh[big], wkh[w])
                start = didx.get(wk_end[w])
                if start:
                    for B in range(start + 1, min(start + 11, n)):
                        if c[B] > two_hi:
                            ev.append((B, "B", "short_stroke", lo[B - 1])); break

    for a in (a_events if "C" in fams else ()):  # Family C variants keyed off A events
        hstar_i = a
        for t in range(a + 1, min(a + 31, n)):
            if h[t] > h[hstar_i]:
                hstar_i = t
            drop = 1 - lo[t] / h[hstar_i]
            if p["c_pull_lo"] <= drop <= p["c_pull_hi"] and lo[t] <= ema21[t] \
                    and ema21[t] > ema21[t - 5] and t >= a + 5:
                for B in range(t + 1, min(t + 16, n)):
                    if c[B] > h[max(0, B - p["c_reclaim"]):B].max():
                        ev.append((B, "C", "fbo_21ema", c[B] * 0.95)); break
                break
        for t in range(a + 1, min(a + 61, n)):   # 10-week first touch
            if lo[t] <= sma50[t] and sma50[t] > sma50[t - 5]:
                for B in range(t + 1, min(t + 16, n)):
                    if c[B] > h[max(0, B - 5):B].max():
                        ev.append((B, "C", "tenweek_first_touch", c[B] * 0.95)); break
                break
        base_low = winmin[a]                     # shakeout reclaim
        for t in range(a + 1, min(a + 61, n)):
            if base_low * 0.9 <= lo[t] < base_low:
                for B in range(t, min(t + 16, n)):
                    if c[B] >= lo[t] * 1.10:
                        ev.append((B, "C", "shakeout_reclaim", c[B] * 0.95)); break
                break

    for R in (range(1, n - 1) if "D" in fams else ()):  # Family D
        if c[R] < o[R] and rng[R] >= p["d_rng"] * a21[R - 1]:
            ref = o[R] if p["d_above"] == "open" else h[R]
            if o[R + 1] > ref:
                ev.append((R + 1, "D", None, c[R]))

    h126 = hs.rolling(126).max().to_numpy()
    a_set = set(a_events)
    for B in (range(1, n) if "E" in fams else ()):  # Family E
        gap = o[B] - h[B - 1]
        if gap >= p["e_gap"] * a40[B - 1] and v[B] >= p["e_vol"] * (adv[B] or np.inf) \
                and c[B] >= o[B]:
            if h[B] >= h126[B] or any((B - k) in a_set for k in range(p["e_prox"] + 1)):
                ev.append((B, "E", None, lo[B]))

    FW, FT = p["f_win"], p["f_tol"]              # Family F
    swings = ([i for i in range(10, n - 5)
               if h[i] == h[max(0, i - 10):i + 11].max()] if "F" in fams else [])
    for si, a0 in (list(enumerate(swings)) if "F" in fams else ()):
        for a1 in swings[si + 1:]:
            if a1 - a0 < 5 or a1 - a0 > FW or h[a1] >= h[a0]:
                continue
            slope = (h[a1] - h[a0]) / (a1 - a0)
            end = min(a0 + FW + 1, n)
            line = h[a0] + slope * (np.arange(a0, end) - a0)
            seg_h, seg_c = h[a0:end], c[a0:end]
            near = (seg_h >= line * (1 - FT)) & (seg_c <= line)
            tidx = np.where(near)[0]
            picked, last = [], -9
            for tt in tidx:
                if tt - last >= 3:
                    picked.append(tt); last = tt
            if len(picked) < p["f_touch"]:
                continue
            after = picked[-1] + 1
            brk = np.where((seg_c[after:] > line[after:] * 1.01))[0]
            for bb in brk:
                B = a0 + after + bb
                if c[B] > c[B - 1]:
                    ev.append((B, "F", None, lo[B - 1]))
                    break
            break
    return ev


def label_outcome(B, o, h, lo, c, a21):
    entry = c[B]
    stop = entry - STOP_ATR * a21[B]
    tgt = entry * (1 + WIN_PCT)
    n = len(c)
    mfe = mae = 0.0
    for t in range(B + 1, min(B + H + 1, n)):
        mfe = max(mfe, h[t] / entry - 1)
        mae = min(mae, lo[t] / entry - 1)
        if h[t] >= tgt:
            return "winner", t - B, mfe, mae, stop
        if c[t] < stop:
            return "failed", t - B, mfe, mae, stop
    return "unresolved", None, mfe, mae, stop


def run_variant(conn, series_cache, run_id, p, fams=frozenset("ABCDEF")):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gws.anchor_events WHERE run_id=%s", (run_id,))
    counts: dict = {}
    rows = []
    for eid, (d, o, h, lo, c, v) in series_cache.items():
        a21 = atr(h, lo, c, 21)
        seen: dict = {}
        for B, fam, tag, native in sorted(detect_all(d, o, h, lo, c, v, p, fams)):
            if B - seen.get(fam, -99) < DEDUP:
                continue
            seen[fam] = B
            outcome, bars, mfe, mae, stop = label_outcome(B, o, h, lo, c, a21)
            rows.append((run_id, eid, d[B], fam, tag, float(c[B]), float(stop),
                         float(native) if native == native else None, outcome,
                         d[B + bars] if bars else None, float(mfe), float(mae), bars))
            counts[fam] = counts.get(fam, 0) + 1
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO gws.anchor_events (run_id, ticker_id, event_date, family, "
            "variant_tag, entry_price, stop_price, native_stop, outcome, outcome_date, "
            "fwd_mfe, fwd_mae, bars_to_resolution) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s) ON CONFLICT (run_id, ticker_id, event_date, family) DO NOTHING",
            rows)
    return counts, len(rows)


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    pilot = load_pilot()
    cache = {}
    for r in pilot:
        if r["kind"] != "stratified":
            continue
        eid = int(r["entity_id"])
        s = load_series(conn, eid)
        if s is None:
            continue
        assert_series_hash(conn, MOVES_RUN_ID, eid, s[0])
        cache[eid] = s
    print(f"series loaded (hash-guarded): {len(cache)}", flush=True)

    counts, total = run_variant(conn, cache, RUN, P)
    print(f"PRIMARY {RUN}: {total} events {counts}", flush=True)
    for key, val in VARIANTS:
        p2 = dict(P); p2[key] = val
        vc, vt = run_variant(conn, cache, f"{RUN}:{key}={val}", p2,
                             fams=frozenset(key[0].upper()))
        print(f"  variant {key}={val}: {vt} events", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
