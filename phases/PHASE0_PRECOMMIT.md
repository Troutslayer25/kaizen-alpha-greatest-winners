# Phase 0 — Pre-Committed Specification (Gate 0→A1)

**Phase:** Phase 0 — Universe Construction and Database Completeness Audit
**Gate:** 0→A1
**Submitted by:** Implementation agent
**Status:** PRE-COMMITMENT — committed to GitHub before any Phase-0 implementation begins.

> ⚠️ This document is Part 1 of the Phase-0 planning session. Its GitHub commit
> timestamp is the proof of pre-commitment. Implementation commits for Phase 0 must
> post-date this commit. Auditors verify this at Gate 0→A1.

---

## Revision History

| Rev | Date | Change |
|---|---|---|
| v1 | 2026-06-19 | Original pre-commitment (commit `cb5a449`). Two-layer universe: index membership + empirical ADV liquidity floor + $5 penny floor. |
| v2 | 2026-06-20 | **Removed the institutional ADV liquidity floor from universe construction.** Replaced with a minimal data-*validity* screen; liquidity is now carried as a *feature* for A2/A3 to discover, and tradeability/capacity moves to the deployment/scoring layer. Penny floor reframed as a data-validity threshold. Rationale: an ADV floor is a human-imposed filter on the early data that forecloses discovering whether liquidity governs move success — the same discovery-first error the move-detector floor made one layer down. **This is a pre-implementation design revision; no Phase-0 code has run, so no parameter was tuned to any observed result.** Decided by reasoning (review of an external debate transcript), not by data examination. |

> **Integrity note for Auditor 4:** the v1→v2 change is a *plan* refinement made before any implementation or data examination. The pre-commitment that matters — spec committed before implementation — still holds: the latest spec predates all Phase-0 implementation commits. The change was reasoned, not fit to results.

---

## Pre-Spec Exploration Disclosure (mandatory)

Before writing this specification, the following was examined — disclosed in full for Auditor 4:

- ☑ **Existing KA pipeline code/schema was read** (via read-only exploration of `~/kaizen-alpha`) to plan reuse: `ka_lib` (db/fmp/log), the step/ingest patterns, `eod_prices`/`fundamentals` schemas, the Norgate `ka_history` schema and loaders, and the existing data-quality machinery (`ticker_exclusions`, `data_valid_from`, `instrument_type`, `repair_phantom_zero_adj_close.py`, `ka_history_crosscheck.py`). This is code/schema inspection, **not** examination of analytical data outputs.
- ☑ **DB structural facts known from prior project memory:** historical PIT index-constituent membership does **not** currently exist in the DB (it must be ingested from Norgate); FMP's delisted endpoint is post-2015 only; documented data-quality issues exist (phantom-zero `adjusted_close`, split-explosion, NUMERIC overflow). These are structural facts about *what data exists*, not snooped distributions.
- ☑ **Phase-0/method machinery was pre-built and committed as synthetic-validated tooling.** Note: `gws/phase0/liquidity_floor.py` (knee-of-curve) is no longer a universe gate under v2; it is retained as a generic utility for liquidity-tier bucketing / capacity analysis at the deployment layer.

**No exploratory data queries were run.** Specifically, for the bias-relevant Gate 0→A1 risk points:

> ☑ No real ADV distributions, eligible-universe sizes, or index-membership counts have been examined. The v2 decision to remove the ADV floor was made by reasoning, not by looking at what it would include/exclude.
> ☑ The index set (below) was chosen by neutral pre-commitment — the full institutional-grade spectrum — not selected after observing which names it includes/excludes.

---

## Pre-Committed Decisions

These resolve the Phase-0 open questions and are fixed before implementation:

- **OQ-1a — Index set (quality filter):** the union of all major US indexes — **S&P 500, S&P MidCap 400, S&P SmallCap 600, Russell 1000, Russell 2000, Russell 3000, Nasdaq-100** — sourced from Norgate historical constituent data, applied as a strict PIT daily flag. Rationale: captures the full institutional-grade spectrum (large→small cap) while excluding OTC/pink-sheet/warrant/rights/foreign-cross-listing/stub instruments without manual lists. **Any index Norgate does not cover for a given window is dropped with documented rationale (Step 0 verifies coverage).**
- **OQ-2 — No institutional liquidity floor in universe construction (v2).** The empirical ADV floor is **removed** as an eligibility gate. Filtering the universe on liquidity early forecloses discovering whether liquidity (or the illiquid→liquid transition) is itself part of what precedes a great winner — the same discovery-first error as the move-detector's removed 10% floor. Liquidity's three jobs are split to the layers where each belongs:
  - **Data validity (Layer 2, kept):** a *minimal data-validity screen* — not a liquidity preference. A ticker-date is valid only with non-zero/real volume, an actually-traded price series, and clean data (passes the QC sweep below). Genuinely broken data is excluded because it is *invalid*, not because it is *illiquid*.
  - **Liquidity as a feature (A2/A3):** 50-day ADV, dollar volume, market cap, and nominal price are *recorded* on every observation as features, so Phase A3 can discover whether liquidity governs move success. Not a gate.
  - **Tradeability / capacity (deployment, Phase X/B2):** the "can I trade this at my size" filter is applied at the scoring/deployment layer via the capacity diagnostic (`gws.tradeability_diagnostic`, `capacity_diagnostic`), calibrated to actual trading size — *after* discovery, by conditioning the population, never by re-detecting moves.
- **OQ-1b — Penny floor reframed as data validity (v2):** the $5 nominal-price gate is replaced by a *minimal* price floor (provisional **$1**, PIT daily) whose purpose is to avoid penny-spread artifacts (where a one-cent tick is a large % move and manufactures phantom % moves) — a data-validity reason, not a quality preference. Nominal price is also carried as a feature. *(Penny-floor level to be confirmed by Scott; flagged because it follows the same discovery-first logic as the ADV floor.)*
- **Anti-pollution rule (v2):** because dropping the ADV floor admits the lower-liquidity end of *index members* (not OTC junk — Layer 1 still excludes that), the data-validity screen carries more weight. A detected move must occur over **actually-traded bars** (real volume); moves built on zero-volume/stale-print stretches are rejected. This — not a liquidity floor — is what keeps the detected-move population clean.
- **OQ-9 — Fundamental availability (recorded for Phase A2, audited in Phase 0):** fundamentals are gated on `available_date` = the public filing/release date when reliable, else `period_end + 60-day conservative lag`, with `CHECK (available_date <= as_of_date)`. `period_end` is the quarter identifier only. Phase 0 confirms whether reliable filing/release dates exist in the source.
- **Retention (survivorship protection):** delisted/merged/bankrupt tickers retained through their last active date; zero-volume rows retained as non-trading flags, never deleted.
- **Minimum history:** 252 trading days before a ticker is eligible.

---

## What Phase 0 Will Produce

| Output | Table / artifact |
|---|---|
| Historical PIT index membership | `gws.index_membership` (ticker_id, index_name, from_date, to_date) |
| Eligibility flag (single source of truth) | `gws.universe_eligibility` (ticker_id, date, eligible, index_member, data_valid, above_min_price, adv_50d, dollar_volume_50d) — `eligible = index_member ∧ data_valid ∧ above_min_price ∧ 252-day history`. ADV/dollar-volume are **recorded, not gating**. |
| Recorded liquidity metrics (features, not gates) | `adv_50d`, `dollar_volume_50d`, market cap, nominal price — surfaced to A2/A3 as candidate features |
| Data-quality corrections/exclusions | `gws.data_quality_exceptions` + `ticker_exclusions` entries |
| Completeness-audit outputs | Coverage maps (committed CSVs) + documented effective start dates per feature branch |

*`gws.liquidity_floors` is no longer produced as a universe gate; the knee utility is retained for optional liquidity-tier/capacity bucketing at deployment.*

---

## Expected Row Counts / Distributions (ranges, not examined values)

- `gws.index_membership`: thousands of tickers × membership intervals (order 10k–100k interval rows across the full window).
- `gws.universe_eligibility`: large (tickers × trading days). **Eligible-universe size is now larger than the v1 ≈2,000–2,500 target** because the ADV floor is gone — it is roughly the count of valid index members per date (the full institutional-grade spectrum down to the thinner index names). To be confirmed, not assumed.
- Null rates: `adv_50d`/`dollar_volume_50d` null only during a ticker's first 50 trading days; `to_date` null for current members.

If any actual output deviates materially from these ranges, it is escalated (Trigger 1) rather than silently accepted.

---

## Anticipated Decisions During the Phase

1. **Norgate index coverage gaps** (Step 0): if an index lacks reliable historical constituents, drop it with documented rationale → Scott reviews.
2. **FMP/Norgate price discrepancy resolution** (Step 2): how to resolve disagreements in the 2010–present overlap (expected: prefer Norgate for split/dividend-adjustment integrity; document discrepancy counts).
3. **Fundamental `available_date` source** (Step 2): whether reliable filing/release dates exist; if not, fall back to the pre-committed 60-day lag.
4. **Market-context effective start dates** (Step 2): the dates options (Factor 1) and high-yield credit (Factor 3) data become reliable; Factor 2 (breadth) + trend anchor confirmed computable across the full price window.

---

## Success Criteria

- Output tables populated; coverage maps and effective start dates committed.
- **Index membership PIT-clean:** no ticker flagged as a member on a date before it actually joined the index (verified by SQL spot-checks).
- Data-quality sweep run across the full eligible+delisted universe; every correction logged; the validity screen demonstrably rejects zero-volume/stale-print stretches (so moves can't form on non-traded bars).
- `universe_eligibility` correctly distinguishes the quality filter (index membership) from the data-validity screen; liquidity metrics are recorded but never gate `eligible`.
- Raw outputs (row counts, 20-row samples, null counts, min/max/mean) assembled into the Part-2 gate document.

---

## Step-by-Step Plan (binding specification for implementation)

0. **`verify_norgate_index_coverage.py`** — confirm Norgate Platinum carries historical constituents (including delisted constituents) for each target index across the study window. Output a coverage table per index. **Go/no-go for the index set.**
1. **`ingest_index_membership.py`** — Norgate → `gws.index_membership` as PIT from/to intervals, keyed by Norgate `assetid` mapped to `ticker_id`. Delisted constituents included.
2. **`completeness_audit.py`** — price/volume coverage by ticker/date with FMP↔Norgate cross-validation (reuse `ka_history_crosscheck.py`); fundamentals coverage by statement type/quarter + confirm `available_date` source; index-constituent coverage; market-context data availability. Document effective start dates per branch.
3. **`data_quality_sweep.py`** — phantom-zero repair + split-explosion/overflow cross-check across the full eligible+delisted universe; log every correction to `gws.data_quality_exceptions` (+ `ticker_exclusions`). Reset any sync watermark per the watermark-after-corrections rule. **This screen now carries the anti-pollution load** (v2) — it must catch corrupted/stale/zero-volume rows so moves cannot form on non-traded bars.
4. **`compute_liquidity_metrics.py`** — compute and store the recorded liquidity *features* (50-day ADV, dollar volume, market cap, nominal price) per ticker-date. These are inputs to A2/A3 and to the deployment capacity layer — **not** eligibility gates.
5. **`build_universe_eligibility.py`** — assemble the PIT flag: `eligible = index_member` (Layer 1, quality) `∧ data_valid` (Layer 2, the minimal validity screen incl. real volume + min $1 price) `∧ 252-day history`, with retention rules → `gws.universe_eligibility`. ADV/dollar-volume recorded, never gating.
6. **Verification** — row counts, null rates, 20-row samples, PIT spot-checks; assemble the Part-2 raw-outputs document for the four-auditor Gate 0→A1 review.

Each step commits with `KA-0-STEP-NN: … — verified <metric>` and follows Sprint-Mode escalation triggers. Implementation of Phase A1 does not begin until all four auditors CLEAR Gate 0→A1.

---

## Risks and Open Questions Going In

- **Norgate index coverage** — older Russell / Nasdaq-100 historical membership depth is uncertain; Step 0 is a hard go/no-go.
- **Pre-2011 delisted survivorship** — the survivorship-free claim for 1950–2009 depends entirely on Norgate's delisted-constituent + delisted-price coverage being complete (FMP delisted is post-2015 only). Confirm in Steps 0–2.
- **Fundamental filing dates** — if reliable filing/release dates are absent, `available_date` falls back to the conservative lag (more conservative, not look-ahead).
- **Data quality at the low-liquidity end (the v2 cost)** — dropping the ADV floor admits the thinner index members, which is exactly where price data is marginally worse (more stale prints, more split/adjustment edge cases). The data-validity screen + "actually-traded bars" rule are the defense; their coverage must be verified (on synthetic now, on real data inside the gate). Mitigant: Layer-1 index membership still excludes the genuine OTC/pink-sheet garbage, so this is a clean expansion to the low-liquidity end of *real* index members, not a floodgate.
- **Scale** — without the ADV floor, the universe and move population grow; expect heavier compute and more overlap/dependence. A tractability concern, not a bias one — handled by percentile significance and a pre-committed primary scale, not by re-imposing a floor.

---

*Pre-committed by the implementation agent for Scott Oman review and four-auditor Gate 0→A1 audit. No Phase-0 implementation has begun as of this commit.*
