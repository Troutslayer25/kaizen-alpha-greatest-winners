# Cell C Premise-Level Review — Verbatim Rulings (2026-07-24)

Three independent agents on the T2 settling FAIL. Synthesis in CELL_C_SYNTHESIS.md.
The integrity referee's synthetic calibration scripts are preserved alongside
(calib_shift_control.py, calib_remedy.py).

---

## 1. ka-premise (lead) — RECOMMENDATION: pause-for-B3

Ruling 1: B-anchor-1 ruled VOID (control asks an easier backward question — retrodiction
of a just-happened trough; the shift swaps a hard forward task for an easy backward one);
corrected controls proposed (run-length-preserving block permutation as primary band;
far-forward bar shift ≥3K as secondary); noted the points query lacks ORDER BY (any redo
must sort by (ticker_id, as_of_index) and assert it). Honest ceiling: a clean re-run only
clears the leakage snowball — it says nothing about tradeability or stationarity.
[NOTE: Ruling 1's "control void" reading was subsequently OVERRULED by the integrity
referee's synthetic proof — see ruling 3 below and CELL_C_SYNTHESIS. The ORDER BY find and
the block-permutation band survive as adopted improvements.]

Ruling 2: B-anchor-2 = (b) wounded, not clean: (i) the de-anchored structural arm
(price_to_ma + ma_compression) no longer measures "structural" in the thesis's sense —
ma_compression is the thesis's own flagship emotional concept (volatility contraction =
anticipation) filed under moving_average→structural; the partition is contestable at
exactly the surviving features; (ii) 61-vs-5 raw-feature arms violate the addendum's own
concept-level mandate; (iii) no permutation reference on the differential. STRONG form of
emotional invariance has zero pilot support and mild evidence against → demote from
organizing principle to open, probably-false question. Honest reframe: regime-conditional
WITHOUT invariance — the durable §1 core (regime as first-class axis, regime-analogy at
deployment) survives independently; invariance was only the proposed mechanism for
cross-regime generalization.

Ruling 3: B-anchor-3 spec (freeze before running): anchor = consolidation-exit via
Method-8/base machinery (pre-commit exact range lookback, tightness threshold, volume
multiple, min base length); primary label = forward MFE ≥ X%/Y·ATR before ≤Z·ATR trail
within horizon H (thresholds fit on early block only); negatives = CONFIGURATION-MATCHED
FAILED BREAKOUTS (same entry rule, stopped out) — the tradeable question a trough frame
cannot ask; features strictly at/before the breakout bar; corrected controls; report
across trail_2/6/15. KILLS the premise: real AUC fails to clear the block-permutation band
vs matched failed breakouts. REVIVES: clears materially + far-shift collapses + holds
across scales.

Snowball re-rank: anchor #2→#1 (materialized); non-stationarity #1→#2 (narrowed: broad
regime-dependence if anything SUPPORTED, the emotion-constant mechanism is the part
looking false); NEW #3 validation-instrument mis-specification to the frame; DoF #7→#4;
failed-lookalike design #10→#5. The one thing that most threatens the study: no
measurable PIT separation at the moment you can actually act — if winners vs matched
failed breakouts are indistinguishable at the pivot, nothing rescues it. Credit: the
governance worked — the machinery caught a contaminated 0.9-AUC headline before full
compute; it is the invariance STORY the evidence does not support, not the machinery.

## 2. ka-quant — VERDICT: instrument-artifact reading; premise UNSETTLED

F1: shift k=5 = 25 bars; window overlap at that lag = 0 (windows disjoint; the "75%" is
lag-1). Shifted labels ~independent of true (P(agree) ≈ p²+(1−p)² = 0.671). Therefore
0.898 cannot be "shifted≈true leaking through" — only mechanism is backward features
detecting the past-trough condition (dist_from_low/range_position/price_to_ma).
0.898 > 0.753 expected (past is in the feature window; future is not). What 0.898
measures: backward feature skill at recognizing a recent trough — an upper reference, not
a null. [Interpretive conclusion "gate structurally impossible on this frame" was
sharpened by the integrity synthetic: impossible for feature sets CONTAINING the anchor
family; clean non-anchored sets DO collapse.]

F2 control table: far-forward bar shift ≥2-3K = clean leak gate (collapses under both
artifact and genuine K-horizon signal); block-permutation-of-runs = autocorrelation-honest
null band (calibrator, not gate); cross-ticker same-date swap = date-composition
decomposer. None alone separates anchor from genuine pre-trough signal.

F3 decomposition of forward 0.753: 0.500→0.577 = date/era composition
(permute-within-date); +0.176 name-specific, large unknown share = decline-autocorrelation
/ trough proximity; 0.914−0.753 ≈ 0.16 = pure definitional (at-trough) component. Cheapest
genuine-signal estimator: AUC on positives lead∈[5,20] vs negatives ≥60 bars from any
trough BOTH directions — positives selectable from setup_labels (lead_time persisted);
clean negatives REQUIRE a gws.moves join (setup_labels label=0 rows can sit 1 bar after a
past trough — contaminated).

F4: 0/12 confounded — ratio not dimension-normalized; 61-feature arm overfits in-era
(inflated denominator) and degrades cross-era (deflated numerator); rank-2 collinear arm
transfers stably by construction (0.967 partly = "5 collinear features generalize"). Fair
test: per-concept ratios (rank test), emotional subsampled to matched dimensionality
(distribution over seeds), dimension-aware regularization, report effective rank.

F5 experiment set: E1 corrected leak gate; E2 lead-time-restricted AUC + T-21/T-63 offset
collapse (decision matrix: ≤0.577 → premise AGAINST; 0.577–0.63 life support; materially
above → alive); E3 dimension-fair transfer (only if E1+E2 leave signal); E4 = run E1–E3 on
the B-anchor-3 point-of-strength frame (sparse, non-overlapping labels — the pathology
largely disappears; converts the question to the decision-relevant one). Sequence:
E4 frame → E1+E2 → E3.

## 3. ka-research-integrity — VERDICT: FAIL-stands; recalibration NOT legitimate; re-scoped re-run legitimate under discipline

One line: the shift control is NOT mis-designed — on synthetic known-clean signal it
collapses exactly as required; the analyst's "structurally incapable of collapsing"
hypothesis is FALSIFIED — but B-anchor-1 as-coded tests de-leak on a feature set that
INCLUDES the definitionally-bidirectional anchor family, so the FAIL is real yet
mis-scoped. HALT stands; the fix is a re-scoped re-run, not a new control.

Calibration experiment (real detector + real control + real scorer; synthetic frames
sample_every=5, K=20):

| Feature set | real | shuffle hi | shift@5 | shift@12 | shift@20 |
|---|---|---|---|---|---|
| clean forward ONLY | 0.728 | 0.504 | **0.519** | 0.502 | 0.502 |
| location/anchor ONLY | 0.626 | 0.503 | **0.705** | — | — |
| clean + location | 0.746 | 0.504 | **0.710** | 0.502 | 0.503 |
| REMEDY: location removed | 0.729 | 0.504 | **0.519** | — | — |
| pure noise | 0.500 | 0.506 | 0.498 | 0.498 | 0.495 |
| real data (reference) | 0.753 | 0.503 | 0.898 | — | — |

Label autocorrelation: lag-1 = 0.694; lag-5 (shift distance) = −0.069; lag-12 ≈ 0.
Clean signal COLLAPSES under k=5 (there is genuinely nothing to predict at that lag);
0.898 is the control CORRECTLY FIRING on the anchor family; removing the family restores
collapse. If the control were broken, clean-only would have scored high — it did not.

Discipline for replacing a failed pre-committed bar: (1) the defect must be demonstrated
on ground truth INDEPENDENT of the failing number (known-clean false-positive or
known-dirty false-negative) — that predicate FAILED here; (2) the FAIL is preserved
verbatim forever; refinements are dated addenda on top; (3) Claude never rules — Scott
signs, refinements committed BEFORE running; (4) a recalibration justified by the very
data that failed is inadmissible.

Replacement-control evaluation: shift ≥3K collapses EVERYTHING including anchors —
strictly weaker, reject as replacement (diagnostic only; the analyst's "k >> overlap"
instinct is wrong — k=5 is exactly the useful lag where label autocorrelation ≈ 0);
block permutation = has_signal null band, leak-insensitive to the anchor channel (keep as
complement); cross-ticker swap = composition decomposer. The genuinely
leak-sensitive-yet-overlap-insensitive move: shift@5 on the ANCHOR-REMOVED feature set
(proven 0.710 → 0.519).

B-anchor-2: not robust (arm asymmetry biases the ratio toward the poverty-stable small
arm; the addendum's concept-level rule was not applied — non-compliant). Spec-vs-run
drift: seed/K/frame/12-pairs compliant; era upper bound relies on upstream lockbox
truncation — add an explicit <2022-01-01 cap and confirm setup_labels max date; the
mandated trail_2/6/15 scale-invariance robustness label WAS NOT PRODUCED (non-compliant).

Directed actions: (1) do not redesign the shift control; (2) re-run B-anchor-1 on the
location-residualized set, pre-committed with the synthetic proof attached, original FAIL
on the record — collapse → leak-free non-anchored forward edge exists; stays high → the
forward edge is irreducibly anchor and the premise is dead on this frame; (3) redo
B-anchor-2 at matched effective dimensionality; (4) produce the scale-invariance label;
(5) add the era cap; (6) B-anchor-3 as the independent decisive exhibit.
