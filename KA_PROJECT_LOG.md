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

## 2026-07-24 — Phase 0 real-data work opened on KA-Workstation; Step-0 GO
**Event type:** DECISION + GATE PASSED (Step-0)
**Auditor or trigger:** Scott ("start the study"), on KA-Workstation local DB (post-G8), NDU installed, norgatedata 1.0.77
**Finding:** Step-0 verifier first run returned NO-GO on 5/7 indexes against the pre-committed REQUIRED_START values. Targeted evidence showed every miss equals vendor/index inception, not a coverage gap: S&P 600 launched 1994-10-28 (Norgate from inception); Russell constituent flags begin exactly 1990-07-03 for GE/XOM/IBM (July 1990 reconstitution = series start); NDX-100 flags begin 1993-10-01 for AAPL/MSFT/INTC (members since the 1980s → vendor series start). S&P 500 depth is strong (sampled earliest 1957-03-04).
**Remediation / decisions ratified by Scott:**
- **Deep-era universe rule pre-committed: all-listed-equity.** Pre-index eras use all listed equities passing data-validity gates; era boundaries documented (1962 AMEX, 1982 NASDAQ breadth jumps). The index gate applies only from each index's vendor series start.
- **REQUIRED_START amended to vendor/inception dates** (sp600 1994-10-28; r1000/r2000/r3000 1990-07-03; ndx100 1993-10-01), all 7 indexes kept. Re-run: clean GO, delisted members sampled on every index.
- **UNKNOWN-vs-non-member rule:** dates before an index's series start are UNKNOWN membership, never non-member. Absence of an interval row is only evidence of non-membership on/after that index's vendor start; `universe_eligibility` must encode this.
- **FRED ingest deferred** — deep-regime inputs stay price/breadth-derived unless a pre-committed spec later requires macro series.
**Resolution:** Step-0 GO. Next: Step-1 membership ingest (parallelized fetch layer for the 32-core workstation), completeness audit, universe_eligibility, then Gate 0.5 pilot per `phases/GATE05_PILOT_PRECOMMIT.md`.
**Scott sign-off:** approved 2026-07-24 (in-session, three decisions answered explicitly)

## 2026-07-12 — h007–h010 restructured to the standard sealed-hypothesis template
**Event type:** DECISION
**Auditor or trigger:** Scott request, after h011 arrived as a fully-structured document
**Finding / remediation:** h007–h010 plaintexts rewritten into the h011 template (numbered sub-hypotheses with predictions, failure hypothesis, null hypothesis, acceptance/success criteria phrased in the study's own instrument vocabulary — findings-hierarchy tiers, family-FDR, required controls, per-sub-hypothesis partial credit). Content-preserving: Scott's verbatim statements and all directional bets unchanged; structure only. Still pre-data (pre-Gate-0.5), so precedence is intact. New hashes committed; original hashes remain in git history as the earlier precedence proof (noted in `hypothesis_commitments.md`). Done in-session rather than by an external agent: the plaintexts already existed in this design session's context, so no new exposure was created, and the acceptance criteria could be bound to the study's actual evaluation machinery.
**Resolution:** Re-sealed; nothing runs.
**Scott sign-off:** approved 2026-07-12 (session request)

## 2026-07-12 — h011 sealed (complete written prior document from Scott)
**Event type:** DECISION
**Auditor or trigger:** Scott delivered a fully-written, self-contained hypothesis document marked LOCKED for post-study evaluation
**Finding / remediation:** Sealed verbatim as **h011** (hash committed, plaintext local/gitignored; subject private by design). No neutral registration needed: the relevant measurement input already appears in the open market-context candidate set (`research/market_context_inputs.md`), so the instrument side was registered before this prior existed. Vocabulary note recorded: Scott's document self-describes as a "lockbox" item; the GWS lockbox proper is the held-out time period (§12.7) — this is a sealed-hypothesis-vault item, evaluated per its own status field only after the primary study completes. Scope note: several of the document's research questions extend beyond GWS into the broader market-regime framework; per the document, all are post-study evaluation.
**Resolution:** Sealed; nothing runs.
**Scott sign-off:** approved 2026-07-12 (document provided directly)

## 2026-07-11 — h009 + h010 sealed + neutral reward/risk response-curve question registered
**Event type:** DECISION
**Auditor or trigger:** Scott design discussion (ATR / ATR-deviation; MA-extension for entry and exit)
**Finding / remediation:** Two new pre-data priors, handled with the established split (directional bets sealed, neutral instrument registered openly). Sealed separately so B3 scores them independently:
1. **h009 sealed** (ATR-related) and **h010 sealed** (MA-extension-related) — hashes committed, plaintexts local/gitignored, subjects private by design.
2. **Direction-free open question logged** at `research/open_questions/reward_risk_response_curves.md`: read the Method-8 forward-MFE/MAE surface (`gws.entry_candidates`) as response curves over volatility state (ATR% + ATR-vs-own-baseline) and swept MA-extension, both tails informative (entry AND exit sides — the exit read is new framing, not a new instrument), with a REQUIRED move-age/gain-so-far control so a mechanical trailing-stop artifact can't masquerade as signal. To fold into the A3 entry-point pre-commit when written (post-Gate-0.5). All inputs are already in the frozen A2 net / inception catalog — no feature added, detector unchanged, nothing runs.
3. Settled-list check recorded: extension-based exits were NOT falsified by the pipeline graduated-exit backtests; the withdrawn ATR% screen gate (2026-05-11) constrains production filters, not discovery features.
**Resolution:** Sealed + registered; nothing runs.
**Scott sign-off:** approved 2026-07-11 (session Q&A)

## 2026-07-11 — h008 sealed + neutral transfer-temporal-distance question registered
**Event type:** DECISION
**Auditor or trigger:** Scott design discussion (cycle-conditional setup efficacy)
**Finding / remediation:** A new pre-data prior from Scott, handled with the h007 split — directional bet sealed, neutral instrument registered openly:
1. **h008 sealed** (hash committed, plaintext local/gitignored). Subject private by design.
2. **Direction-free open question logged** at `research/open_questions/transfer_temporal_distance.md`: extend the pre-committed §12.1 transfer test from one early→late split to a transfer CURVE over a ladder of train→test temporal distances, run per feature class (emotional vs structural), and compare temporal-proximity weighting vs similarity-matched regime analogy OOS. To be folded into the Phase A3 regime-conditioned analysis pre-commit when that [FORWARD] spec is written (post-Gate-0.5) — no instrument built now; feature freeze and Gate 0.5 sequencing intact. Known constraints recorded in the note: cycle boundaries are hindsight-defined (deployment claims must be calendar-time/PIT), circularity guard on era definitions, Market School machinery stays sealed until B3, deep history load-bearing for the k-ladder.
**Resolution:** Sealed + registered; nothing runs.
**Scott sign-off:** approved 2026-07-11 (session Q&A)

## 2026-07-10 — Pattern-query surface review: direction affordance, candlestick backlog, intraday deferred, h007
**Event type:** DECISION
**Auditor or trigger:** Scott design question — "will the move-classification DB be searchable on a pattern basis (e.g. parabolic shorts in downtrend vs uptrend regimes; intraday demand signatures of winners vs non-winners), and should the study also classify downward moves?"
**Finding:** Review against the built catalog concluded the pattern-search capability is ALREADY the design: `gws.moves` typed columns + descriptors/inception JSONB bags + GIN/expression indexes + the composable `MoveQuery` layer (regime via `context_label`, theme via `tickers_in`, PIT inception slices, outcome-filter tripwire). Winner-vs-non-winner contrast is the core two-dataset design (matched controls, failed lookalikes, setup_labels). Three real gaps: (1) no `direction` concept anywhere — "parabolic shorts" is unrepresentable, and adding it later means a natural-key migration + full re-persist of a populated catalog; (2) no literal candlestick bar-anatomy descriptors (closing range, tail ratios, spread); (3) no intraday data anywhere in the design — a new data workstream, modern-window-only regardless of source.
**Remediation / decisions (scoped to respect the 2026-06-20 design-close + 2026-06-21 feature freeze):**
1. **Schema affordance only for direction (approved option).** `gws.moves.direction` (`'up'`/`'down'`, DEFAULT `'up'`, CHECK-constrained) added to the schema and to the natural key; writer stamps `'up'`; `MoveQuery.direction()` predicate added (a population selector like scale/detection_system, NOT an outcome filter). The study remains UP-MOVES ONLY through all current phases. Down-move detection/classification is a FUTURE SIBLING pre-committed study (own hypotheses, decision matrix, gates) after Gate 0.5 — never folded into the current discovery run. Rationale: the catalog is empty today, so the column is one line now vs a key migration later; scope discipline is preserved because nothing down-related runs.
2. **Candlestick bar-anatomy descriptor family → classification backlog** (freeze-safe additive per the backlog's standing rules; CHAR_VERSION bump on implementation). The A2 discovery feature net stays frozen.
3. **Intraday: availability audit FIRST, no design work.** Before any intraday descriptor branch exists, audit FMP Ultimate intraday granularity/history depth/rate limits/storage vs UW-era capture. Any eventual branch is modern-window-only and follows the fundamental-branch availability pattern (NULL in deep history). Decision after the audit + Gate 0.5.
4. **h007 sealed** — Scott's pre-data prior on intraday/candlestick demand signatures goes into the sealed-hypothesis vault (plaintext private, hash committed), tested at B3 like h001–h006. Zero researcher-DoF cost.
**Resolution:** Design freeze and Gate 0.5 sequencing intact; master doc unchanged by design (no current-study methodology changed). Implementation limited to the direction affordance + backlog entry.
**Scott sign-off:** approved 2026-07-10 (session Q&A: schema-affordance-only / audit-first / seal-h007)

## 2026-06-21 — Feature net FROZEN + risk re-ranking (review feedback)
**Event type:** DECISION
**Auditor or trigger:** External review (9.2/10) of the 2026-06-21 review package
**Finding:** The feature-net expansion (volume/base/RS/group/breadth/weekly/float/earnings) improved comprehensiveness but pushed the project to the inflection where comprehensiveness itself becomes overfitting pressure. Researcher degrees of freedom is now under-ranked at #10.
**Remediation:**
1. **Risk register re-ranked** (master doc §13): researcher degrees of freedom moved #10 → #7, above several implementation risks (K, multi-scale dependence, failed-lookalike controls shift down).
2. **Feature net FROZEN pending real data.** The catalog is closed: the A2 pre-commit fixes the final feature list; no features added during discovery. Converts "stop expanding" from advice into an enforced constraint — itself a researcher-DoF control. Further capability questions wait for the Gate 0.5 pilot.
**Resolution:** Design expansion halted. Remaining uncertainties are now EMPIRICAL (does emotional invariance hold; does the transfer test pass; breakout vs trough; are failed-lookalikes distinguishable; are signals regime-specific) — only data answers them. Reviewer-approved next steps: Norgate ingest → Phase 0 → Gate 0.5 pilot → stationarity transfer + trough-vs-breakout experiments, before any further methodology expansion.
**Scott sign-off:** approved 2026-06-21

## 2026-06-21 — Trend-following foundations (7 additions)
**Event type:** DECISION
**Auditor or trigger:** Off-the-record design debate with Scott ("what strengthens the foundation, bias-free, that we'd backtrack to add later?")
**Finding / remediation:** Seven comprehensiveness/capability additions (wider neutral net + data capture, never assertions). See `research/trend_following_foundations.md`.
- BUILT (A2 feature code, tested): #3 consolidation/base family (base_depth, range_position, vol_contraction, tight_days_share); #4 RS-line family (rs_line_slope, rs_at_high); #2 group-strength function (`group_strength.py` — sector_rs, sector_rs_slope, group_strength); #7 weekly-resample helper (`common/resample.py`, families run on both timeframes). All motivation-tagged (fail-closed), PIT-clean (future-invariance harness). +8 tests, 115 pass.
- SPEC (Phase 0 data capture, PHASE0_PRECOMMIT v3): #2 sector/industry + sector returns (Norgate, potentially deep-history); #5 earnings report dates as event markers (FMP, modern-window only); #6 free float (FMP, modern-window only). All recorded as features/markers, never gates; earnings/float join the fundamental branch (NULL in deep history per the branch-availability design).
- DESIGN (implement in A1): #1 failed-lookalike negatives — the negative/control set must include configuration-matched FAILED setups, not random non-events (the trend-following discriminator). Defined by configuration, bias-clean.
**Resolution:** Built + pre-committed before any implementation. Rationale: data capture + feature families are the expensive-to-backtrack layers; do now. Bias discipline intact (first-principles measurements, sealed frameworks, motivation tags).
**Scott sign-off:** approved 2026-06-21

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
