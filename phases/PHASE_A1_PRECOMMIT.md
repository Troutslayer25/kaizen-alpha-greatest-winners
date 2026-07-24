# Phase A1 pre-commit — significance, K, and cluster targets are TRAIN-ONLY / EXPANDING

**Committed 2026-07-03 (review CF-3, four-auditor pass).** Any statistic that participates in
a *label* or *target* definition must be knowable at the labeled point's own decision time. A
statistic computed over the full 1950–2025 population leaks the future move distribution into
every training fold, upstream of the walk-forward split where purging cannot reach it. This
document freezes how the three such statistics are computed; the [FORWARD] writers must use it.

## 1. `magnitude_pctile` (move significance = the positive-class definition)
- **Never** the percentile within the full population.
- The decision date is the **stop-fire RESOLUTION date** (`resolved_date` / `MoveMFE.resolved_idx`),
  NOT `peak_date` (review C-2): magnitude and the peak's finality are unknowable until the trailing
  stop fires, and keying on `peak_date` lets a then-open peer's later peak mutate an early move's
  comparison set across a fold boundary. **Open (unresolved) moves get NaN and never rank or are ranked.**
- Assign via `gws.phase_a1.significance`:
  - **`expanding`** (default) — rank each move against all moves *resolved on/before its own
    resolution date*. PIT-invariant to later moves and to future bars (unit-tested).
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

---

## ADDENDUM — 2026-07-24, post Gate 0→A1 four-auditor review (Scott approved all four synthesis items; `phases/gate0_a1_review/`)

**Operative gate state:** Gate 0.5 cell amended to **A-provisional / B-live**. The
universal-discovery reading is held in abeyance until the T2 settling package clears.

**Pins (outcome-independent rationales, fixed before any settling result exists):**
- **Primary scale = `trail_6`** — the middle of the pre-committed scale triplet (2/6/15);
  rationale is positional, not performance-based. The anchor experiment MUST report
  scale-invariance of its conclusions across trail_2/6/15 as a robustness label.
- **Headline analytical frame = the forward `setup_labels` (deployment) frame.** The
  trough-anchored case-control frame remains a diagnostic view only; no headline claim may
  rest on it (review T1/F-B: it is maximally exposed to the anchor).

**Settling package (T2 — runs FIRST in A1; bars pre-committed):**
- **B-anchor-1 (de-leak):** on the forward frame, the within-ticker label-shift control
  (k=5) must fall INSIDE the shuffle-null band while the real score stays materially above
  it. Fail → premise-level review (Cell C), per ka-premise.
- **B-anchor-2 (differential):** the frozen `PHASE_A3_TRANSFER_PRECOMMIT` instrument
  (`gws/regime/transfer_test.py`: symmetric era-relative normalization, transfer ratio,
  ≥3 ordered era pairs, `invariance_supported` majority rule), on the forward frame, with
  the anchor variables (location family: dist_from_high/dist_from_low/range_position)
  REMOVED from the structural arm. Not supported → operative cell is B.
- Era bins (pre-committed here): pre-1990 / 1990-1999 / 2000-2009 / 2010-2021 → 12 ordered
  pairs.
- **B-anchor-3 (point-of-strength)** follows as the anchor experiment's second half:
  breakout/consolidation-exit-anchored labels vs trough-anchored, scored on forward MFE/MAE
  with lead time at a point of strength (Method 8 machinery) — spec'd in its own pre-commit
  before it runs.

**Statistical hygiene (binding for all A1 claims):** two-way ticker×date clustered SEs (or
date-block bootstrap) for univariate claims; significance counts reported on
stratified/clean-universe rows only; transfer agreement metrics computed at CONCEPT level
(one representative per lookback ladder) with a permutation reference; the negative-control
`passes=false` from Gate 0.5 is carried as an OPEN flag until B-anchor-1 rules on it.

**Clustering protocol (full universe):** n-scaled `min_cluster_size = max(50, 0.005·n)`;
m-out-of-n stability (`subsample_frac`, fixed m ≈ 50k, many replicates) reporting the
DISTRIBUTION of ARI and cluster count; tie-break computed on a common coverage subset (or
noise assigned to nearest cluster); noise share > 20% forces the continuous representation;
the pilot taxonomy is treated as CONTINUOUS.

**Engineering gates before any full-universe run (review T3; correctness items landed
2026-07-24 — reset_derived + children guard, detection_series_hash composition guard,
strat-empty hard-fail, --run-id):** parallelize the per-ticker passes (detect-once/reuse,
loading persisted cleaned series instead of re-detecting); process fan-out +
`subsample_frac` for the clustering bootstrap; temp-table `UPDATE … FROM` for significance;
`move_clusters` PK → (cluster_id, input_dimensions); close or document the delisted
FMP-crosswalk gap (PIT F1); confirm detection scope (ever-eligible vs all-equity) before
locking the runtime budget.
