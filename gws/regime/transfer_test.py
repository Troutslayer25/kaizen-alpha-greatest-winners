"""Emotional-invariance transfer test — the study's central instrument (review C-2).

The hypothesis (master §1): behavioral/emotional features transfer across regimes; structural
features do not. The earlier design confounded this three ways; this module fixes all three so
the test can actually confirm or deny the hypothesis rather than an artifact:

  1. SYMMETRIC normalization. Both feature classes are expressed regime-relative
     (`regime_relative_normalize`), so a transfer gap is attributable to CONTENT, not to the
     fact that emotional features were z-scored and structural ones were raw magnitudes.
  2. IN-ERA BASELINE. The statistic is a transfer RATIO — out-of-era skill relative to in-era
     skill — not a raw out-of-era AUC. "Structural doesn't transfer" is only meaningful against
     how well structural features predict in-era in the first place.
  3. MANY era pairs. The conclusion is a DISTRIBUTION of transfer ratios across >=3 ordered era
     pairs (full matrix at A3), not a single early->late split (N=1 regime transition).

`fit_score_fn(X_tr, y_tr, X_te, y_te) -> auc` is injected so this module stays model-agnostic.
Pre-committed decision rule: invariance is SUPPORTED only if the emotional-class transfer ratio
exceeds the structural-class ratio across a majority of era pairs (see phases doc)."""
from __future__ import annotations

import numpy as np


def regime_relative_normalize(values, era) -> np.ndarray:
    """Z-score `values` within each era. Applied to BOTH feature classes (the symmetry fix)."""
    v = np.asarray(values, float)
    era = np.asarray(era)
    out = np.zeros_like(v)
    for e in np.unique(era):
        m = era == e
        col = v[m]
        mu, sd = np.nanmean(col), np.nanstd(col)
        out[m] = (col - mu) / sd if sd > 0 else 0.0
    return out


def transfer_ratio(auc_out: float, auc_in: float, chance: float = 0.5) -> float:
    """Out-of-era skill relative to in-era skill: (auc_out - chance) / (auc_in - chance).
    ~1 = transfers fully; ~0 = no transfer; NaN when the feature had no in-era skill to begin
    with (so a transfer 'failure' isn't confused with in-era uselessness)."""
    denom = auc_in - chance
    if denom <= 1e-6:
        return float("nan")
    return float((auc_out - chance) / denom)


def era_pair_transfer(fit_score_fn, X, y, era, train_era, test_era, *, holdout_frac=0.3,
                      seed=0) -> float:
    """Transfer ratio for one ordered era pair: train on train_era (minus a holdout), measure
    in-era AUC on that holdout and out-of-era AUC on test_era, return their ratio."""
    X = np.asarray(X, float)
    y = np.asarray(y)
    era = np.asarray(era)
    m_tr, m_te = era == train_era, era == test_era
    Xtr, ytr = X[m_tr], y[m_tr]
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(ytr))
    cut = int((1 - holdout_frac) * len(idx))
    tr, ho = idx[:cut], idx[cut:]
    if len(np.unique(ytr[tr])) < 2 or len(np.unique(ytr[ho])) < 2 or len(np.unique(y[m_te])) < 2:
        return float("nan")
    auc_in = fit_score_fn(Xtr[tr], ytr[tr], Xtr[ho], ytr[ho])
    auc_out = fit_score_fn(Xtr[tr], ytr[tr], X[m_te], y[m_te])
    return transfer_ratio(auc_out, auc_in)


def transfer_distribution(fit_score_fn, X, y, era, *, seed=0) -> dict:
    """Transfer ratios across ALL ordered era pairs. Returns per-pair ratios + summary."""
    eras = list(np.unique(era))
    ratios = {}
    for a in eras:
        for b in eras:
            if a == b:
                continue
            ratios[(a, b)] = era_pair_transfer(fit_score_fn, X, y, era, a, b, seed=seed)
    vals = np.array([r for r in ratios.values() if r == r])
    return {"pairwise": ratios,
            "median": float(np.median(vals)) if vals.size else float("nan"),
            "n_pairs": int(vals.size)}


def invariance_supported(emotional_ratios, structural_ratios, *, min_pairs: int = 3) -> dict:
    """Pre-committed decision rule (C-2). Invariance is SUPPORTED iff there are >=min_pairs
    comparable era pairs AND the emotional-class transfer ratio exceeds the structural-class
    ratio in a MAJORITY of them. Returns the verdict plus the supporting counts."""
    e = np.asarray(emotional_ratios, float)
    s = np.asarray(structural_ratios, float)
    m = ~(np.isnan(e) | np.isnan(s))
    e, s = e[m], s[m]
    n = e.size
    wins = int((e > s).sum())
    supported = bool(n >= min_pairs and wins > n / 2)
    return {"supported": supported, "n_pairs": n, "emotional_wins": wins,
            "emotional_median": float(np.median(e)) if n else float("nan"),
            "structural_median": float(np.median(s)) if n else float("nan")}
