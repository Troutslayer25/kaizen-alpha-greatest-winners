# KA Greatest Winners Study — Project Log

All HALT events, escalations, and gate decisions are recorded here, newest first.

Entry format:
```
## [Date] — [Gate or Sprint phase]
**Event type:** HALT / ESCALATION / GATE PASSED / DECISION
**Auditor or trigger:** [which auditor or escalation trigger]
**Finding:** [what was found]
**Remediation:** [what was done]
**Resolution:** [CLEARED / OVERRIDE with written justification]
**Scott sign-off:** [initials and date]
```

---

## 2026-06-21 — A2 volume family + sealed-hypothesis vault stood up
**Event type:** DECISION
**Auditor or trigger:** Off-the-record design debate with Scott
**Finding / remediation:**
1. **A2 volume feature family expanded comprehensively from first principles** (`compute_features`, `gws/phase_a2/features_price_volume.py`): added vol_surge (RVOL), vol_trend, accum_vol_share, up_vs_down_vol_extreme (biggest buying vs biggest selling day), and cmf (Chaikin money flow), alongside the existing vol_ratio / updown_vol. Designed across the natural ways to measure volume so any volume-based accumulation signal can be DISCOVERED — NOT reverse-engineered to any specific practitioner rule (general measures + the standard lookback sweep, not a named rule's specific window). New prefixes added to the motivation map (fail-closed). Future-invariance (PIT) auto-covered by the existing harness; +1 test. 107 pass.
2. **Sealed-hypothesis vault stood up** (hash-commitment mechanism): `research/hypothesis_commitments.md` (committed) records opaque IDs + SHA-256 of private plaintext priors kept local/gitignored at `research/hypotheses/sealed/` (never pushed). The commit timestamp proves a prior predates discovery; the opaque ID reveals no subject, so even the committed record cannot bias discovery; at B3 the plaintext is revealed and re-hashed to verify. First entry **h001** sealed (a pre-data prior to be compared against discovered findings at B3). Subject is private to Scott; not recorded here by design.
**Resolution:** Built + committed. Bias integrity preserved (volume family justified on first-principles grounds; hypothesis sealed opaque, opened only at B3).
**Scott sign-off:** approved 2026-06-21
**Note:** Scott should keep a private backup of the `research/hypotheses/sealed/` plaintext (gitignored = not in GitHub); if lost before B3 the commitment cannot be verified.

## 2026-06-21 — Design refinement: swept breadth-MA surface (on-the-fly)
**Event type:** DECISION
**Auditor or trigger:** Off-the-record design debate with Scott (market-health inputs)
**Finding:** The "% of stocks above the 5-day MA" (FOMO indicator) is valuable but hardcoding one named horizon contradicts the discovery-first principle — and the same logic already applied to stock-level MAs (sweep, don't hardcode).
**Remediation (design change, code built):** `compute_breadth` (`gws/regime/breadth.py`) now computes **% of the eligible universe above the N-day MA across a SWEEP** (`SWEEP_PERIODS = 5,8,10,13,21,50,100,200`) plus a short/long **breadth term-structure spread** (`breadth_spread_5_200`) as a candidate leading-divergence measure. Analyzed as a response curve (not N collinear features); both tails informative; lead-lag analysis discovers which horizon leads vs describes. Price-derived → deep-history → full-study input (not an overlay). Discovery-first: 5-day winning would confirm FOMO; another horizon = novel. Design note: `research/market_context_inputs.md` (also captures the neutral-measurement-vs-sealed-framework split and the candidate market-context input set: VIX family, COR1M/realized correlation, credit spreads, curve slope, rotation ratios, etc., to be pre-committed with the market-context spec). 2 new tests; 106 pass.
**Resolution:** Built + committed. Discovery-first integrity preserved (swept not hardcoded; measurement not framework; relationship discovered).
**Scott sign-off:** approved 2026-06-21

## 2026-06-21 — Design refinement (on-the-fly, post-close)
**Event type:** DECISION
**Auditor or trigger:** Off-the-record design debate with Scott surfaced a real gap (the kind we agreed to handle on the fly)
**Finding:** The move detector anchors entries at troughs. Multi-scale detection already captures pullback/dip entries (as nested-move troughs), but breakout / earnings-gap / MA-reclaim entries are POINTS OF STRENGTH — never local lows at any scale — so no trough anchor reaches them. The study could capture every move yet never flag the buyable pivot Scott actually trades.
**Remediation (design change, pre-committed before any A3 implementation):** Expand Phase A3 Method 8 (entry-point analysis) to evaluate candidate entries at points ALONG each move — including points of strength, not only the pre-trough window — scored empirically by forward reward (MFE) / risk (MAE). "Low-risk entry" defined as best forward MFE/MAE; no pattern pre-defined. Production version forward-labels arbitrary points (hindsight-free). **Move detector UNCHANGED** — analysis layer only. Same bias guards; validation by our own methods, NOT by CANSLIM agreement; frameworks consulted only at B3 (convergence vs novelty). Operationalizes the trough-vs-breakout experiment. New schema table `gws.entry_candidates`. Full spec: `research/entry_point_discovery.md`.
**Resolution:** Rolled into the spec (master doc §8, design note, schema, this log). Discovery-first integrity preserved (framework-neutral; CANSLIM sealed to B3). Not a contamination event — pure method.
**Scott sign-off:** approved 2026-06-21

## 2026-06-20 — Design phase CLOSED
**Event type:** DECISION
**Auditor or trigger:** Final external institutional review (8.8 institutional research quality)
**Finding:** Independent reviewer scored the design strong across all dimensions; every sub-9 score is an implementation/data-readiness gap, not a design gap. Verdict: "strong final design, I would not keep redesigning it — proceed to Norgate ingest → Phase 0 → Gate 0.5 pilot." Reviewer's risk list matched the §13 register independently. This is the exit signal agreed in the wind-down.
**Remediation / decision:** Design phase declared CLOSED. Adopted the reviewer's single insisted item: Gate 0.5 must produce a signed written go/no-go memo answering "Is the study learning a transferable winner setup, or merely rediscovering regime-specific historical artifacts?" (transfer/stationarity test = evidence). Folded into the V11 Gate 0.5 spec + master doc. No further design rounds; remaining weaknesses handled on the fly during implementation.
**Resolution:** CLEARED to proceed to data work (gated on FMP backfill + workstation).
**Scott sign-off:** agreed 2026-06-20

## 2026-06-20 — Pre-implementation (validation architecture)
**Event type:** DECISION
**Auditor or trigger:** External critique (ChatGPT) — concrete method proposals; Scott approved the triaged subset
**Finding:** Treat the target, universe, and control design as first-class objects of validation, not fixed infrastructure ("validate the definition, not just the model"). The full proposal (12 methods + 5 new gates) would, taken whole, be the analysis-paralysis machine the same review warned against.
**Remediation / decisions (triaged subset, all approved):**
- BUILT now: negative-control harness (`gws/common/negative_controls.py`) + research-path/family-FDR + deflated Sharpe (`gws/phase_a3/research_path.py`), with tests (104 total pass).
- ONE new hard gate: **Gate 0.5 — real-data pilot sanity** (break the pipeline on 100–300 tickers before full compute). The other proposed gates (A1.5/A2.5/A3.5/X.5) folded into existing gates as required analyses — NOT new gates.
- **Marginal-sensitivity discipline** (critical): vary one design axis at a time vs pre-committed defaults, never a full grid; multi-target = primary + robustness labels, not co-equal discovery. This prevents the sensitivity studies from exploding the search space that family-FDR then has to correct.
- Deferred to phase: economic-validation metrics (Phase X/B2), post-discovery decay monitoring (B-phase), independent mechanism test (extends blind review).
- Pushed back on / declined: 5-new-gate proliferation; co-equal multi-target discovery (6x compute + DoF); hard-gate on mechanism auxiliary predictions (kept strong-preference).
- Auditor framework V10 → V11 (Appendix G; Gate 0.5 added to the gate table).
**Resolution:** FINAL design pass. Further weaknesses handled on the fly. Consolidated final master document issued for one last external review.
**Scott sign-off:** approved 2026-06-20

## 2026-06-20 — Pre-implementation
**Event type:** DECISION
**Auditor or trigger:** External critique (ChatGPT) on target non-stationarity + Scott reframe
**Finding:** The dominant risk is conceptual, not execution: a "great winner setup" may not be a stable, universal phenomenon across regimes. Prior rounds hardened execution (detector, liquidity, PIT) but left this premise untested.
**Remediation / decisions:**
- Make **regime a first-class discovery axis**: discover the move taxonomy per environment, characterize how it morphs, and build a regime-analogy engine ("what past regime are we in; what worked then?"). Non-stationarity becomes the subject, not the failure mode.
- Adopt the **emotional-invariance hypothesis** as the study's central, *testable* thesis: behavioral/emotional features (contraction, shakeout depth/timing, volume, smoothness, RS persistence) should transfer across regimes; structural features (price levels, fundamentals magnitude, sector, duration) should not. Held as a hypothesis, confirmed/denied by the transfer-test — discovery-first discipline applies to it.
- Adopt regime-relative feature normalization and (continuous) regime-analogy similarity.
- Add seven pre-committed early go/no-go experiments (run on the real-data pilot BEFORE full compute): target-stationarity transfer test (emotional vs structural), trough-vs-breakout move-anchor sensitivity, universe-definition sensitivity, multiple significance definitions, multiple control constructions, continuous-vs-discrete characterization as co-equal, and a true lockbox period.
- Snowball-risk register reordered: **target non-stationarity** and **trough-vs-breakout anchoring** elevated above Norgate membership accuracy. Deep-history (Norgate 1950–2009) is now load-bearing for the regime thesis.
- Process: this is the LAST synthetic-stage critique round; the real validator is the data run. Captured in `research/regime_conditional_discovery.md`.
**Resolution:** Captured as design decision; folds into Phase A1/A3 pre-commit when reached. No code/data work triggered.
**Scott sign-off:** agreed 2026-06-20

## 2026-06-19 — Pre-implementation
**Event type:** DECISION
**Auditor or trigger:** Planning session (implementation blueprint)
**Finding:** Critical-path review against the existing KA database found historical PIT index-constituent membership (the universe foundation) is **not present** — it must be ingested from Norgate before any universe work. Reusable KA components and known data-quality machinery catalogued.
**Remediation / decisions ratified by Scott:**
- T1/T2 adopted: two-dataset model (matched controls for discovery; universe-sampled forward-labeled points for production) + `(ticker_id, as_of_date)`-keyed feature store via an `observations` table.
- T4 adopted (modified): cluster on magnitude + duration + an uncensored smoothness metric; retain raw drawdown as a comparative/diagnostic input.
- T6/OQ-7 adopted: expanding temporal walk-forward + purge + embargo is binding; ticker non-independence handled by ticker-clustered SEs; ticker-disjoint CV is a robustness probe only.
- OQ-1a/OQ-3b adopted as starting points: index union (S&P 500/400/600 + Russell 1000/2000/3000 + Nasdaq-100); primary reversal threshold 20%.
- Prior-code reuse governance (§1A) adopted with lighter Tier-A handling (attest once, approved forever; scrutiny on Tier B/C).
- Clustering simplified to HDBSCAN + bootstrap stability.
- Synthetic test dataset added as the first foundational deliverable.
- Auditor framework advanced V5 → V6 to reconcile with the V10 design.
**Resolution:** Blueprint approved. V6 committed (`3338fba`) and pushed.
**Scott sign-off:** approved 2026-06-19
