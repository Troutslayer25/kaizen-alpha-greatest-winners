"""Negative-control harness — the mirror of the synthetic oracle.

The oracle asks "does the pipeline find the signal we PLANTED?" Negative controls ask the
complementary question: "does the pipeline correctly find NOTHING in deliberately useless
data?" If a model scores above chance on shuffled/misaligned inputs, something is leaking or
overfitting — caught before the expensive real run.

Recalibrated per review M-5:
  * The misalignment probe shifts labels WITHIN each ticker (`shift_labels_within_ticker`), not
    across the whole panel. A global np.roll on a (ticker,date)-sorted panel splices ticker A's
    labels onto ticker B and guarantees ~chance for almost anything — a weak probe. Shifting
    within ticker keeps a pipeline whose "edge" is slow-feature x slow-label autocorrelation
    scoring above chance, which is exactly the pathology worth catching.
  * "Chance" is LEARNED, not assumed. A fixed +/-0.05 margin is N-blind (too tight at full N,
    too loose at pilot N). We build a permutation-null band from repeated label shuffles and
    judge every probe against that band.
  * Verdicts are split: `leak_free` (destroyed-data scores sit at the learned chance band) is
    separate from `has_signal` (real beats the band). In a discovery-first study a true null is
    a valid outcome, not a harness failure.
  * permute-within-date is a DECOMPOSITION baseline (timing/base-rate vs cross-sectional), not a
    pass/fail gate — date-level context features are invariant under within-date permutation and
    would false-trip a fixed margin.

All corruptions are deterministic under `seed`.
"""
from __future__ import annotations

import numpy as np


def shuffle_labels(y, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.permutation(np.asarray(y))


def permute_features_within_date(X, dates, seed: int = 0) -> np.ndarray:
    """Permute feature ROWS within each date group. Preserves each day's cross-sectional
    feature distribution but destroys the row-to-label correspondence."""
    X = np.asarray(X, float)
    dates = np.asarray(dates)
    rng = np.random.default_rng(seed)
    out = X.copy()
    for d in np.unique(dates):
        idx = np.where(dates == d)[0]
        out[idx] = X[rng.permutation(idx)]
    return out


def shift_labels_within_ticker(y, tickers, k: int = 5) -> np.ndarray:
    """Roll labels by `k` positions WITHIN each ticker (temporal misalignment that stays inside
    a ticker's own history). Catches an 'edge' that is really slow-feature x slow-label
    autocorrelation — the misalignment a cross-ticker roll cannot probe."""
    y = np.asarray(y)
    tickers = np.asarray(tickers)
    out = y.copy()
    for g in np.unique(tickers):
        idx = np.where(tickers == g)[0]
        out[idx] = np.roll(y[idx], k)
    return out


def gaussian_noise_feature(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0, 1, n)


def _band(scores, ci: float = 0.95) -> dict:
    s = np.asarray(scores, float)
    lo = float(np.quantile(s, (1 - ci) / 2))
    hi = float(np.quantile(s, 1 - (1 - ci) / 2))
    return {"lo": lo, "hi": hi, "mean": float(s.mean()), "scores": s.tolist()}


def negative_control_report(X, y, t, fit_score_fn, *, tickers=None, seed: int = 0,
                            n_null: int = 50, shift_k: int = 5) -> dict:
    """Run `fit_score_fn(X, y, t) -> score` (e.g. an OOS AUC) on the real data and against
    learned null bands. Returns the real score, a shuffle-null band (the learned 'chance'
    reference), a permute-within-date band (cross-sectional-vs-timing decomposition), and the
    within-ticker misalignment score. Interpret with `negative_control_verdicts`."""
    X = np.asarray(X, float)
    y = np.asarray(y)
    shuffle_scores = [fit_score_fn(X, shuffle_labels(y, seed + i), t) for i in range(n_null)]
    permuted_scores = [fit_score_fn(permute_features_within_date(X, t, seed + i), y, t)
                       for i in range(n_null)]
    shifted = None
    if tickers is not None:
        shifted = float(fit_score_fn(X, shift_labels_within_ticker(y, tickers, shift_k), t))
    return {
        "real": float(fit_score_fn(X, y, t)),
        "shuffle_null": _band(shuffle_scores),
        "permuted_within_date_null": _band(permuted_scores),
        "shifted_within_ticker": shifted,
    }


def negative_control_verdicts(report: dict, *, chance: float = 0.5, tol: float = 0.05) -> dict:
    """Split the report into independent verdicts (M-5):
      leak_free  — destroyed-data scores sit at the learned chance band (no leakage);
      has_signal — the real score beats the shuffle-null band (genuine discrimination);
      cross_sectional_edge — real beats the permute-within-date band (edge is cross-sectional,
                   not merely timing/base-rate).
    `passes` = leak_free AND has_signal. A leak_free pipeline with has_signal False is a valid
    null result, not a failure."""
    sh = report["shuffle_null"]
    leak_free = sh["mean"] <= chance + tol
    if report.get("shifted_within_ticker") is not None:
        leak_free = leak_free and (report["shifted_within_ticker"] <= sh["hi"])
    has_signal = report["real"] > sh["hi"]
    cross_sectional_edge = report["real"] > report["permuted_within_date_null"]["hi"]
    return {"leak_free": bool(leak_free), "has_signal": bool(has_signal),
            "cross_sectional_edge": bool(cross_sectional_edge),
            "passes": bool(leak_free and has_signal)}
