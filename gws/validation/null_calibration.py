"""Harness A — null-calibration of the discovery funnel (review 2026-07-03, C-1 exhibit).

The single most important statistical-validity check in the study: on data with NO real
association between features and labels, the discovery funnel must reject the null at close
to its nominal rate. Under the global null, BH-FDR also controls the family-wise error, so
the honest headline is `familywise_rate` — the fraction of trials in which ANY feature is
called significant at q<=alpha. Calibrated => ~alpha; anti-conservative => >> alpha.

The panels here deliberately carry the two dependence structures that break naive i.i.d.
inference (C-1): (1) features are within-ticker AR(1)-persistent, so a ticker has a stable
feature level; (2) labels are ticker-clustered and time-blocked (the overlapping multi-scale
move analog), so positives concentrate on a subset of tickers. Labels are drawn INDEPENDENTLY
of features — any rejection is therefore a false positive. Naive pooled tests over-count each
correlated row as independent evidence and fire far above alpha; ticker-clustered inference
(task C-1 fix) should pull `familywise_rate` back to ~alpha. This harness is the exhibit that
proves both halves.

    from gws.validation.null_calibration import make_null_panel, run_calibration
    naive = run_calibration(lambda fm, y, tk: univariate_screen(fm, y), n_trials=200)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import lfilter


def make_null_panel(n_tickers: int = 60, obs_per_ticker: int = 200, n_features: int = 20,
                    seed: int = 0, rho: float = 0.9, block_len: int = 20):
    """Pure-null panel with within-ticker AR(1) features and ticker-clustered block labels.

    Returns (feature_matrix, labels, ticker_ids). Labels are independent of the features, so
    the true number of predictive features is ZERO — every rejection is a false positive."""
    rng = np.random.default_rng(seed)
    n = n_tickers * obs_per_ticker
    X = np.empty((n, n_features))
    tickers = np.repeat(np.arange(n_tickers), obs_per_ticker)
    labels = np.zeros(n, dtype=int)
    scale = np.sqrt(max(1e-9, 1.0 - rho * rho))

    row = 0
    for _ in range(n_tickers):
        # AR(1) features around a per-ticker, per-feature mean (within-ticker persistence)
        mean = rng.normal(0.0, 1.0, n_features)
        innov = scale * rng.normal(0.0, 1.0, (obs_per_ticker, n_features))
        s = lfilter([1.0], [1.0, -rho], innov, axis=0)   # zero-mean AR(1)
        X[row:row + obs_per_ticker] = s + mean

        # labels: ticker-level propensity (U-shaped -> high across-ticker variance) placed in
        # contiguous time blocks. INDEPENDENT of X.
        p_g = rng.beta(0.3, 0.3)
        lab = np.zeros(obs_per_ticker, dtype=int)
        n_blocks = rng.poisson(max(0.0, p_g * obs_per_ticker / block_len))
        for _b in range(int(n_blocks)):
            st = int(rng.integers(0, obs_per_ticker))
            lab[st:st + block_len] = 1
        labels[row:row + obs_per_ticker] = lab
        row += obs_per_ticker

    fm = pd.DataFrame(X, columns=[f"f{j}" for j in range(n_features)])
    return fm, labels, tickers


def make_iid_panel(n_obs: int = 6000, n_features: int = 20, seed: int = 0, pos_rate: float = 0.3):
    """Fully independent baseline: one observation per 'ticker', i.i.d. features and labels.
    Naive BH is correctly calibrated here — this proves the harness measures real
    miscalibration rather than always failing."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0.0, 1.0, (n_obs, n_features))
    labels = (rng.random(n_obs) < pos_rate).astype(int)
    tickers = np.arange(n_obs)
    fm = pd.DataFrame(X, columns=[f"f{j}" for j in range(n_features)])
    return fm, labels, tickers


def run_calibration(screen_fn, *, n_trials: int = 200, alpha: float = 0.05,
                    panel_fn=make_null_panel, base_seed: int = 0, **panel_kwargs) -> dict:
    """Run `screen_fn(feature_matrix, labels, ticker_ids)` over `n_trials` fresh null panels.

    `screen_fn` must return a DataFrame with a boolean `significant` column (q<=alpha). Returns
    realized false-positive metrics; under the global null a valid pipeline yields
    familywise_rate ~ alpha and fp_rate <= alpha."""
    n_sig = n_feat = fw_hits = 0
    per_trial = []
    for t in range(n_trials):
        fm, labels, tickers = panel_fn(seed=base_seed + t, **panel_kwargs)
        res = screen_fn(fm, labels, tickers)
        k = int(np.asarray(res["significant"], dtype=bool).sum())
        n_sig += k
        n_feat += len(res)
        fw_hits += int(k > 0)
        per_trial.append(k)
    return {
        "n_trials": n_trials,
        "alpha": alpha,
        "fp_rate": n_sig / n_feat if n_feat else float("nan"),      # per-feature FP at q<=alpha
        "familywise_rate": fw_hits / n_trials,                      # trials with >=1 rejection
        "mean_rejections": float(np.mean(per_trial)) if per_trial else float("nan"),
    }
