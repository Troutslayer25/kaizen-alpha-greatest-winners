"""Follow-up: reproduce the real-data signature (shifted 0.898 > real 0.753) with a STRONG
bidirectional location feature, then test the pivotal remedy: does REMOVING the anchor family
(as b_anchor_2 already does) recover a de-leak PASS on the shift@5 control?
"""
import sys
import numpy as np
sys.path.insert(0, r"C:\Users\scott\kaizen-alpha-greatest-winners")

from gws.phase_a1.move_detector_mfe import detect_moves_multiscale
from gws.common.negative_controls import negative_control_report, negative_control_verdicts
from gws.phase_a1.run_gate05_transfer import auc_fit_score

K, SAMPLE_EVERY, MIN_INDEX = 20, 5, 252
N_TICKERS, N_DAYS, SEED = 250, 3000, 20260719


def build():
    rng = np.random.default_rng(SEED)
    L, TK, D, CLEAN, LOC = [], [], [], [], []
    for g in range(N_TICKERS):
        close = 100 * np.cumprod(1 + rng.normal(0.0003, 0.02, N_DAYS))
        high, low = close * 1.006, close * 0.994
        by = detect_moves_multiscale(high, low, close, scales=(6.0,))
        troughs = np.array(sorted({m.trough_idx for ms in by.values() for m in ms}), int)
        idx = np.arange(MIN_INDEX, N_DAYS - K, SAMPLE_EVERY)
        lab = np.zeros(len(idx), int); clean = np.zeros(len(idx))
        # STRONG location feature: real trailing dist-from-low over a 40-bar window (bidirectional:
        # small right before AND right after a genuine low). This is what dist_from_low actually is.
        loc = np.zeros(len(idx))
        for j, i in enumerate(idx):
            ahead = troughs[(troughs >= i) & (troughs <= i + K)]
            lab[j] = int(ahead.size > 0)
            if ahead.size:
                clean[j] = 1.0 - (ahead[0] - i) / K
            w0 = max(0, i - 40)
            lo = low[w0:i + 1].min(); hi = high[w0:i + 1].max()
            loc[j] = (close[i] - lo) / (hi - lo + 1e-9)      # range_position: low value = near a recent low
        L.append(lab); TK.append(np.full(len(idx), g)); D.append(idx)
        CLEAN.append(clean); LOC.append(loc)
    return (np.concatenate(L), np.concatenate(TK), np.concatenate(D),
            np.concatenate(CLEAN), np.concatenate(LOC))


def probe(name, X, y, d, tk):
    rep = negative_control_report(X, y, d, auc_fit_score, tickers=tk, seed=SEED, n_null=25)
    p = (rep["shifted_within_ticker"] <= rep["shuffle_null"]["hi"] + 1e-9
         and rep["real"] > rep["shuffle_null"]["hi"] + 0.05)
    print(f"{name:34} real={rep['real']:.3f}  shuffle_hi={rep['shuffle_null']['hi']:.3f}  "
          f"shift@5={rep['shifted_within_ticker']:.3f}  -> B1 {'PASS' if p else 'FAIL'}", flush=True)
    return rep


def main():
    lab, tk, d, clean, loc = build()
    print(f"n={len(lab)} pos={lab.mean():.1%}", flush=True)
    rng = np.random.default_rng(1)
    cln = clean + rng.normal(0, 0.55, len(clean))
    # invert loc so 'near recent low' is the high-signal direction, add light noise -> strong bidirectional anchor
    locf = (1 - loc) + rng.normal(0, 0.25, len(loc))
    probe("clean forward ONLY", cln[:, None], lab, d, tk)
    probe("location/anchor ONLY (strong)", locf[:, None], lab, d, tk)
    probe("FULL (clean+location) = as b_anchor_1", np.column_stack([cln, locf]), lab, d, tk)
    print("   ^ reproduces real signature shifted>real when location present\n", flush=True)
    probe("REMEDY: location REMOVED (clean only)", cln[:, None], lab, d, tk)
    print("   ^ pivotal: does de-leak PASS once the anchor family is out?", flush=True)


if __name__ == "__main__":
    main()
