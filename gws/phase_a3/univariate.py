"""Method 1 — univariate distribution analysis (the screen, Phase A3).

For each feature, compare setups vs controls: test for normality, apply the
appropriate two-sample test (Welch t if normal; Mann-Whitney U for the non-normal
financial norm), report effect sizes (Cohen's d, rank-biserial) and a KS shape
statistic alongside p-values, and apply Benjamini-Hochberg FDR across ALL features
simultaneously. The surviving features are escalated to the expensive methods
(screen-then-deepen).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import shapiro, ttest_ind, mannwhitneyu, ks_2samp

from gws.common.stats import benjamini_hochberg, cohens_d


def _is_normal(x, subsample_n, alpha=0.05, seed=0):
    if len(x) > subsample_n:
        x = np.random.default_rng(seed).choice(x, subsample_n, replace=False)
    if len(x) < 3:
        return False
    try:
        return shapiro(x).pvalue > alpha
    except Exception:
        return False


def _rank_biserial(a, b):
    u, _ = mannwhitneyu(a, b, alternative="two-sided")
    return 1.0 - 2.0 * u / (len(a) * len(b))


def univariate_screen(feature_matrix: pd.DataFrame, labels, *, alpha: float = 0.05,
                      subsample_n: int = 500) -> pd.DataFrame:
    """labels: 1 = setup, 0 = control. Returns one row per feature with the test used,
    raw p-value, BH q-value, significance flag, and effect sizes — sorted by q-value."""
    labels = np.asarray(labels).astype(bool)
    rows = []
    for col in feature_matrix.columns:
        x = feature_matrix[col].to_numpy(float)
        a = x[labels]; a = a[~np.isnan(a)]
        b = x[~labels]; b = b[~np.isnan(b)]
        if len(a) < 3 or len(b) < 3:
            rows.append({"feature": col, "n_setup": len(a), "n_control": len(b),
                         "test": None, "pvalue": np.nan, "cohens_d": np.nan,
                         "rank_biserial": np.nan, "ks_stat": np.nan})
            continue
        if _is_normal(a, subsample_n) and _is_normal(b, subsample_n):
            _, p = ttest_ind(a, b, equal_var=False); test = "welch_t"
        else:
            _, p = mannwhitneyu(a, b, alternative="two-sided"); test = "mann_whitney"
        rows.append({"feature": col, "n_setup": len(a), "n_control": len(b),
                     "test": test, "pvalue": float(p), "cohens_d": cohens_d(a, b),
                     "rank_biserial": float(_rank_biserial(a, b)),
                     "ks_stat": float(ks_2samp(a, b).statistic)})
    df = pd.DataFrame(rows)
    rejected, q = benjamini_hochberg(df["pvalue"].to_numpy(), alpha)
    df["qvalue"] = q
    df["significant"] = rejected
    return df.sort_values("qvalue", na_position="last").reset_index(drop=True)
