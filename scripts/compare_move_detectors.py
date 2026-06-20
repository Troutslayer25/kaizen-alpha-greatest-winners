"""Run ATR-swing vs threshold-free multi-scale MFE detectors on a synthetic panel.

A small-sample comparison (no DB) to evidence the design choices before committing a
detector to Phase A1. Reports, per method: move count, magnitude distribution, the share
of sub-10% moves (the continuous-vs-floored difference the debate hinged on), and — for
MFE — mean recorded MAE and how the population grows as the scale tightens.

Usage:  python -m scripts.compare_move_detectors
"""
from __future__ import annotations

import numpy as np

from gws.synthetic.generate import generate_panel
from gws.phase_a1.trough_detector import detect_moves as detect_atr_swing
from gws.phase_a1.move_detector_mfe import detect_moves_mfe


def _pct(mags, q):
    return float(np.percentile(mags, q)) if len(mags) else float("nan")


def _summary(mags, mae=None):
    mags = np.asarray(mags, float)
    sub10 = float(np.mean(mags < 0.10)) if len(mags) else float("nan")
    line = (f"n={len(mags):>5}  mag p50={_pct(mags,50):+.2f} p90={_pct(mags,90):+.2f} "
            f"max={mags.max() if len(mags) else float('nan'):+.2f}  <10%={sub10:.0%}")
    if mae is not None and len(mae):
        line += f"  mean_MAE={np.mean(mae):.3f}"
    return line


def main():
    panel, _ = generate_panel(n_tickers=15, n_days=2520, seed=20, planted_per_ticker=3)
    tickers = sorted(panel["ticker_id"].unique())

    atr_mags = []
    mfe = {2.0: ([], []), 6.0: ([], []), 15.0: ([], [])}   # scale -> (mags, maes)

    for tk in tickers:
        sub = panel[panel["ticker_id"] == tk].sort_values("date")
        h, l, c = sub["high"].to_numpy(), sub["low"].to_numpy(), sub["close"].to_numpy()
        atr_mags += [m.trough_gain_pct for m in detect_atr_swing(h, l, c)]
        for k, (mags, maes) in mfe.items():
            ms = detect_moves_mfe(h, l, c, trail_atr=k)
            mags += [m.magnitude for m in ms]
            maes += [m.mae for m in ms]

    print(f"Synthetic panel: {len(tickers)} tickers x 2520 days\n")
    print(f"  ATR-swing (3xATR + 10% floor) : {_summary(atr_mags)}")
    for k in sorted(mfe):
        mags, maes = mfe[k]
        print(f"  MFE trail={k:<4} (threshold-free): {_summary(mags, maes)}")

    print("\nKey reads:")
    print("  - ATR-swing has ~no sub-10% moves (floored); MFE surfaces the full continuum.")
    print("  - Tighter MFE scale -> more moves (swing legs inside trends); looser -> fewer (arcs).")
    print("  - MFE records MAE per move (early drawdown), available as a characterization axis.")


if __name__ == "__main__":
    main()
