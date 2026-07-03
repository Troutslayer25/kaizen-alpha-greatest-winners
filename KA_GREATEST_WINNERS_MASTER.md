# Kaizen Alpha — Greatest Winners Study
## Master Methodology, Validation Architecture & Risk Register (final design pass)

> **Status.** This is the consolidated, definitive design document, current to auditor
> framework V11. It supersedes the earlier standalone explainer/critique drafts. The design
> is considered settled after multiple adversarial-review rounds; remaining weaknesses are to
> be handled on the fly. **No real market data has been processed.** Tags: **[BUILT]** = code
> exists + unit-tested (104 tests pass); **[SCHEMA]** = table defined, no writer yet;
> **[FORWARD]** = designed, not implemented.
>
> **For a final reviewer.** The execution-level concerns (look-ahead, survivorship,
> validation hygiene) are well-hardened — attack the *premise* instead. The two deepest open
> questions are whether a "great winner setup" is a stable, universal phenomenon (it probably
> is not — see §1, §12) and whether trough-anchored moves measure the setup at the right
> reference point for how the stock is actually traded (§4, §12). The snowball-risk register
> (§13) is ranked; challenge the ranking.

---

## 1. What the study is, and its central reframe

**Operational question:** given everything measurable about a stock as of a date, what is the
probability it is in a pre-move setup that precedes a significant advance?

**Discovery-first:** characteristics are found from raw data, written and timestamp-locked,
and only then compared to external frameworks (CANSLIM/IBD/Minervini/Zanger) and the team's
own sealed hypotheses, which stay sealed until Phase B3.

**The central reframe (the study's organizing principle).** A "great winner setup" is almost
certainly NOT one stable, universal phenomenon across decades — 1999 speculative momentum,
2003 recovery, 2020 liquidity-growth, and 2022 energy leadership may be different mechanisms.
Rather than assume one universal target and be blindsided by regime-dependence, the study
makes **regime a first-class discovery axis**: discover the move taxonomy *per environment*,
characterize how it morphs, and build a regime-analogy capability ("what past regime are we
in now; which move-types worked then; are today's leaders showing that signature?").

**The central, testable hypothesis — emotional invariance.** Regimes change; human emotion is
the constant. Behavioral/emotional features (volatility contraction = anticipation; shakeout
depth/timing = fear/capitulation; volume surge vs. dry-up = conviction; path smoothness =
order vs. panic; relative-strength persistence = herding) are hypothesized to **transfer
across regimes**; structural features (price levels, fundamental magnitudes, sector, duration)
are hypothesized **not** to. The transfer test (§12) is the instrument that confirms or denies
this. Held as a hypothesis, tested — discovery-first discipline applies to it too. (Full note:
`research/regime_conditional_discovery.md`.)

**Two targets, two datasets (kept separate):**
- *Primary* — a forward-looking setup classifier (binary: setup vs. control), trained on
  universe-sampled (ticker, date) points forward-labeled by whether a confirmed trough falls
  within the next K days; features measured at the point's own date (matches deployment).
- *Secondary* — descriptive move-type characterization (magnitude/duration/path-shape).
- *Discovery dataset* (matched controls) vs. *production dataset* (`setup_labels`, an
  independent sampling frame) — not derived from each other.

---

## 2. Data infrastructure
FMP (primary, 2010–present: OHLCV + quarterly PIT fundamentals); Norgate (1950–present:
adjusted OHLCV, PIT index membership, delisted tickers, sector/industry/market cap), cross-
validated over the overlap. Deep history is **load-bearing** for the regime thesis (you need
many distinct regimes), not a nicety. Feature-store key: `(ticker_id, as_of_date)`, making
asymmetric extraction structurally impossible. Study tables in a `gws` schema; analytical
functions return index-keyed objects, a documented persistence layer does the translation.

---

## 3. Phase 0 — universe & data audit
Eligibility (daily, PIT): `index_member ∧ data_valid ∧ above_min_price (~$1) ∧ ≥252-day
history`. **Liquidity is NOT a gate** — ADV/dollar-volume/market-cap/price are recorded as
features (so the study can discover liquidity's role); capacity is applied at deployment.
Anti-pollution: a move must occur over actually-traded bars (pollution is bad *data*, not low
*liquidity*; index membership already excludes OTC junk). Fundamentals gated by `available_date`
with a hard `CHECK (available_date <= as_of_date)`. Survivorship: delisted/merged/bankrupt
retained through last active date. Norgate index-membership ingest **[BUILT, ka-runner]**.

---

## 4. Phase A1 — move detection & population mapping
**Canonical detector — threshold-free, multi-scale MFE [BUILT]:** every local low seeds a
candidate; magnitude is measured (continuous distribution; significance = percentile, not a
cutoff); move ends at a `trail_atr × ATR` trailing stop from the running peak (not a round
trip); early drawdown tolerated and recorded (MAE); run at multiple scales (tight = swing
legs, loose = arcs). Path-shape metrics: `smoothness`, plus `early_smoothness` and
`drawdown_timing` (uncensored early-drama dims that separate a violent shakeout from a calm
grind). ATR-swing detector retained only as a cross-check baseline; an absolute-return
detector adds a volatility-independent cross-check.

**Open question flagged for the pilot (§12):** the move is trough-anchored, but the user
trades buyable *pivots* (breakouts from bases), not bottoms. Trough-vs-breakout anchoring is a
pre-committed early experiment — a trough may be the wrong reference point for the tradeable
event.

**Clustering [BUILT]:** mandatory bootstrap stability (ARI/VI; stable/marginal/unstable/
no-structure); `resolve_representation` programmatically decides discrete-vs-continuous for the
marginal band; continuous-spectrum fallback when unstable; `segment_by_early_drama` splits the
fallback by shakeout vs. ascent. Continuous latent-factor characterization is run **co-equal**
with clustering (clustering may be solving a non-problem if the manifold is continuous).

**Controls & labels [BUILT]:** matched controls (minimal set + over-matching diagnostic;
*multiple* control constructions run as a sensitivity); `setup_labels` (forward-labeled, K
from decay).

---

## 5. Point-in-time discipline
Future-invariance harness `assert_future_invariant` (randomize future bars; assert features
unchanged) **[BUILT]**; `available_date` gating; purged/embargoed expanding walk-forward
(expanding overlapping train, non-overlapping sequential test, purge=K, embargo, drop-
incomplete final-fold labels) **[BUILT]**; ticker non-independence via clustered errors /
block bootstrap, with ticker-disjoint CV only as a separate leakage probe.

---

## 6. Market context **[breadth/anchor BUILT; F1/F3 FORWARD]**
Daily `regime_daily` score (Factor 2 breadth + trend anchor now; equity/options + credit
pending data start dates). Attached to each move as a feature, never a discovery filter. The
regime score should lean on partly-exogenous (credit/macro) factors to avoid defining regimes
from the same price data whose move-types are discovered within them (circularity).

---

## 7. Phase A2 — features
Branch-1 price/volume `compute_features` **[BUILT]** (consolidation, proximity, MA relations —
to be **swept** across {3..200}×{SMA,EMA}, not just canonical windows — volume, RS); generic/
auto bank `compute_generic_features` **[BUILT]** (entropy, Hurst, moments, autocorrelation) so
practitioner features compete against framework-neutral ones; provenance/`motivation` tagging
(pre-committed, fail-closed) **[BUILT]**; wide feature matrix including the generic bank
**[BUILT]**; collinearity/VIF diagnostic **[BUILT]**. Features classified emotional vs.
structural (§1) for the transfer test.

---

## 8. Phase A3 — statistical discovery
Helpers (BH-FDR, Cohen's d, ticker block bootstrap) **[BUILT]**; univariate screen (normality-
aware test, effect sizes, KS, BH-FDR) **[BUILT]**; factor+industry neutralization **[BUILT]**;
mutual information **[BUILT]**; feature decay + pre-trough actionability **[BUILT]**; ML bake-
off (RF/XGB/LGBM/ElasticNet/SVM in walk-forward; permutation imp OOS; SHAP) **[BUILT]**;
regime-conditioned analysis **[FORWARD]**; **entry-point analysis (Method 8, expanded) [FORWARD]**.

**Entry-point analysis — low-risk entries *along* the move (Method 8).** The move detector
anchors at troughs; pullback/dip entries are already captured as nested smaller-scale-move
troughs, but breakout / earnings-gap / MA-reclaim entries are *points of strength* — never
local lows at any scale — so they are out of reach of any trough anchor. Method 8 therefore
evaluates candidate entries at points *along* each detected move (not only the pre-trough
window), **including points of strength**, and scores each empirically by forward reward/risk:
**reward = forward MFE** (upside remaining to the peak), **risk = forward MAE** (worst drawdown
from that point). "Low-risk entry" is *defined* as the best forward MFE/MAE — discovered, never
a pre-defined pattern. The production version forward-labels arbitrary `(ticker, as_of_date)`
points by forward reward/risk (deployment-matched, hindsight-free), exactly like the setup
classifier. This operationalizes the trough-vs-breakout experiment (§12.2): the data adjudicates
whether entering at the bottom or at a point of strength gives better risk-adjusted forward
return. **The move detector is unchanged** — this is purely an A3 analysis layer on top of the
moves already detected. Bias discipline: validated by our own methods (neutralization,
walk-forward, findings hierarchy) — NOT by agreement with any external framework; CANSLIM /
sealed hypotheses are consulted only at B3 for convergence-vs-novelty. Full spec:
`research/entry_point_discovery.md`.

**Research-path multiple testing [BUILT]:** family-level (hierarchical) FDR — a feature family
must clear family-level correction before its members are inspected — plus deflated Sharpe for
strategy outputs. A Tier-1 finding survives family-level, not just feature-level, correction.

**Negative-control harness [BUILT]:** the pipeline must find *nothing* in shuffled labels,
features permuted within date, and misaligned labels. A control above chance = leakage/
overfitting. Run at the pilot and at A3.

**Findings hierarchy [BUILT]:** pre-committed tolerances; Tier 1 = walk-forward consistency
(no catastrophic fold) AND retains effect after **both** neutralizations AND pre-trough
actionable. Every Tier-1 finding carries an economic-mechanism annotation, reviewed **blind**
(logic voted without seeing the return profile) + optional falsifiable auxiliary-prediction.

---

## 9. Phase X — scoring model **[components BUILT]**
Three architectures (effect-size linear / Elastic-Net / LightGBM) on identical walk-forward
periods; only Tier-1 features; deployment-matched hindsight-free training. Selection on
discrimination **and** calibration: `fit_calibrator` (held-out split), `reliability_table`,
`brier`, and `calibration_decay` (alarms when AUC falls toward chance behind a flat calibrated
Brier — calibration can't mask degrading ranking). Backtest: `decile_lift` + `capacity_
diagnostic` (where liquidity is applied — at deployment, conditioning on the recorded feature)
+ economic-viability metrics (turnover, slippage, sector concentration, holding period,
capital per unit edge).

---

## 10. Pass B
B1 advanced regime/factor decomposition (incl. context-conditioned calibration as an
experiment); B2 walk-forward + ±20% parameter robustness + Monte Carlo (empirical bootstrap)
**[BUILT]** + deep-history persistence; B3 first external-framework + sealed-hypothesis
consultation, component mapping, back-population, validated v2.

---

## 11. Governance & validation architecture (V11)
Four independent auditors (PIT / quant / statistical / bias) at the gates; all CLEAR to
proceed; any one HALTs; Auditor 4 = agent report + mandatory human review.

**Gates (8 now):** Gate 0→A1; **Gate 0.5 (hard) — real-data pilot sanity**; A1→A2; A2→A3;
A3→A4; A4→B1; B1→B2; B2→B3. The five sensitivity studies the review proposed as new gates are
instead **required analyses within existing gates** (target stability + universe at A1→A2;
control design at A2→A3; research-path FDR at A3→A4; economic viability at B2→B3) — rigor
without gate proliferation.

**Operating modes:** Gate mode (full review at transitions) vs. Sprint mode (autonomous on
the pre-committed plan). Risk-tiered: data-integrity = hard stop; methodology/cosmetic = async
(automated unit-test tier + diff-based audit). Speculative discovery execution on un-cleared
features **declined** (premature result visibility > idle compute in a discovery-first study).

**Marginal-sensitivity discipline (critical):** the sensitivity studies (targets, controls,
universes, characterizations) themselves multiply the search space, fighting the family-FDR
correction. So every design axis is varied **one at a time vs. pre-committed defaults, never a
full grid**; multi-target = a primary target + robustness labels, not co-equal discovery.

**Pre-commitment & provenance:** every consequential decision committed to GitHub before
implementation (timestamp = proof); reused production code tier-classified A/B/C in
`code_provenance`; hypotheses sealed until B3.

**DISCOVERY-AGENT DIRECTIVE (review M-6):** the sealed-hypothesis plaintexts under
`research/hypotheses/` are BLINDING material, not just tamper-proofing. Any Claude agent or human
doing discovery work (Phases 0–A4) MUST NOT open, grep, or ingest those files — reading one
contaminates that session for discovery (priors would steer feature/finding selection). Only the
IDs + SHA-256 hashes in `research/hypothesis_commitments.md` are safe to read before B3. **Action
for Scott:** move the plaintexts to an encrypted / out-of-agent-context archive until B3; keep only
IDs + hashes in the tree.

---

## 12. Pre-committed early experiments (go/no-go, run at the pilot / early A1–A3, BEFORE full compute)
These treat each major assumption as a falsifiable sub-study. Each is a *marginal* sensitivity
(one axis at a time).
1. **Target stationarity / transfer test** — train on an early window, test on a later one;
   run separately for emotional vs. structural features (the invariance test). If it doesn't
   transfer, switch to regime-conditional discovery as primary.
2. **Trough-vs-breakout anchoring** — compare trough-anchored vs. breakout/consolidation-exit
   move definitions on OOS AUC, top-decile return, lead time, capacity. Change the production
   anchor if breakout wins, even though the trough framework is elegant. *(Most important for
   how the user actually trades.)*
3. **Universe-definition sensitivity** — index-only vs. pre-index-extension vs. exchange-listed
   liquid; report whether findings are index-only artifacts. Be explicit the population is
   "future winners among already-institutional names."
4. **Multiple significance definitions** — percentile / raw / ATR-adjusted / benchmark-relative
   / within-regime; confirm findings aren't artifacts of one definition.
5. **Multiple control constructions** — minimal / liquidity / volatility / momentum /
   propensity-score / random-universe; keep only findings robust across them.
6. **Continuous vs. discrete characterization, co-equal** — retain clusters only if they beat
   continuous descriptors OOS.
7. **True lockbox** — a final period never examined until the end (bounds researcher DoF that
   FDR doesn't cover).

---

## 13. SNOWBALL-RISK REGISTER (ranked; challenge the ranking)
Where an early, error-throwing-silent mistake propagates through everything or wastes a big run.
Ranking revised 2026-06-21: **researcher degrees of freedom moved #10 → #7** — the feature net
is now wide enough (volume/base/RS/group/breadth/weekly/float/earnings families) that hidden
selection pressure outranks several implementation risks. The feature net is **frozen** pending
real data (§ note below); no further expansion before the Gate 0.5 pilot.
1. **Target non-stationarity (premise risk).** If "great winner setup" isn't a stable
   phenomenon, a universal model is mud. Mitigated by making regime a discovery axis + the
   transfer test (#12.1) as an early go/no-go. *Biggest risk; conceptual, not a bug.*
2. **Trough-vs-breakout anchoring.** The move definition may measure the setup at the wrong
   reference point vs. how the stock is traded; everything downstream inherits it. Mitigated by
   #12.2. *Intersects the user's actual methodology.*
3. **Norgate index-membership accuracy.** The universe *is* membership; wrong constituents/
   dates silently describe the wrong universe (no error thrown). Mitigated by Step-0 coverage
   verifier, assetid mapping, cross-validation — but correctness vs. ground truth is hard.
4. **Data-quality corruption → phantom moves.** Corrupted adjusted_close manufactures fake
   moves. Mitigated by the QC sweep + actually-traded-bars rule (coverage is the risk).
5. **Detector scale set + percentile cutoff.** Define the population; a poor choice mis-shapes
   everything. Pre-committed (good for bias) but locked for a run; robustness scales + pilot
   pre-check mitigate.
6. **`available_date` correctness.** Wrong filing dates = invisible look-ahead. The CHECK
   enforces the rule, not the dates' correctness.
7. **Researcher degrees of freedom (raised from #10).** The now-wide feature net × lookbacks ×
   scales × targets × controls × regimes × models creates hidden selection pressure that
   exceeds some implementation risks. Defense: family-level FDR, the true lockbox, the
   marginal-sensitivity discipline, negative controls, **and a frozen feature net** (no
   expansion during discovery). The brake on comprehensiveness is now itself a control.
8. **K (forward window).** Defines production labels; mislabeling propagates. From decay +
   sensitivity in B2.
9. **Multi-scale dependence / inflated N.** Overlapping moves overstate significance if
   ticker-clustered inference isn't applied everywhere; family-FDR + marginal-sensitivity
   discipline help.
10. **Failed-lookalike / matched-control design.** No ground truth; findings can be matching
    artifacts, and the negatives must include configuration-matched failures (the trend
    discriminator). Mitigated by multiple control constructions (#12.5).
11. **Compute cost of late-discovered bugs.** A bug found after a multi-day full-universe run
    (esp. #3/#4/#6, which throw no error) is expensive — the reason Gate 0.5 (pilot) and the
    negative-control harness exist: break the pipeline cheap, first.

**Feature net FROZEN (2026-06-21).** Comprehensiveness has reached the point of diminishing
returns vs. overfitting pressure (per external review). The feature catalog is closed pending
real data: the A2 pre-commit fixes the final list, and no features are added during discovery.
Further capability questions wait for the Gate 0.5 pilot. This converts "stop expanding" from
guidance into an enforced constraint and is itself a researcher-DoF control.

---

## 14. Implementation status
**[BUILT] (~230 tests, hardened over three four-auditor review passes):** the full method library
— indicators, MFE + ATR detectors, clustering + stability + resolve + segmentation, labeling,
matched controls, feature library + generic bank + provenance + matrix + collinearity, univariate
(now ticker-cluster-robust), neutralization (per-date), mutual info, decay, ML bake-off (capped
SVC), calibration + decay monitor, findings hierarchy (Benjamini–Bogomolov), backtest + capacity
(per-date deciles), Monte Carlo, breadth/context, walk-forward, stats, PIT harness, negative
controls (learned null bands), research-path FDR + deflated-Sharpe; **move CLASSIFICATION catalog**
(rich characterization + PIT inception context + base/stage + queryable JSONB `gws.moves` +
`MoveQuery` + persistence + audits); **universe-eligibility builder**; **exclusion-consuming
detector driver**; **entry-point / trough-vs-breakout instrument** (stop-conditioned, §12.2);
**theme-own-move**; two calibration harnesses (modeled + detector-derived null) + a scaling harness
+ **an end-to-end synthetic integration harness** (recovers a planted signal, null-safe); Norgate
ingest / adjusted-backfill / sweep / completeness-audit / assert-adjustment-fresh scripts.
**[SCHEMA]:** all `gws` tables + persistence contracts (moves catalog now populated by the writer).
**[FORWARD]:** fundamental feature builder; regime-conditioned analysis; scoring/Pass-B assembly;
the production orchestrator wiring Phase-0→A3 on the workstation; all real-data runs.

**Next real step (blocked on backfill + workstation):** Norgate membership ingest → Phase 0 →
Gate 0.5 pilot (with the early experiments §12 as the first true test of the regime/invariance
thesis) → full pipeline under the gates.

**Gate 0.5 exit artifact (required, per final external review):** a written go/no-go memo
answering *"Is the study learning a transferable winner setup, or merely rediscovering
regime-specific historical artifacts?"* — evidenced by the transfer/stationarity experiment
(§12.1) run on the pilot. Scott signs this memo before any full-universe compute. This is the
single most important checkpoint in the study: it decides whether universal discovery is
viable or whether the work must proceed regime-conditionally.

---

*Kaizen Alpha Research · Greatest Winners Study · master design (auditor framework V11). The
most important risks are conceptual (target stability, move anchoring), not execution. Contains
no analytical results.*
