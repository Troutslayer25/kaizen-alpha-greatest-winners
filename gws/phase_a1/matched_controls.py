"""Matched controls for the discovery dataset (case-control design, Phase A1).

For each setup observation, sample control (ticker, date) points matched on a minimal
bucket set (date, size, industry, liquidity). Used by the discovery analyses
(univariate, neutralization) — distinct from setup_labels (blueprint T1). Keeps the
matching set deliberately minimal and reports an over-matching diagnostic (effective
control-pool size), since matching on too many variables shrinks the pool and can
match away the signal being sought.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_matched_controls(setups: pd.DataFrame, pool: pd.DataFrame, match_cols: list[str],
                           *, n_per_setup: int = 1, seed: int = 0,
                           exclude_same_ticker: bool = True) -> tuple[pd.DataFrame, dict]:
    """Match each setup to controls sharing identical `match_cols` values.

    Returns (controls_df, diagnostic). controls_df carries `matched_setup_id` (the
    setup's DataFrame index) and the matched bucket columns. The diagnostic reports
    the mean effective pool size and how many setups had an empty pool — the
    over-matching safeguard.
    """
    rng = np.random.default_rng(seed)
    groups = pool.groupby(match_cols, sort=False).indices  # bucket-key -> positional indices
    out, eff_sizes, empty = [], [], 0

    for sid, srow in setups.iterrows():
        key = tuple(srow[c] for c in match_cols)
        key = key if len(match_cols) > 1 else key[0]
        idxs = np.asarray(groups.get(key, np.array([], dtype=int)))
        if exclude_same_ticker and "ticker_id" in pool.columns and len(idxs):
            idxs = idxs[pool["ticker_id"].to_numpy()[idxs] != srow.get("ticker_id")]
        eff_sizes.append(len(idxs))
        if len(idxs) == 0:
            empty += 1
            continue
        chosen = rng.choice(idxs, size=min(n_per_setup, len(idxs)), replace=False)
        for c in chosen:
            rec = pool.iloc[c].to_dict()
            rec["matched_setup_id"] = sid
            out.append(rec)

    controls = pd.DataFrame(out)
    diag = {
        "mean_effective_pool": float(np.mean(eff_sizes)) if eff_sizes else 0.0,
        "min_effective_pool": int(np.min(eff_sizes)) if eff_sizes else 0,
        "n_setups_with_empty_pool": empty,
        "n_match_cols": len(match_cols),
    }
    # DELISTED-SHARE diagnostic (review M-5 / GICS pre-commit): survivor-tilted controls are the
    # silent killer — dead names with NULL/stale sector classification fall out of sector-matched
    # pools, so a case-vs-control contrast partially measures survivorship. Surface the share so
    # it's visible. Requires an `is_delisted` column on both frames; fail loudly if absent when
    # a classification (sector/industry) column is being matched on.
    matches_classification = any(c in ("sector", "industry", "gics", "gics_name") for c in match_cols)
    if "is_delisted" in pool.columns and "is_delisted" in setups.columns:
        diag["delisted_share_controls"] = (float(controls["is_delisted"].mean())
                                           if len(controls) and "is_delisted" in controls else float("nan"))
        diag["delisted_share_cases"] = float(setups["is_delisted"].mean())
    elif matches_classification:
        raise ValueError("matched_controls: matching on a classification column requires an "
                         "is_delisted column on both frames to expose survivorship tilt (M-5).")
    return controls, diag
