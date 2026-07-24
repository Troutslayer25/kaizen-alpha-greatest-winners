# Cell C Work Package (W1–W5) — Pre-Committed Specification

**Scott signed W1–W5 in-session 2026-07-24** (log entry same date). Per the integrity
ruling's discipline: this spec is committed BEFORE any of it runs; the original B-anchor-1
FAIL remains on the record untouched; the synthetic defect-proof (calib_*.py in
gate0_a1_review/) is the attached justification for W1's re-scoping. Frame: forward
`setup_labels`, stratified pilot names, seed 20260719 throughout.

## W1 — Re-scoped de-leak (the only admissible follow-up to the FAIL)
- Same control, same k: `shift_labels_within_ticker(k=5)`; same shuffle band.
- Feature set: **location-residualized** — every column with `family_of == "location"`
  dropped; nothing else changes.
- Rows sorted by (ticker_id, as_of_index) and asserted (premise ruling's ORDER BY find).
- **PASS iff shifted AUC ≤ shuffle_hi (+1e-9) while real (residualized) AUC > shuffle_hi
  + 0.05.** PASS → a leak-free non-anchored forward edge exists. FAIL → the forward edge
  is irreducibly anchor-driven on this frame; premise falls to W5 alone.

## W2 — Lead-time-restricted genuine-signal estimate (load-bearing)
- Positives: `setup_labels` label=1 with `lead_time_days ∈ [5, 20]`.
- Negatives: label=0 AND ≥60 bars from ANY trail_6 trough in EITHER direction (via
  gws.moves join + the hash-guarded date vectors; setup_labels-only negatives are
  contaminated per the quant ruling).
- Metric: pooled AUC on the **location-residualized** set (primary; full set reported as
  diagnostic), vs two references: the 0.577 era-composition floor and a
  **run-length-preserving null band** = per-ticker cyclic label rotation by a random
  offset ≥12 sample positions (=60 bars), 50 replicates, 95% band.
- Offset collapse: same points re-scored with features measured at T-21 and T-63 bars.
- **Pre-committed reading: AUC_res ≤ max(0.577, null_hi) → premise AGAINST on this frame;
  (max floor, 0.63] → life support; > 0.63 AND > null_hi → premise ALIVE pending W5.**

## W3 — Dimension-fair invariance rematch
- Concept collapse: one representative per lookback ladder — the 63-lookback variant,
  else the longest available (fixed, outcome-independent rule).
- Arms: emotional concepts vs structural concepts; **primary = structural WITHOUT
  location** (consistent with W1); with-location reported as a labeled robustness line.
  Contested assignments (ma_compression, price_to_ma) flagged in output, not re-mapped.
- Balance: emotional subsampled to the structural arm's concept count, 20 seeds →
  distribution of `invariance_supported` outcomes and median-ratio gaps; frozen A3
  instrument (12 era pairs) throughout.
- Reading: SUPPORTED in a majority of balanced subsamples → thesis revives; else it stays
  demoted (open, unsupported).

## W4 — Compliance
- Explicit `< 2022-01-01` era cap in the settling/workpackage runners (no reliance on
  upstream lockbox truncation) + assert max(setup_labels.date) < 2022-01-01.
- **Scale-invariance label:** W2 repeated with trail_2 and trail_15 trough catalogs
  (labels re-derived in-memory from gws.moves per scale) — the missing pre-committed
  deliverable. Conclusions must agree in direction across scales or the disagreement is
  reported as a limitation, not resolved post hoc.

## W5 — B-anchor-3 point-of-strength pre-commit (spec'd separately before it runs)
Per the premise ruling §3: consolidation-exit anchor (exact rule frozen), forward
MFE-vs-ATR-trail primary label, **configuration-matched FAILED breakouts as negatives**,
features strictly at/before the breakout bar, W1/W2-class controls, trail_2/6/15
robustness. THE continue-vs-stop gate. Its parameter freeze gets its own document
(`phases/B_ANCHOR3_PRECOMMIT.md`) and Scott sign-off before implementation.

*No result below alters this spec after the fact; deviations get dated addenda.*

---

## AMENDMENT 2026-07-24 (Scott, in-session) — intent correction: no bottom-prediction bar

Scott clarified the study's intent verbatim-in-substance: identify meaningful moves
(≥20%-class, no meaningful correction, ATR-defined — i.e., the existing detector),
classify by size/momentum/amplitude (the existing clustering dims), then REWIND to ask
whether characteristics preceded the move's beginning. Predicting troughs from arbitrary
days was never the intent; W2's trough-prediction kill-bar is WITHDRAWN as a premise test.

**W2′ — REWIND analysis (replaces W2 as the discovery-frame test):**
- Cases = resolved trail_6 moves (stratified names); controls = the persisted MINIMAL
  matched controls (same-date, different ticker — calendar composition neutralized by
  construction).
- Features measured at T-0 (reference only; known anchor-contaminated), **T-5, T-21,
  T-63 bars BEFORE** the case trough / control date; points needing <252 bars history drop.
- Primary metric: pooled AUC on the **location-residualized** feature set per offset;
  full-set AUC and top-10 ticker-clustered univariate reported per offset.
- **Pre-committed reading:** the move was "visible being born" iff AUC_res(T-21) >
  shuffle_hi + 0.05, with the T-5→T-63 decay profile reported as-is. No single-offset
  cherry-pick: all four offsets publish together.
- W1 unchanged (runs as spec'd). W3 deferred to the corrected frame. **W5 / B-anchor-3
  (point-of-strength) is promoted to the study's load-bearing tradeability gate** — the
  rewind answers "visible at birth?"; the pivot test answers "visible where Scott buys?".
