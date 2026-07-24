# Gate 0→A1 Four-Auditor Review — Auditor-4 First-Pass Synthesis

**Date:** 2026-07-24. **Panel:** ka-premise, ka-research-integrity, ka-pit-auditor, ka-quant,
ka-integration (ka-economic-mechanism benched until A3→A4 per its charter). Full verbatim
reports in this directory. **This synthesis is the Claude first-pass; Scott's human review is
mandatory (V11). All findings are opinions; Scott approves every change.**

## Verdict sheet

| Auditor | Verdict | Core finding |
|---|---|---|
| ka-premise | **HALT** | F1/F2/transfer-FOR are one artifact seen three times (structural family *contains* the anchor variables); pre-committed matrix maps the coded `passes:false` to Cell D, not A; the de-confounded `gws/regime/transfer_test.py` instrument was never invoked |
| ka-research-integrity | CLEAR-WITH-CONDITIONS | Pre-commitment ordering VERIFIED from git; both Decision-D fixes genuine (no tunable knob); but "checklist green" not literally met — Cell A is functionally a soft B until the anchor experiment clears; discovery-frame choice was an unlogged fork |
| ka-pit-auditor | CLEAR-WITH-CONDITIONS (LOW only) | **Data path verified PIT-clean and survivorship-free in code AND persisted data** — lockbox holds, membership closures historically exact, features strictly trailing, no survivor tilt. Conditions: delisted FMP-crosswalk gap documented; lockbox-boundary label censoring noted |
| ka-quant | CLEAR-WITH-CONDITIONS | Frozen `PHASE_A3_TRANSFER_PRECOMMIT` (ratio, ≥3 era pairs, emotional>structural majority) points to **B, not A**; ticker-only clustering leaves date dependence unmodeled (80/92 soft, top tier survives); transfer ρ≈0.95 near-mechanical (effective N ≈ concepts, not features); cluster tie-break biased toward discrete |
| ka-integration | **HALT** | **C1 proven live:** re-detection is FK-blocked by controls/labels children, exception swallowed per-ticker → silently stale catalog **with a passing fingerprint**; M1: three serial per-ticker passes + serial 102-fit clustering bootstrap → full run ≈25–30 h as-coded, not the projected 1–2 h; M2: pilot `kind`/`RUN_ID` couplings would silently empty step 6–7 on the full universe |

## Convergent findings (what multiple auditors independently hit)

**T1 — The Cell A label is stronger than the evidence (premise + integrity + quant).**
The coded negative-control verdict is `passes=false`; the frozen A3 transfer instrument
(ratio, ≥3 pairs, emotional>structural majority) was not the one run, and under it the
honest cell is B; the headline evidence ran on the frame maximally exposed to the anchor
while the cleaner forward-labeled `setup_labels` frame sat unused. Nobody alleges fraud —
integrity verified the timestamps and the honest reporting — but the three science
auditors agree the operative reading must be **downgraded from signed-A to
"A-provisional / B-live"** (or formally reopened) until the settling experiments run.

**T2 — One settling experiment package, converged on independently by all three:**
(a) re-run §12.1 transfer + the negative-control harness on the **forward-labeled
`setup_labels` frame** (features at the sampled point, label = future trough): the
within-ticker shift control must fall inside the shuffle band; (b) run the **frozen A3
instrument as written** (transfer ratio, ≥3 ordered era pairs, symmetric normalization,
emotional>structural majority) with anchor variables (`dist_from_low`/`dist_from_high`/
`range_position`) removed or residualized from the structural arm; (c) this IS the
mandated anchor experiment's first half — it uses data that already exists (~1 day).
Premise's falsifiable bar: if the shift control does not collapse to ~chance on the
forward frame, the premise question reopens (Cell C review).

**T3 — Engineering blockers before ANY A1 compute (integration, proven live):**
C1 FK-deadlock/silent-stale-catalog (children must tear down before re-detect; `n_err>0`
must refuse to pass), detect-once/reuse with a persisted per-ticker date-vector hash
(closes M3 drift), parallelize the per-ticker passes + clustering bootstrap
(`subsample_frac` + process fan-out), parameterize `RUN_ID`/universe-source/adversarial
semantics, temp-table significance UPDATE. Corrected honest runtime estimate as-coded:
25–30 h; ~2–3 h after fixes.

**T4 — The data foundation is sound (PIT).** Nothing at the data layer needs rebuilding;
A1 may build on the pilot's data path. The panel's problems are in the *reading* and the
*orchestration seams*, not the spine.

**T5 — Statistical hygiene for the A1 pre-commit (quant):** two-way ticker×date clustered
inference; report univariate counts stratified-only; effective-N-honest transfer metrics
(one representative per concept); n-scaled `min_cluster_size`, m-out-of-n stability with
distributions, coverage-penalized tie-break, noise-share override to continuous; treat the
pilot taxonomy as continuous.

## Auditor-4 first-pass recommendation (Scott decides every item)

1. **Reopen the Gate 0.5 cell determination.** Recommended amendment: **"A-provisional /
   B-live"** — universal-discovery held in abeyance; regime-conditional treated as live
   co-primary — pending T2. (Premise argues strict D/C; integrity+quant argue this
   downgrade suffices given the mandates Scott already bound. The strict-reading minority
   position is preserved in the premise report.)
2. **Approve the T3 engineering fixes** (pure correctness/orchestration; no science
   parameters touched) before any further gws compute.
3. **Approve the T2 settling package** as the FIRST A1 act (it is the mandated anchor
   experiment, sharpened by the panel into pass/fail bars).
4. **Fold T5 into the A1 pre-commit**, plus integrity's list: pin primary scale and
   frame choice with outcome-independent rationale or show scale-invariance; carry
   `passes=false` as an open flag; exercise the fundamentals/PIT branch; preserve pre/post
   artifacts on any post-peek fix.
5. Log the review; Gate 0→A1 is **NOT cleared** until Scott rules on 1–4.

*Panel disposition: 2 HALT / 3 CLEAR-WITH-CONDITIONS → under V11 the gate does not clear
on this pass. Nothing in the panel requires discarding pilot work; every remediation reuses
existing data and modules.*
