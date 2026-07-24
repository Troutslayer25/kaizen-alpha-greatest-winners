"""Decisive calibration test for shift_labels_within_ticker(k=5) on the forward frame class.

Question (Cell C charge #2): on a SYNTHETIC forward frame with realistic overlapping-window
label autocorrelation (real multiscale detector on random walks, sample_every=5, K=20), does
the within-ticker label-shift control COLLAPSE to chance on GENUINELY predictive, NON-ANCHORED
signal? If it collapses -> control is valid and 0.898 is damning. If it stays high on
known-clean forward signal -> control is structurally mis-calibrated for this frame class.
"""
import sys
import numpy as np
sys.path.insert(0, r"C:\Users\scott\kaizen-alpha-greatest-winners")

from gws.phase_a1.move_detector_mfe import detect_moves_multiscale
from gws.common.negative_controls import (negative_control_report,
                                          negative_control_verdicts,
                                          shift_labels_within_ticker,
                                          shuffle_labels)
from gws.phase_a1.run_gate05_transfer import auc_fit_score

K = 20
SAMPLE_EVERY = 5
MIN_INDEX = 252
N_TICKERS = 250
N_DAYS = 3000
SEED = 20260719
LABEL_SCALES = (6.0,)      # primary scale trail_6 -> single-scale forward labels (matches addendum pin)


def build_frame(seed):
    rng = np.random.default_rng(seed)
    all_pos, all_lab, all_tk = [], [], []
    all_clean, all_anchor, all_noise = [], [], []
    for g in range(N_TICKERS):
        rets = rng.normal(0.0003, 0.02, N_DAYS)
        close = 100 * np.cumprod(1 + rets)
        high, low = close * 1.006, close * 0.994
        by_scale = detect_moves_multiscale(high, low, close, scales=LABEL_SCALES)
        troughs = np.array(sorted({m.trough_idx for ms in by_scale.values() for m in ms}), dtype=int)
        idx = np.arange(MIN_INDEX, N_DAYS - K, SAMPLE_EVERY)
        lab = np.zeros(len(idx), dtype=int)
        clean = np.zeros(len(idx)); anchor = np.zeros(len(idx))
        for j, i in enumerate(idx):
            ahead = troughs[(troughs >= i) & (troughs <= i + K)]         # label window (matches labeling.py)
            lab[j] = int(ahead.size > 0)
            # CLEAN forward signal: elevated ONLY when a trough is imminently AHEAD (leading, non-retrodictive)
            if ahead.size:
                clean[j] = (1.0 - (ahead[0] - i) / K)                    # ramps up as the trough approaches
            # ANCHOR/location-like: elevated ONLY just AFTER a recent trough (retrodictive, like dist_from_low)
            behind = troughs[(troughs <= i) & (troughs >= i - K)]
            if behind.size:
                anchor[j] = (1.0 - (i - behind[-1]) / K)                 # proximity to the most recent past low
        all_pos.append(idx); all_lab.append(lab); all_tk.append(np.full(len(idx), g))
        all_clean.append(clean); all_anchor.append(anchor)
        all_noise.append(rng.normal(0, 1, len(idx)))
    lab = np.concatenate(all_lab); tk = np.concatenate(all_tk)
    dates = np.concatenate(all_pos)                                       # integer "date" proxy = bar index; monotone within ticker
    clean = np.concatenate(all_clean); anchor = np.concatenate(all_anchor); noise = np.concatenate(all_noise)
    return lab, tk, dates, clean, anchor, noise


def add_noise(sig, snr, seed):
    rng = np.random.default_rng(seed)
    return sig + rng.normal(0, snr, len(sig))


def run_probe(name, X, y, dates, tk, shift_ks=(5,)):
    rep = negative_control_report(X, y, dates, auc_fit_score, tickers=tk, seed=SEED, n_null=25)
    verd = negative_control_verdicts(rep)
    line = (f"{name:28} real={rep['real']:.3f}  "
            f"shuffle=({rep['shuffle_null']['lo']:.3f},{rep['shuffle_null']['hi']:.3f})  "
            f"shift@5={rep['shifted_within_ticker']:.3f}")
    extra = {}
    for kk in shift_ks:
        if kk == 5:
            continue
        s = float(auc_fit_score(X, shift_labels_within_ticker(y, tk, kk), dates))
        extra[kk] = s
        line += f"  shift@{kk}={s:.3f}"
    b1_pass = (rep["shifted_within_ticker"] <= rep["shuffle_null"]["hi"] + 1e-9
               and rep["real"] > rep["shuffle_null"]["hi"] + 0.05)
    line += f"  -> B1 {'PASS' if b1_pass else 'FAIL'}"
    print(line, flush=True)
    return rep, verd, extra


def main():
    print("building synthetic forward frame (real detector on random walks) ...", flush=True)
    lab, tk, dates, clean, anchor, noise = build_frame(SEED)
    print(f"n_points={len(lab)}  positive={lab.mean():.1%}  n_tickers={len(np.unique(tk))}", flush=True)

    # label autocorrelation at the relevant lags (position units), within ticker
    def label_autocorr(lag_pos):
        cs = []
        for g in np.unique(tk):
            yy = lab[tk == g].astype(float)
            if len(yy) > lag_pos + 5 and yy.std() > 0 and np.roll(yy, lag_pos)[lag_pos:].std() > 0:
                a, b = yy[lag_pos:], yy[:-lag_pos]
                if a.std() > 0 and b.std() > 0:
                    cs.append(np.corrcoef(a, b)[0, 1])
        return float(np.nanmean(cs)) if cs else float("nan")
    print(f"within-ticker label autocorr: lag1(5bar)={label_autocorr(1):.3f} "
          f"lag5(25bar)={label_autocorr(5):.3f} lag12(60bar)={label_autocorr(12):.3f}", flush=True)

    # tune noise so each planted single-feature 'real' AUC ~ 0.75 (analog of the real 0.753)
    cln = add_noise(clean, 0.55, SEED + 1)
    anc = add_noise(anchor, 0.55, SEED + 2)

    print("\n--- SINGLE-FEATURE PROBES (shift_k in {5,12,20} positions) ---", flush=True)
    run_probe("clean forward ONLY", cln[:, None], lab, dates, tk, shift_ks=(5, 12, 20))
    run_probe("anchor/location ONLY", anc[:, None], lab, dates, tk, shift_ks=(5, 12, 20))
    run_probe("clean+anchor (full-set analog)", np.column_stack([cln, anc]), lab, dates, tk, shift_ks=(5, 12, 20))
    run_probe("pure noise (sanity null)", noise[:, None], lab, dates, tk, shift_ks=(5, 12, 20))

    # candidate replacement control: era-blocked run-length-preserving label permutation
    print("\n--- candidate replacement: within-ticker BLOCK permutation (preserves run-lengths) ---", flush=True)
    def block_permute(y, tickers, seed=0):
        rng = np.random.default_rng(seed)
        out = y.copy()
        for g in np.unique(tickers):
            idx = np.where(tickers == g)[0]
            yy = y[idx]
            # split into maximal runs of equal label, shuffle run order
            runs, s = [], 0
            for e in range(1, len(yy) + 1):
                if e == len(yy) or yy[e] != yy[s]:
                    runs.append(yy[s:e]); s = e
            rng.shuffle(runs)
            out[idx] = np.concatenate(runs) if runs else yy
        return out
    for nm, X in (("clean forward ONLY", cln[:, None]), ("anchor/location ONLY", anc[:, None])):
        scores = [auc_fit_score(X, block_permute(lab, tk, SEED + i), dates) for i in range(15)]
        real = auc_fit_score(X, lab, dates)
        print(f"{nm:28} real={real:.3f}  block-perm band=({np.min(scores):.3f},{np.max(scores):.3f}) "
              f"mean={np.mean(scores):.3f}", flush=True)


if __name__ == "__main__":
    main()
