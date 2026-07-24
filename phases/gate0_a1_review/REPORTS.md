# Gate 0→A1 Review — Verbatim Auditor Reports (2026-07-24)

Five independent agents, launched in parallel against commit `f2d9492` + the live pilot DB.
Reports reproduced verbatim from each agent's final output. Synthesis in SYNTHESIS.md.

---

## 1. ka-premise — VERDICT: HALT

Ranked findings (most damaging first):

**1. The FOR reading, F1, and F2 are not three findings — they are one artifact seen three
times.** THESIS_CLASS maps structural = location + moving_average + group_strength; the
location family is dist_from_high/dist_from_low/range_position — dist_from_low is precisely
the variable F2 names as the definitional leak. The shift control (0.832) shows ~80% of the
real model's above-chance discrimination survives destroying label timing. Cases are
trough-anchored; the structural class is led by "how close is price to its recent low";
that separates troughs from controls trivially and transfers across eras trivially because
price geometry is era-invariant. Structural sign-agreement 1.00 and the absent differential
follow deductively. F1 is uninformative about the thesis — the test never isolated the
thesis from the anchor. Design change that settles it: re-run the transfer test on the
production frame (setup_labels, 201,446 forward-labeled points) — features at the point's
own date predicting a FUTURE trough, so dist_from_low cannot mechanically encode the label.
One-day change on data that already exists.

**2. The instrument that ran is the confounded one the team already built a replacement
for.** gws/regime/transfer_test.py's own docstring says the earlier approach "confounded
this three ways" and fixes them: symmetric normalization, the transfer RATIO
(out-of-era skill ÷ in-era skill), and a distribution over ≥3 era pairs with the decision
rule invariance_supported (emotional ratio > structural in a majority of ≥3 pairs). None of
it ran — run_gate05_transfer.py uses a single early→late split, raw cross-era AUC, and
Cohen's-d sign agreement. The pilot pre-commit specified the cruder metrics, silently
downgrading the instrument below the master design's own standard. With min_pairs=3 and one
transition tested, invariance_supported returns supported=False for lack of pairs alone —
F1 "no differential" is structurally guaranteed by the test that was run.

**3. The pre-committed decision matrix maps this pilot to Cell D or C — not A.** The
harness returned passes:false / leak_free:false; checklist item 5 is failed by the study's
own code; the matrix says checklist failed → Cell D (fix, re-run, no memo, no gate
progress). Alternatively, if the leak is definitional-not-a-bug, "transfer FOR" cannot be
asserted on clean signal → at best MIXED → B or C, never A. Cell A was reached by routing a
code-level FAIL into a narrative finding and reading raw anchor-inflated AUCs as FOR. The
anchor experiment is a PRECONDITION for interpreting the transfer result, not a follow-on.

**4. Falsifiable bars for the A1 anchor experiment:** B-anchor-1 (de-leak): on the
setup_labels frame the shift control must fall inside the shuffle band (≤~0.52) while the
real model stays materially above. If still ~0.83, the signal is geometry and the premise
is dead regardless of anchor. B-anchor-2: invariance_supported over ≥3 era pairs with
dist_from_low/high/range_position removed or residualized from the structural arm —
emotional > structural in a majority. B-anchor-3: breakout-anchored labels yield OOS
top-decile forward reward/risk comparable to trough-anchored with positive lead time at a
point of strength. If B-anchor-1 fails → HALT the universal premise. If it passes but
B-anchor-2 fails → correct cell is B.

**5. Premise-level risks being baked into A1:** $SPX price-only large-cap benchmark vs an
all-listed deep-history universe confounds the herding/leadership family with the size
factor and injects dividend drag — inside the one family the thesis most wants invariant
(check: equal-weight all-listed benchmark over the overlap). K=20 with 21% positive base
rate is a frequent-geometry target, not a rare-winner target (check: sweep K). trail_6 was
runtime-chosen and its ratification bundled into the gate signature. The move taxonomy did
not form (27 clusters/35% noise/ARI 0.710/tie-break) — threatens both cells; Cell B needs
stable per-regime taxonomies, strictly harder.

**Snowball register re-rank:** anchor risk #2→#1 (materialized, 0.832); non-stationarity
#1→#2 (unmeasurable until #1 cleared); NEW #3 instrument/pre-commit drift (governance);
trail_6 "pre-committed" claim contradicted.

**The one thing that most threatens the study:** the label is trough-proximity geometry and
every result so far is the features reconstructing that geometry. If the shift control does
not collapse on the forward frame, the 0.91 AUC, the transfer FOR, the absent differential,
and 80/92 are all the same artifact.

**Credit:** the harness caught its own contamination and the memo published it; the
lockbox, sealed vault, and negative-control machinery are better pre-registration than most
institutional research. The design's instruments returned a stop signal; the gate signature
drove past it. Fix = run the de-confounded instruments already built, on the clean frame
already populated, BEFORE Cell A is honored.

**VERDICT: HALT** — matrix maps to Cell D (passes:false); transfer FOR rests on AUCs that
are ~80% anchor geometry measured by the crude single-split instrument transfer_test.py was
written to replace. Before Gate 0→A1: (1) transfer on setup_labels frame, shift control
must fall inside shuffle band; (2) invariance_supported over ≥3 pairs, anchor variables
residualized; (3) RS features vs breadth-appropriate benchmark; (4) unbundle
trail_6/$SPX/K=20 ratifications from the gate signature. If the shift control collapses on
the production frame → re-read as A-with-conditions; if not → Cell C.

---

## 2. ka-research-integrity — VERDICT: CLEAR-WITH-CONDITIONS

**Executive summary:** Ordering claims all confirmed from git timestamps + diffs
(783c8d8 2026-07-19 predates everything; 292524d 07:01 predates first compute 42391a5
07:22; d0b5b29 08:21 predates the transfer evidence 08:27/08:31). The pre-commitment
machinery is mechanically sound, not procedural theater. Both Decision-D fixes are genuine
correctness fixes — no free parameter dialed toward a result, both backed by regression
tests encoding the exact failure class. The load-bearing problem is the cell label: the
pre-committed harness returns passes=false and the memo reinterprets that as "PASS with
flag" to land Cell A; the PIT item was also "PASS with scope note." Two of seven checklist
items are not clean passes, yet Cell A's precondition is "checklist green."

**F-A (HIGH):** Cell A's precondition not literally met; the negative-control fail was
reinterpreted after seeing the number. Per "never resolve ambiguity by weakening a gate,"
siding with the narrow prose over the coded passes field after seeing 0.832 is the textbook
forking path. Mitigation: Scott signed A with the anchor experiment bound as mandate #1 —
the flag was escalated into a binding condition, not buried. Honest state: "A-with-mandates
that behaves like a soft B."

**F-B (HIGH, partly unlogged):** All headline evidence runs on the trough-vs-control frame
— maximally exposed to F2 — while the less-tautological forward setup_labels frame was
built and left unused. The frame choice is an unpinned fork NOT in the F4 ratification
list. Settle: re-run §12.1 + negative controls on the forward frame; if the shift control
drops materially, the FOR reading was frame-driven.

**F-C (MEDIUM):** trail_6 never pinned; agent-chosen; entire pilot keyed to it
(trail_2 n=53,544 / trail_6 n=11,803 / trail_15 n=3,246 are radically different
populations); ratified only after results seen. Settle: pin with outcome-independent
rationale or show scale-invariance across all three scales.

**F-D (LOW/CONTAINED):** the post-peek runner fix (within-baseline NaN) is contained BY
CODE STRUCTURE: the fix touches only the within-train baseline; cross-era AUC is
independent of the ordering. Caveat: no pre-fix evidence JSON was preserved. Rule going
forward: preserve pre/post artifacts for any post-peek fix.

**F-E (LOW):** both Decision-D events are real pipeline breaks. Fix 1: data-determined
factor, no free parameter. Fix 2: wiring an already-ratified Phase-0 constant ($1 floor,
"the pilot inherits whatever Phase 0 ships") into a stage that wasn't consuming it =
enforcement, not tuning; triggered by an unambiguous audit HALT. Both reduced move count
toward correctness with tests encoding the motivating failure. Clean.

**F-F forking-path ranking:** 1. trail_6 (highest); 2. discovery-frame choice (high,
unlogged); 3. same-scale significance sets (moderate); 4. $SPX benchmark (low-moderate);
5. clustering transform (low); 6. K=20 (low cell exposure); 7. D1–D3 (low).

**What the machinery gets right:** git-timestamp pre-commitment real and verified; lockbox
mechanically enforced; FROZEN_FAMILIES fail-closed (regroup diffs in git); the thesis
mapping was pre-registered AND its prediction failed and was reported honestly — the
opposite of p-hacking; the memo fabricates nothing (every number matches the JSON);
determinism proven; adversarial 50 correctly excluded from transfer metrics.

**VERDICT: CLEAR-WITH-CONDITIONS** — (1) anchor experiment as hard gate, re-run on the
forward frame; (2) pin trail_6 + frame choice pre-A1 or prove invariance; (3) carry
passes=False as an open flag, not a passed item; (4) exercise the PIT/fundamentals branch;
(5) preserve pre/post artifacts on post-peek fixes.

---

## 3. ka-pit-auditor — VERDICT: CLEAR-WITH-CONDITIONS (LOW-severity only)

**Executive summary:** The pilot data path is PIT-clean and survivorship-free. Every
load-bearing control is enforced in the persisted data, not just present in code: lockbox
holds (0 rows ≥2022-01-01 eligible or detected; max start_date 2021-12-30, max peak_date
2021-12-31); post-1990 index gate enforced (0 eligible non-member rows) while the pre-1990
all-listed rule fires (17.4M eligible pre-1990 non-member rows); membership intervals close
at historically exact dates (Enron sp500 →2001-11-29; Lehman →2008-09-16; Bear Stearns
→2008-05-30; 0 open intervals on delisted; 0 intervals past last_quoted_date); expanding
percentiles keyed on resolved_date with all 791 open moves NULL-pctile and all 67,802
resolved populated; every feature is a trailing function of close[:i+1] (per-point windows
and pandas rolling both trailing; benchmark mapped only onto each ticker's own cleaned
dates); outcome quarantine enforced at the matrix choke point. Universe delisted-dominated
at every stage (eligible 15,446 delisted vs 3,255 active; cases 78.6% delisted; controls
75.5–78.5%) — no survivor tilt reintroduced anywhere. H/L per-bar factor uses only the
bar's own values. The 46 phantom mega-moves are gone (max magnitude 82.2x, non-round).

**F1 — LOW:** completeness_audit docstring promises delisted-inclusive cross-validation but
iterates entity_ticker_map, which is populated active-only — delisted Norgate series are
never FMP-cross-validated. No pilot bias (Norgate is the preferred survivorship-free spine
and GWS detection never reads FMP), but the stated QC guarantee is unmet. Fix doc or add a
symbol+date-bounded delisted crosswalk before the full run leans on FMP reconciliation.
Test plan: Enron/Lehman/Bear entity_ids have no crosswalk row and zero completeness spans —
gap demonstrated; fix validated when they produce spans or a clean pass.

**F2 — LOW/INFO:** setup_labels right-censored at the lockbox boundary (points within K=20
bars of 2021-12-31 can't see sealed-era troughs) — conservative censoring, not leakage;
record so boundary label scarcity isn't read as signal decay.

**F3 — INFO:** lockbox rests on callers never passing unlock=True casually; all Gate 0.5
callers clean; assert backstops.

**F4 — INFO (onward to ka-practitioner/ka-quant):** 26,683 resolved moves have
max_intra_drawdown=0 — predominantly 1-bar trail_2 legs (min_duration=1); whether these are
meaningful "moves" is a characterization question for A1.

**VERDICT: CLEAR-WITH-CONDITIONS** (F1 delisted-crosswalk gap; F2 censoring note). A1 may
build on this pilot's data path.

---

## 4. ka-quant — VERDICT: CLEAR-WITH-CONDITIONS

**CRITICAL C1:** The pre-committed leak gate is failed (shifted_within_ticker=0.832 vs
shuffle hi ~0.517 → leak_free=false, passes=false) and Cell A rests on the contaminated
frame. The univariate contrast is features AT the trough bar vs a same-date bar of another
ticker; distance-from-low / range_position / dist_from_high are near-definitional of a
launch bar and persist across nearby bars → 0.832. Most of AUC 0.914 and most of the
transfer is the detector's own definition transferring trivially. Settling study
(pre-committed, must precede any A1 finding): re-run univariate + AUC on the forward
deployment frame with lead ≥5; any feature whose effect collapses to the shuffle band at
T-21/T-63 is an anchor artifact.

**CRITICAL C2:** Executed transfer instrument diverges from the frozen
PHASE_A3_TRANSFER_PRECOMMIT (2026-07-03), which mandates symmetric regime-relative
normalization, the transfer RATIO (AUC_out-0.5)/(AUC_in-0.5), ≥3 era pairs, and
invariance SUPPORTED iff emotional ratio > structural in a majority. What ran: two NESTED
raw-AUC splits with structural transferring as well or better (sign 1.00 vs 0.82) — under
the frozen rule that is NOT-supported → regime-conditional primary → Cell B. Two committed
specs, divergent verdicts, the run implemented the more permissive one. Settle: run the
frozen A3 instrument as written on the pilot before A1 closes.

**MAJOR M1:** Ticker-only clustering leaves date-level cross-sectional dependence
unmodeled (troughs concentrate on market-bottom dates: 2009, 2020). Two-way ticker×date
CR SEs (Cameron-Gelbach-Miller) or date block-bootstrap required. Top tier (range_position,
rel_strength, price_to_ma, dist_from_high; p≈1e-90..1e-192) survives any plausible
inflation; the marginal tail is fragile — expect ~80 → mid-50s-to-60s. Settle: recompute
with two-way SEs; check date concentration of the 11,536 cases.

**MAJOR M2:** Transfer sign/Spearman computed over feature rows, but 61 emotional features
≈ 10–15 independent concepts (lookback ladders) and 17 structural ≈ 4–5. Sign agreement
1.00 over 17 collinear features is close to mechanical; ρ≈0.95 inflated. Settle: collapse
to one representative per concept; permutation reference; effective-N-adjusted CI.

**MAJOR M3:** Cross-era ≈ within-era is confounded by a same-construction baseline:
same-date matching removes level/base-rate drift symmetrically in both windows, so
cross-era AUC is insensitive to feature-level non-stationarity BY DESIGN. "Minimal
degradation" is not stationarity evidence. Settle: train pre-2010 → score post-2010 on the
forward frame with absolute feature levels; that read can actually degrade.

**MAJOR M4:** 27 clusters / 35% noise at min_cluster_size=15 (~0.13% of n) is manufactured
fragmentation, and the tie-break is biased: discrete variance skips noise (tightest 65%)
while continuous PC1 bands cover 100% — discrete favored by discarding its hardest third.
Full-universe protocol to pre-commit: n-scaled min_cluster_size (e.g. max(50, 0.005n));
m-out-of-n subsampling (fixed m≈50k, many replicates, report DISTRIBUTIONS of ARI and
cluster count); coverage-penalized or same-subset tie-break; noise-share >20% forces
continuous; frozen seed/n_boot. Pilot taxonomy verdict unusable; treat as continuous.

**MINOR:** m1 univariate 80/92 includes the adversarial 50 (transfer/negative-controls
correctly exclude them; report the count stratified-only). m2 iid_ok branch is fail-closed
(good); add a full-run driver test asserting cluster_ids always passed. m3 the 2000/2010
splits are nested, not independent robustness.

**What the pilot legitimately supports:** pipeline integrity, feasibility, and the
direction/large magnitude of the strongest cross-sectional launch-bar contrasts
(pullback-in-a-leader: low range_position, high RS, near highs; |d|>1). **Cannot support:**
any universal-vs-regime verdict, any stationarity claim, any expectancy/hit-rate claim
(case-control carries no base rate), any cluster taxonomy, any feature ranking for a
ranker.

**VERDICT: CLEAR-WITH-CONDITIONS** — (1) anchor/deployment-frame experiment FIRST, features
collapsing at T-21/T-63 dropped; (2) frozen A3 instrument as written, reconciled against
the softer Gate-05 bands — if emotional does not beat structural, operative cell is B;
(3) two-way clustered univariate on stratified-only; (4) cluster protocol pre-committed,
pilot taxonomy treated as continuous; (5) universal-discovery carried as provisional into
the review until 1–2 clear.

---

## 5. ka-integration — VERDICT: HALT

**CRITICAL C1 — proven live:** matched_controls / setup_labels / entry_candidates all
REFERENCE gws.moves(move_id) with NO ACTION; move_id is SERIAL; persist_moves does
DELETE+INSERT keyed on (id_domain, ticker_id, detection_system, direction) — NOT run_id.
run_gate05_detection catches every per-ticker exception and continues. A rolled-back probe
on ticker 124578 returned the FK violation live; matched_controls references 11,466 of
11,536 trail_6 moves; move_id occupies 215000–283592 (ids 1–214,999 already burned →
reassignment on every re-detect is demonstrated). Failure scenario: any A1 re-detection is
FK-blocked per referenced ticker → swallowed as n_err → catalog silently left stale WHILE
THE FINGERPRINT STILL MATCHES (it hashes surviving rows). Fresh run_id does not escape it.
Fix before A1: teardown FK children BEFORE any detection re-run (reset script or ON DELETE
CASCADE + non-empty-children guard); a re-run with n_err>0 must refuse to pass.

**MAJOR M1 — compute claim unbacked:** detection, labels re-detect, and transfer re-detect
are serial for-loops (only feature_matrix pools); clustering = ~102 full-size HDBSCAN fits
single-threaded with the subsample_frac hatch unused; significance = one executemany of
single-row 6-col-key UPDATEs (4M at full scale). Projection at ever-eligible 18,701 (≈62×
pilot): three serial detection passes ≈15 h + serial clustering 2–8 h → ~25–30 h
single-core-bound, 63 threads idle — not "13 h serial / 1–2 h parallel." Two biggest items:
(1) detect ONCE, persist cleaned series + date vector, labels/transfer LOAD it (kills 2/3
of the 15 h and closes M3); parallelize the per-ticker passes; (2) subsample_frac +
process fan-out for the bootstrap; temp-table UPDATE…FROM for significance. After fixes
~2–3 h parallel is realistic.

**MAJOR M2 — pilot couplings fail open:** transfer's strat mask hard-codes
kind=="stratified" — on a full-universe file with no kind tags, strat is all-False and
steps 6–7 SILENTLY RUN ON ZERO ROWS. per_kind[row["kind"]] KeyErrors are swallowed
(double-counting as move+error). RUN_ID/PILOT_CSV are literals imported into all four
runners. Parameterize universe source, run_id, and adversarial-exclusion semantics.

**MAJOR M3 — date-vector drift unguarded:** detect_moves_for_ticker re-run in three stages;
nothing asserts the cleaned date vectors are identical. Drift silently NULLs
setup_labels.linked_move_id and silently shrinks transfer samples. Fix: persist per-ticker
sha256(date_vector) at detection; assert-equal at labels/transfer; refuse to compose on
mismatch (free under detect-once/reuse).

**MINOR:** m1 move_clusters PK is bare cluster_id — collides on any T4 comparative
dimension-set run (fix PK to (cluster_id, input_dimensions)). m2 full-universe control pool
= 44.3M-row single-threaded pandas load + per-date qcut (consider in-SQL ntile). m3 confirm
A1 detection scope: ever-eligible 18,701 vs 32,234 tickers in the table — 1.7× on every
serial pass.

**Credit:** persist_moves null-safety and within-run idempotency, detect_driver cleaning,
feature_matrix fail-closed guards, and significance's structural full-sample ban are
genuinely careful — failures are at the STAGE SEAMS, not inside the units.

**VERDICT: HALT** — C1 (silent stale catalog on any re-detect, proven live) is a
correctness blocker before A1; M1 means the run as-coded is ~25–30 h not 1–2 h. Clear once:
(1) FK children torn down before detection and n_err>0 refuses to pass; (2) per-ticker
passes + clustering bootstrap parallelized (ideally detect-once/reuse, closing M3);
(3) kind/RUN_ID/PILOT_CSV couplings parameterized.
