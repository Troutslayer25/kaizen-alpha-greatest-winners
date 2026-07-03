"""Wide feature-matrix builder (Phase A2).

Turns a set of observation points (ticker_id, as_of_index) into a wide numeric matrix
by calling the (ticker_id, as_of_date)-keyed feature functions once per point. This is
the ML-consumable materialization referenced in blueprint T3; the long per-value store
remains the audit/lineage record. Because every point goes through the same feature
calls, extraction is identical for setups, controls, and sampled points by construction.

The matrix includes BOTH the Branch-1 price/volume features AND the generic/auto feature
bank by default (`include_generic=True`). Wiring the generic bank in is a bias control,
not an optimization: practitioner-recognizable features must compete against
framework-neutral descriptors, or the Gate A3->A4 motivation cross-tab is trivially
all-practitioner (KA_AUDITOR_PROMPTS Auditor 4 §28).

SCALE (review, compute aspect). The old builder iterated points one at a time on a single
thread — the pipeline's real wall at 1e7 sample points on a 64-thread box. This version groups
points BY TICKER and computes each ticker independently, so the work fans out across a process
pool (`n_jobs`), and emits float32 by default (halves the ~44 GB in-RAM matrix). The feature
FUNCTIONS are unchanged, so results are numerically identical to the serial build (regression-
tested) — the parallelism is in the driver only.
FURTHER WORK (documented tradeoff, deliberately deferred): computing each feature as a per-ticker
VECTORIZED rolling array once and indexing the sample points would remove the per-point recompute
(another ~10-25x), but every feature's vectorized form must be proven bit-equal to the windowed
one first (silently-different features are the exact bug class the study guards against). That
rewrite is gated on a numeric-equality harness; on a 256 GB box the float32 matrix fits, so it is
an optimization, not a blocker.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from gws.phase_a2.features_price_volume import compute_features, DEFAULT_LOOKBACKS
from gws.phase_a2.generic_features import compute_generic_features


def _features_for_ticker(args):
    """Compute features for all sample points of ONE ticker (a picklable worker)."""
    labels, idxs, series, bench, lookbacks, include_generic, use_vec = args
    vec, exclude = None, frozenset()
    if use_vec:
        from gws.phase_a2.features_vectorized import VECTORIZED_FIELDS, compute_features_vectorized
        vec = compute_features_vectorized(series["close"], lookbacks=lookbacks)
        exclude = set(VECTORIZED_FIELDS)                  # families served from the vectorized arrays
    out = []
    for lab, i in zip(labels, idxs):
        feats = compute_features(series["close"], series["high"], series["low"],
                                 series["volume"], i, bench_close=bench, lookbacks=lookbacks,
                                 exclude=exclude)
        if include_generic:
            feats = {**feats, **compute_generic_features(
                series["close"], series["high"], series["low"], series["volume"], i)}
        if vec is not None:
            for key, arr in vec.items():                  # merge vectorized families (finite == present)
                v = arr[i]
                if np.isfinite(v):
                    feats[key] = float(v)
        out.append((lab, feats))
    return out


def build_feature_matrix(points: pd.DataFrame, series_by_ticker: dict, *,
                         bench_by_ticker: dict | None = None,
                         lookbacks=DEFAULT_LOOKBACKS,
                         include_generic: bool = True,
                         n_jobs: int = 1, dtype=np.float32, vectorized: bool = False) -> pd.DataFrame:
    """Compute features for each (ticker_id, as_of_index) point.

    `series_by_ticker[tk]` is a dict with 'close','high','low','volume' arrays.
    Returns a DataFrame aligned 1:1 with `points` (same index), one column per feature.
    Includes the generic/auto bank unless `include_generic=False`.

    `n_jobs` > 1 (or -1 for all cores) fans the per-ticker work out across a process pool;
    the result is identical to the serial build. `dtype` controls the output precision
    (float32 by default to halve memory at full-universe scale)."""
    # Duplicate index labels would collapse the label->features dict and silently assign one
    # ticker's features to another's rows (the natural pd.concat(setups, controls) shape produces
    # duplicate RangeIndex labels) — plausible-garbage ML input, the study's nightmare class
    # (review M2). Fail closed.
    if not points.index.is_unique:
        raise ValueError("build_feature_matrix: points.index must be unique — duplicate labels "
                         "would mis-assign features across rows; reset_index(drop=True) first")
    # group point positions by ticker (preserving each point's original index label)
    by_ticker: dict = {}
    for lab, tk, idx in zip(points.index, points["ticker_id"], points["as_of_index"]):
        by_ticker.setdefault(tk, ([], [])) [0].append(lab)
        by_ticker[tk][1].append(int(idx))

    tasks = []
    for tk, (labels, idxs) in by_ticker.items():
        bench = bench_by_ticker.get(tk) if bench_by_ticker else None
        tasks.append((labels, idxs, series_by_ticker[tk], bench, lookbacks, include_generic,
                      vectorized))

    if n_jobs == 1 or len(tasks) <= 1:
        results = [_features_for_ticker(t) for t in tasks]
    else:
        workers = None if n_jobs in (-1, 0) else n_jobs
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(_features_for_ticker, tasks))

    feats_by_label = {lab: feats for chunk in results for lab, feats in chunk}
    recs = [feats_by_label[lab] for lab in points.index]
    df = pd.DataFrame(recs, index=points.index)
    # Standing quarantine at the choke point (review M-4): no move-outcome column may enter the
    # feature matrix. A leaked descriptor here would be trained on the move's own future.
    from gws.validation.quarantine import assert_no_outcome_leak
    assert_no_outcome_leak(df.columns)
    return df.astype(dtype) if dtype is not None else df
