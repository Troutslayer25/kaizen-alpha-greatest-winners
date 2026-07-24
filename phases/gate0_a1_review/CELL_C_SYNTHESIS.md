# Cell C Premise-Level Review — Synthesis (Scott rules on every item)

**Date:** 2026-07-24. **Panel:** ka-premise (lead), ka-research-integrity, ka-quant.
Verbatim rulings in `CELL_C_RULINGS.md`. Trigger: T2 settling FAIL (`anchor_settling.json`:
B-anchor-1 shift 0.898 > real 0.753; B-anchor-2 emotional 0/12).

## The decisive fact of this review

**The integrity referee refuted the implementation agent's "control mis-designed"
hypothesis with a blind synthetic experiment** (scripts preserved; run with the study's
actual detector, control, and scorer): on planted KNOWN-CLEAN forward signal the k=5 shift
control COLLAPSES to 0.519 — the control is correctly calibrated for this frame class. On
a planted anchor (location-family) feature it fires (0.705); clean+anchor reproduces the
real signature (0.710 vs real 0.746 ≈ the live 0.898 vs 0.753); **removing the anchor
family restores the clean collapse (0.519).** Premise and quant had argued the control was
void; the synthetic proof overrules that reading. Where all three DO converge: the
mechanism is the anchor family, and the informative follow-up is anchor-removed.

**Standing consequence:** the B-anchor-1 FAIL is PRESERVED VERBATIM. It is evidence that
the pilot's forward-frame signal is substantially anchor-family-driven until the
re-scoped test says otherwise. The agent's hypothesis is on the record as refuted.

## Where all three rulings converge

1. **B-anchor-2 (0/12) is NOT valid evidence of thesis reversal** — 61-feature emotional
   arm vs 5-feature near-rank-2 structural arm mechanically favors the small arm's
   transfer ratio, and the addendum's own concept-level hygiene rule was not applied
   (a logged non-compliance). The emotional-invariance thesis is nonetheless DEMOTED from
   organizing principle to open question (zero support in any cut of the pilot).
2. **The premise is UNSETTLED — neither validated nor dead.** Honest state: real forward
   AUC 0.753, of which ~0.577 is date/era composition; the name-specific remainder is
   anchor-suspect until the re-scoped de-leak runs.
3. **B-anchor-3 (point-of-strength) is the decisive experiment** — winners vs
   configuration-matched FAILED breakouts at the pivot Scott actually trades. If nothing
   separates them there, the setup exists only in hindsight and the study stops or
   radically rescopes. Full spec in the premise ruling (freeze before running).

## The approved-if-Scott-signs work package (pilot-scale, ~1 session, pre-commit first)

- **W1 — Re-scoped B-anchor-1 (integrity's admissible follow-up):** shift@5 de-leak on the
  LOCATION-RESIDUALIZED feature set; pre-committed as a dated addendum with the synthetic
  proof attached; original FAIL untouched. Collapse → a non-anchored forward edge exists;
  stays high → the forward edge is irreducibly anchor-driven on this frame.
- **W2 — Lead-time-restricted AUC (quant E2):** positives lead∈[5,20] vs negatives ≥60
  bars from any trough (gws.moves join — setup_labels negatives alone are contaminated),
  judged vs block-permutation band and the 0.577 floor; plus T-21/T-63 feature-offset
  collapse tests. This is the cleanest de-anchored signal estimate.
- **W3 — B-anchor-2 redo at matched effective dimensionality** (one representative per
  concept, both arms; permutation reference). Only meaningful if W1/W2 leave signal.
- **W4 — Compliance items:** produce the missing trail_2/6/15 scale-invariance label;
  add an explicit <2022-01-01 era cap in the settling runner + confirm setup_labels max
  date; preserve pre/post artifacts on all of it.
- **W5 — B-anchor-3 pre-commit** (premise ruling §3 spec: consolidation-exit anchor rule,
  MFE/ATR-vs-trail label, configuration-matched failed-breakout negatives, corrected
  controls, scale-invariance) — committed before it runs; it is the gate that decides
  continue-reframed vs stop.

## Panel recommendation to Scott

**PAUSE-FOR-EVIDENCE (unanimous in effect):** no full-universe compute; demote the
invariance thesis; run W1–W4 on the pilot, pre-commit W5, and rule continue-reframed vs
stop with the de-anchored numbers in hand. The premise's kill-bar: if W1 stays high AND
W2 sits at the 0.577 composition floor AND W5's pivot test cannot separate winners from
matched failed breakouts — the core operational question has a negative answer.

*Recorded per V11: Claude first-pass synthesis; Scott's human review and signature
required. The disagreement between rulings (control void vs control correct) is resolved
in favor of the synthetic proof and preserved honestly in the verbatim record.*
