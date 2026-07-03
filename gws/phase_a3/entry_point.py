"""Entry-point analysis & trough-vs-breakout adjudication (Phase A3, §12.2 / risk #2).

The study's #2-ranked risk: moves are trough-anchored, but the user trades buyable PIVOTS
(breakouts / points of strength). This is the instrument the Gate 0.5 memo turns on. Two review
corrections are baked in:

  * STOP-CONDITIONED metric (practitioner P-1). Unstopped forward MFE/MAE rewards deep-drawdown
    entries a disciplined trader is stopped out of before the MFE exists. `stop_conditioned_outcome`
    walks the path and resolves win/loss at whichever of {+target, -stop} is hit first — so the
    metric measures HARVESTABLE, rule-following expectancy, not statistician's pain.
  * ANCHOR comparison + winner-POPULATION overlap (practitioner P-2): §12.2 compares trough vs
    breakout anchoring on stop-conditioned expectancy AND on which names each admits.

Deployment-matched: entries are scored by FORWARD reward/risk from the entry's own date (no
hindsight). Pure and testable.
"""
from __future__ import annotations

import numpy as np


def forward_mfe_mae(close, i, horizon):
    """Unstopped forward max-favorable / max-adverse excursion from entry i over `horizon` bars,
    relative to close[i]. (Descriptive only — see stop_conditioned_outcome for the tradeable
    metric; a huge MFE with a deep MAE is exactly the trap P-1 warns about.)"""
    close = np.asarray(close, float)
    j = min(len(close) - 1, i + horizon)
    if j <= i or close[i] <= 0:
        return np.nan, np.nan
    fwd = close[i + 1:j + 1] / close[i] - 1.0
    return float(fwd.max()), float(fwd.min())


def stop_conditioned_outcome(close, i, *, target, stop, horizon):
    """Walk forward from entry i; resolve at whichever of {+target, -stop} is hit FIRST (intrabar
    order unknown -> close-based, conservative). Returns {outcome, bars, exit_return}. `target`
    and `stop` are positive fractions (e.g. 0.20 and 0.08)."""
    close = np.asarray(close, float)
    n = len(close)
    if close[i] <= 0:
        return {"outcome": "invalid", "bars": 0, "exit_return": np.nan}
    for t in range(i + 1, min(n, i + horizon + 1)):
        r = close[t] / close[i] - 1.0
        if r <= -stop:
            return {"outcome": "loss", "bars": t - i, "exit_return": float(r)}
        if r >= target:
            return {"outcome": "win", "bars": t - i, "exit_return": float(r)}
    last = min(n - 1, i + horizon)
    return {"outcome": "timeout", "bars": last - i, "exit_return": float(close[last] / close[i] - 1.0)}


def entry_expectancy(close, entries, *, target, stop, horizon):
    """Stop-conditioned expectancy over a set of entry indices: win rate under the stop policy,
    average win / loss, and expectancy (mean exit return). This is the per-entry-type score §12.2
    adjudicates on."""
    outs = [stop_conditioned_outcome(close, int(i), target=target, stop=stop, horizon=horizon)
            for i in entries]
    outs = [o for o in outs if o["outcome"] != "invalid"]
    if not outs:
        return {"n": 0, "win_rate": np.nan, "expectancy": np.nan, "avg_win": np.nan, "avg_loss": np.nan}
    wins = [o["exit_return"] for o in outs if o["outcome"] == "win"]
    losses = [o["exit_return"] for o in outs if o["outcome"] == "loss"]
    return {
        "n": len(outs),
        "win_rate": float(np.mean([o["outcome"] == "win" for o in outs])),
        "expectancy": float(np.mean([o["exit_return"] for o in outs])),
        "avg_win": float(np.mean(wins)) if wins else np.nan,
        "avg_loss": float(np.mean(losses)) if losses else np.nan,
    }


def breakout_entries(close, move, *, lookback=20):
    """'Points of strength' along a move: bars (trough..peak) where close makes a new `lookback`-day
    high — the breakout/continuation entries a pivot trader actually takes (never local lows)."""
    close = np.asarray(close, float)
    ti, pi = int(move.trough_idx), int(move.peak_idx)
    outs = []
    for t in range(ti + 1, pi + 1):
        lo = max(0, t - lookback + 1)
        if close[t] >= close[lo:t + 1].max() and close[t] > close[t - 1]:
            outs.append(t)
    return outs


def trough_vs_breakout(close, moves, *, target=0.20, stop=0.08, horizon=60, lookback=20):
    """Compare stop-conditioned entry expectancy anchoring at the TROUGH vs at BREAKOUTS (points
    of strength) across a set of moves. Returns both expectancies — the §12.2 adjudication. If the
    trough still wins under stop discipline, that's a genuinely surprising, believable finding."""
    trough_entries = [int(m.trough_idx) for m in moves]
    bo_entries = [e for m in moves for e in breakout_entries(close, m, lookback=lookback)]
    return {
        "trough": entry_expectancy(close, trough_entries, target=target, stop=stop, horizon=horizon),
        "breakout": entry_expectancy(close, bo_entries, target=target, stop=stop, horizon=horizon),
    }


def population_overlap(names_a, names_b) -> dict:
    """Winner-population overlap between two anchor definitions (review P-2). `names_a`/`names_b`
    are sets of move-identities (e.g. (ticker_id, start_date)). Returns Jaccard + the disagreement
    sets to eyeball (are trough-only winners V-recoveries? are breakout-only ones base leaders?)."""
    a, b = set(names_a), set(names_b)
    union = a | b
    return {
        "jaccard": (len(a & b) / len(union)) if union else float("nan"),
        "only_a": sorted(a - b), "only_b": sorted(b - a), "n_both": len(a & b),
    }
