# Phase A1 pre-commit — significance, K, and cluster targets are TRAIN-ONLY / EXPANDING

**Committed 2026-07-03 (review CF-3, four-auditor pass).** Any statistic that participates in
a *label* or *target* definition must be knowable at the labeled point's own decision time. A
statistic computed over the full 1950–2025 population leaks the future move distribution into
every training fold, upstream of the walk-forward split where purging cannot reach it. This
document freezes how the three such statistics are computed; the [FORWARD] writers must use it.

## 1. `magnitude_pctile` (move significance = the positive-class definition)
- **Never** the percentile within the full population.
- Assign via `gws.phase_a1.significance`:
  - **`expanding`** (default) — rank each move against all moves *resolved on/before its own
    peak/decision date*. PIT-invariant to later moves (unit-tested).
  - **`frozen_train`** — rank against the magnitude ECDF of the pilot / first training block,
    frozen and applied study-wide, when a single stable threshold is wanted.
- The chosen mode is stamped into `gws.moves.pctile_basis` (`'expanding'` | `'frozen_train:<date>'`);
  the value `'full_sample'` is unrepresentable by construction.

## 2. `K` (forward label window)
- Fit the feature-decay curve that motivates K on the **early training block only** (or expanding),
  never on the full history. K is then held fixed; its ±sensitivity is a B2 robustness label, not a
  co-equal discovery axis (master §11 marginal-sensitivity discipline).

## 3. Cluster-derived score targets
- Move clusters are **descriptive / secondary** (master §4). A cluster id is **not** a walk-forward
  score target unless the clustering is **refit per fold** on train-only data. A single all-history
  clustering used as a forward target is the same full-sample leak as (1).

## Gate check
Before Gate 0.5, the significance writer runs the PIT-invariance assertion
(`tests/test_significance.py::test_expanding_pctile_is_invariant_to_future_moves` generalized to the
real move frame): early-block percentiles must be byte-identical with vs without later data present.
