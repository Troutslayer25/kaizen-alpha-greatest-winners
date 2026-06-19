# Phase 0 — Pre-Committed Specification (Gate 0→A1)

**Phase:** Phase 0 — Universe Construction and Database Completeness Audit
**Gate:** 0→A1
**Submitted by:** Implementation agent
**Status:** PRE-COMMITMENT — committed to GitHub before any Phase-0 implementation begins.

> ⚠️ This document is Part 1 of the Phase-0 planning session. Its GitHub commit
> timestamp is the proof of pre-commitment. Implementation commits for Phase 0 must
> post-date this commit. Auditors verify this at Gate 0→A1.

---

## Pre-Spec Exploration Disclosure (mandatory)

Before writing this specification, the following was examined — disclosed in full for Auditor 4:

- ☑ **Existing KA pipeline code/schema was read** (via read-only exploration of `~/kaizen-alpha`) to plan reuse: `ka_lib` (db/fmp/log), the step/ingest patterns, `eod_prices`/`fundamentals` schemas, the Norgate `ka_history` schema and loaders, and the existing data-quality machinery (`ticker_exclusions`, `data_valid_from`, `instrument_type`, `repair_phantom_zero_adj_close.py`, `ka_history_crosscheck.py`). This is code/schema inspection, **not** examination of analytical data outputs.
- ☑ **DB structural facts known from prior project memory:** historical PIT index-constituent membership does **not** currently exist in the DB (it must be ingested from Norgate); FMP's delisted endpoint is post-2015 only; documented data-quality issues exist (phantom-zero `adjusted_close`, split-explosion, NUMERIC overflow). These are structural facts about *what data exists*, not snooped distributions.
- ☑ **Phase-0/method machinery was pre-built and committed as synthetic-validated tooling** (e.g., `gws/phase0/liquidity_floor.py` knee-of-curve discovery). This fixes the *method* before any real values are seen.

**No exploratory data queries were run.** Specifically, for the bias-relevant Gate 0→A1 risk points:

> ☑ The liquidity-floor **values** have NOT been computed or examined for any real period. Only the discovery *method* is fixed (below).
> ☑ The real ADV distributions, eligible-universe sizes, and index-membership counts have NOT been examined.
> ☑ The index set (below) was chosen by neutral pre-commitment — the full institutional-grade spectrum — not selected after observing which names it includes/excludes.

---

## Pre-Committed Decisions

These resolve the Phase-0 open questions and are fixed before implementation:

- **OQ-1a — Index set (quality filter):** the union of all major US indexes — **S&P 500, S&P MidCap 400, S&P SmallCap 600, Russell 1000, Russell 2000, Russell 3000, Nasdaq-100** — sourced from Norgate historical constituent data, applied as a strict PIT daily flag. Rationale: captures the full institutional-grade spectrum (large→small cap) while excluding OTC/pink-sheet/warrant/rights/foreign-cross-listing/stub instruments without manual lists. **Any index Norgate does not cover for a given window is dropped with documented rationale (Step 0 verifies coverage).**
- **OQ-1b — Penny-stock floor:** minimum nominal price **$5 (adjusted close), PIT daily**. The empirical ADV floor handles residual illiquidity.
- **OQ-2 — Liquidity-floor discovery method:** the **knee-of-curve** of the sorted `log10(50-day ADV)` distribution across index-constituent equities (`gws/phase0/liquidity_floor.discover_floor`, already committed and synthetic-validated). Run **separately per calendar year** and **separately for the 1950–2009 and 2010–present windows**. The floor for each (period, year) is the value the data produces and is **not adjusted after observing downstream effects** on the move population.
- **OQ-9 — Fundamental availability (recorded for Phase A2, audited in Phase 0):** fundamentals are gated on `available_date` = the public filing/release date when reliable, else `period_end + 60-day conservative lag`, with `CHECK (available_date <= as_of_date)`. `period_end` is the quarter identifier only. Phase 0 confirms whether reliable filing/release dates exist in the source.
- **Retention (survivorship protection):** delisted/merged/bankrupt tickers retained through their last active date; zero-volume rows retained as non-trading flags, never deleted.
- **Minimum history:** 252 trading days before a ticker is eligible.

---

## What Phase 0 Will Produce

| Output | Table / artifact |
|---|---|
| Historical PIT index membership | `gws.index_membership` (ticker_id, index_name, from_date, to_date) |
| Empirically discovered liquidity floors | `gws.liquidity_floors` (period_label, year, adv_floor_value, discovery_method, n_tickers_in_dist) |
| Two-layer eligibility flag (single source of truth) | `gws.universe_eligibility` (ticker_id, date, eligible, index_member, above_price_floor, above_adv_floor, adv_50d, adv_floor) |
| Data-quality corrections/exclusions | `gws.data_quality_exceptions` + `ticker_exclusions` entries |
| Completeness-audit outputs | Coverage maps (committed CSVs) + documented effective start dates per feature branch |

---

## Expected Row Counts / Distributions (ranges, not examined values)

- `gws.index_membership`: thousands of tickers × membership intervals (order 10k–100k interval rows across the full window).
- `gws.liquidity_floors`: ~one row per year per period (≈ 60–80 years × 2 periods, bounded by confirmed data coverage).
- `gws.universe_eligibility`: large (tickers × trading days); **eligible-universe size ≈ 2,000–2,500 tickers on any given date in the primary window** (per the design target — to be confirmed, not assumed).
- Null rates: `adv_50d`/`adv_floor` null only during a ticker's first 50 trading days; `to_date` null for current members.

If any actual output deviates materially from these ranges, it is escalated (Trigger 1) rather than silently accepted.

---

## Anticipated Decisions During the Phase

1. **Norgate index coverage gaps** (Step 0): if an index lacks reliable historical constituents, drop it with documented rationale → Scott reviews.
2. **FMP/Norgate price discrepancy resolution** (Step 2): how to resolve disagreements in the 2010–present overlap (expected: prefer Norgate for split/dividend-adjustment integrity; document discrepancy counts).
3. **Fundamental `available_date` source** (Step 2): whether reliable filing/release dates exist; if not, fall back to the pre-committed 60-day lag.
4. **Market-context effective start dates** (Step 2): the dates options (Factor 1) and high-yield credit (Factor 3) data become reliable; Factor 2 (breadth) + trend anchor confirmed computable across the full price window.

---

## Success Criteria

- All four output tables populated; coverage maps and effective start dates committed.
- **Index membership PIT-clean:** no ticker flagged as a member on a date before it actually joined the index (verified by SQL spot-checks).
- Liquidity-floor discovery-method commit timestamp predates any floor-value computation.
- Data-quality sweep run across the full eligible+delisted universe; every correction logged.
- `universe_eligibility` correctly distinguishes quality-filter failures from liquidity-filter failures.
- Raw outputs (row counts, 20-row samples, null counts, min/max/mean) assembled into the Part-2 gate document.

---

## Step-by-Step Plan (binding specification for implementation)

0. **`verify_norgate_index_coverage.py`** — confirm Norgate Platinum carries historical constituents (including delisted constituents) for each target index across the study window. Output a coverage table per index. **Go/no-go for the index set.**
1. **`ingest_index_membership.py`** — Norgate → `gws.index_membership` as PIT from/to intervals, keyed by Norgate `assetid` mapped to `ticker_id`. Delisted constituents included.
2. **`completeness_audit.py`** — price/volume coverage by ticker/date with FMP↔Norgate cross-validation (reuse `ka_history_crosscheck.py`); fundamentals coverage by statement type/quarter + confirm `available_date` source; index-constituent coverage; market-context data availability. Document effective start dates per branch.
3. **`data_quality_sweep.py`** — phantom-zero repair + split-explosion/overflow cross-check across the full eligible+delisted universe; log every correction to `gws.data_quality_exceptions` (+ `ticker_exclusions`). Reset any sync watermark per the watermark-after-corrections rule.
4. **`liquidity_floor` run** — apply the pre-committed knee method per year, per period → `gws.liquidity_floors`.
5. **`build_universe_eligibility.py`** — assemble the two-layer PIT flag: index membership (Layer 1) ∧ ($5 price floor ∧ ADV-floor, Layer 2) ∧ 252-day history, with retention rules → `gws.universe_eligibility`.
6. **Verification** — row counts, null rates, 20-row samples, PIT spot-checks; assemble the Part-2 raw-outputs document for the four-auditor Gate 0→A1 review.

Each step commits with `KA-0-STEP-NN: … — verified <metric>` and follows Sprint-Mode escalation triggers. Implementation of Phase A1 does not begin until all four auditors CLEAR Gate 0→A1.

---

## Risks and Open Questions Going In

- **Norgate index coverage** — older Russell / Nasdaq-100 historical membership depth is uncertain; Step 0 is a hard go/no-go.
- **Pre-2011 delisted survivorship** — the survivorship-free claim for 1950–2009 depends entirely on Norgate's delisted-constituent + delisted-price coverage being complete (FMP delisted is post-2015 only). Confirm in Steps 0–2.
- **Fundamental filing dates** — if reliable filing/release dates are absent, `available_date` falls back to the conservative lag (more conservative, not look-ahead).

---

*Pre-committed by the implementation agent for Scott Oman review and four-auditor Gate 0→A1 audit. No Phase-0 implementation has begun as of this commit.*
