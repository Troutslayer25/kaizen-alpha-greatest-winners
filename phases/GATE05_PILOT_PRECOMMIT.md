# Gate 0.5 — Real-Data Pilot: Pre-Committed Specification

**Phase:** Gate 0.5 (hard gate) — real-data pilot sanity run
**Position in sequence:** after Phase-0 outputs exist (`gws.index_membership`, `gws.universe_eligibility`, completeness audit, QC sweep), **before** the Gate 0→A1 four-auditor review clears and before ANY full-universe compute.
**Submitted by:** Implementation agent
**Status:** PRE-COMMITMENT — committed to GitHub before any pilot implementation or pilot data query.

> ⚠️ GitHub commit timestamp = proof of pre-commitment. All pilot implementation
> commits and all pilot data queries must post-date this commit. Auditors verify.

---

## Revision History

| Rev | Date | Change |
|---|---|---|
| v1 | 2026-07-19 | Original pre-commitment. Drafted on KA-Workstation during the Phase-B migration window (DB is the freshly-migrated local copy; no GWS analytical queries run — see disclosure). |

---

## Pre-Spec Exploration Disclosure (mandatory)

- ☑ Repo docs read: `KA_GREATEST_WINNERS_MASTER.md` (gates, §12 early experiments, snowball register), `phases/PHASE0_PRECOMMIT.md` (template + Phase-0 bindings), project memory.
- ☑ Infrastructure parity checks were run on the workstation DB during the Phase-B cutover (G4/G5: row counts on `public.*` tables, golden RS spot-checks, `gws` schema presence). These are migration-integrity checks on non-GWS outputs, not analytical exploration.
- ☑ **No queries against `gws.*` analytical tables, no move detection, no feature computation, no return/outcome examination of any kind has been run.**
- ☑ Sealed-hypothesis plaintexts under `research/hypotheses/` remain unread (blinding directive M-6 honored).
- ☑ Feature net remains FROZEN (2026-06-21); nothing here expands it.

---

## Purpose (two jobs, in priority order)

1. **Break the pipeline cheap.** Surface the silent-failure classes from the snowball register (#3 membership accuracy, #4 phantom moves, #6 available_date, #9 inflated N) on 300 tickers instead of after a multi-day full-universe run.
2. **Produce the Gate 0.5 exit evidence:** the §12.1 transfer/stationarity experiment on pilot scale, feeding the signed go/no-go memo answering *"Is the study learning a transferable winner setup, or merely rediscovering regime-specific historical artifacts?"*

The pilot does NOT tune parameters, does NOT expand the feature net, and its
analytical outputs are NOT findings — they are evidence about pipeline health and
transfer viability only.

---

## Pre-Committed Pilot Universe (N = 300)

Selection is by **structural criteria only** — selection queries may touch dates,
flags, index membership, delisting status, split/QC metadata; they may NEVER touch
prices, returns, volumes-as-signal, or move outcomes.

- **250 stratified random** from tickers ever eligible in `gws.universe_eligibility`.
  Strata (proportional allocation, remainder to largest stratum):
  - era of first eligibility: pre-1990 / 1990–2009 / 2010–present
  - status: active / delisted
  - index family at first eligibility: S&P 500 / S&P 400+600 / Russell-only
  - RNG seed: **20260719** (fixed here; changing it post-hoc is a violation)
- **50 adversarial, chosen by structural CLASS, never by outcome:**
  - ≥10 delisted via bankruptcy/liquidation
  - ≥10 with a reverse split in `corporate_actions` / Norgate metadata
  - ≥10 symbol-reuse or relist cases (Norgate assetid ≠ unique per symbol)
  - ≥10 first_quoted_date before 1980 (deep-history stress)
  - ≥5 tickers carrying `gws.data_quality_exceptions` flags (QC-machinery stress)
- The selection script + resulting ticker list are committed BEFORE any pilot
  compute runs on them.

## Pre-Committed Pilot Scope (what runs, in order)

All parameters at their pre-committed defaults from the A1 pre-commit / method
library. **No parameter changes during the pilot** — a capability gap or a
suspected-wrong default gets LOGGED to the backlog, not fixed-and-rerun, unless the
pipeline is actually broken (Decision D below).

1. MFE move detector (canonical) + ATR-swing cross-check; exclusion-consuming driver.
2. Move catalog persistence (`gws.moves`) + idempotent re-run proof.
3. Clustering (magnitude / duration / uncensored smoothness) + stability check.
4. Labeling + matched controls: minimal construction primary; ONE robustness
   construction (liquidity-matched) as a marginal sensitivity — not the full §12.5 set.
5. Feature matrix on the frozen net; univariate pass with ticker-clustered inference.
6. Negative-control harness (learned null bands) + PIT harness.
7. **§12.1 transfer/stationarity experiment** (below).
8. Runtime accounting for full-universe projection.

## Pre-Committed Transfer Experiment (§12.1)

- **Primary split:** train = moves with inception `< 2010-01-01`; test = `>= 2010-01-01`.
  (Pilot strata guarantee both sides are populated; deep history is load-bearing.)
- **Robustness label (one axis):** the same run with a 2000-01-01 split. Reported
  alongside, never substituted if the primary disappoints.
- Run separately for **emotional/behavioral** vs **structural** feature families —
  this is the invariance instrument (central testable hypothesis).
- **Pre-committed evidence metrics:** (a) sign agreement of univariate effect
  directions train→test; (b) rank correlation (Spearman) of effect sizes train→test;
  (c) OOS AUC of a simple pooled model scored on the test window vs within-window
  baseline. All with ticker-clustered inference; no new metrics added after results
  are seen.
- **Pre-committed reading bands:** FOR transfer = majority sign agreement + positive
  rank correlation materially above the negative-control null band, in BOTH families;
  MIXED = holds for emotional/behavioral but not structural (per-thesis expectation)
  or holds only on one split; AGAINST = neither family separates from the null band.
  The bands are deliberately qualitative at pilot N — the memo argues from them, it
  does not invent thresholds post hoc.

## Pre-Committed Break-the-Pipeline Checklist (all must pass)

- End-to-end completes on all 300 tickers including every adversarial class.
- Idempotent re-run: identical move-catalog counts and IDs.
- Every stage logs row counts; all within pre-stated order-of-magnitude ranges;
  zero silent-empty stages.
- PIT harness green; `CHECK (available_date <= as_of_date)` violations = 0.
- Negative controls produce null bands; no planted-signal leakage.
- No detected move spans zero-volume/stale-print/excluded bars (anti-pollution rule).
- Full-universe projection: pilot runtime × (universe/pilot) < **7 days** wall-clock
  on this workstation; if projected over, escalate before any full run.

## Decision Matrix (memo cells — Scott signs; the agent never self-certifies)

| Cell | Condition | Pre-committed recommendation |
|---|---|---|
| A | checklist green + transfer FOR | Universal discovery viable → proceed to Gate 0→A1 review |
| B | checklist green + transfer MIXED | Regime-conditional discovery becomes PRIMARY (per `research/regime_conditional_discovery.md`); universal model demoted to robustness |
| C | checklist green + transfer AGAINST | HALT for premise-level review (ka-premise + four auditors) before any further compute |
| D | checklist failed | Fix the pipeline, re-run the pilot; no memo, no gate progress until green |

**Exit artifact:** written go/no-go memo (`phases/GATE05_EXIT_MEMO.md`) stating which
cell fired, the evidence, and the §12.1 outputs — signed by Scott before any
full-universe compute. This is a POLICY gate; workstation capacity does not waive it.

---

## Risks and Open Questions Going In

- Pilot N=300 is powered for pipeline-breaking and directional transfer evidence,
  not for significance claims — the memo must not overclaim.
- Stratified sampling depends on `universe_eligibility` being correct (snowball #3);
  the Phase-0 verifier + PIT spot-checks run first and gate the pilot start.
- The adversarial 50 deliberately over-weight pathology; they are excluded from the
  transfer-metric computation (pipeline-stress only) to avoid biasing the evidence.
- Penny-floor level ($1 provisional) still awaits Scott's confirmation from the
  Phase-0 pre-commit; the pilot inherits whatever Phase 0 ships.

---

*Pre-committed by the implementation agent for Scott Oman review and auditor
verification at Gate 0.5. No pilot implementation or pilot data query has run as of
this commit.*
