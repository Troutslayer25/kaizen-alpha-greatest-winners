# B-anchor-3 — Point-of-Strength Experiment: Pre-Committed Specification (DRAFT for Scott)

**Status:** DRAFT — awaiting Scott's signature. NOTHING below runs until signed.
**Position:** the study's load-bearing tradeability gate (Cell C review + Scott's
2026-07-24 intent correction). The rewind (W2′) established that moves telegraph a modest
signature while being born; THIS experiment decides whether anything separates winners
from losers **at the pivot — the moment Scott actually buys**. Its outcome drives
continue-reframed vs stop.

> Commit timestamp = proof: every parameter below is frozen BEFORE any anchor-event query
> runs. Rationales are practitioner-literature-based (O'Neil/Minervini/M&K house skills),
> chosen for outcome-independence — no number below was fit to GWS data.

## Pre-Spec Exploration Disclosure
No breakout/anchor-event query has been run against gws or ka_history. The only inputs to
this spec are the Cell C rulings, the pilot catalog counts already on the record, and the
practitioner corpus. The W2′ rewind used trough anchors only.

## 1. Anchor event (the pivot) — frozen definition
A bar **B** for ticker T is a **breakout event** iff (all on the hash-guarded cleaned
series, pre-lockbox, ≥252 bars history, bar data-valid):
- **Pivot clearance:** close(B) > max(high) over the base window **[B−65, B−6]** — it
  clears a ~3-month range that stood untouched for ≥5 bars. (65 bars ≈ 13 weeks; O'Neil
  minimum base lengths are 5–7 weeks, most sound bases are 2–4 months; 5-bar standoff
  prevents same-week pivot churn.)
- **Consolidation tightness:** (max(high) − min(low)) / max(high) over [B−65, B−6]
  ≤ **35%**. (Correction depth: sound bases 10–35% per the base-analysis corpus; >35% is
  a broken structure, not a base.)
- **Volume expansion:** volume(B) ≥ **1.5 ×** ADV50(B−1). (M&K buyable-gap-up floor;
  O'Neil breakout-volume convention ≥40–50% above average.)
- **De-dup:** one event per ticker per 21 bars (first bar wins).
- Universe: the 250 stratified pilot names (adversarial 50 excluded from all metrics, run
  as pipeline stress only).

*Labeled robustness variants (one axis at a time, reported alongside, never substituted):*
tightness 25% / 45%; volume 1.25× / 2.0×; base window 40 / 90 bars.

## 2. Outcome label — frozen definition
Entry = close(B). From B forward:
- **WINNER:** MFE reaches **≥ +20%** above entry BEFORE close < entry − **2 × ATR21(B)**,
  within **H = 126 bars**. (+20% = the study's ratified meaningful-move floor; 2×ATR ≈
  the 7–8% O'Neil stop on a typical liquid growth name; H = 6 months.)
- **FAILED:** the stop level prints first.
- **UNRESOLVED:** neither within H, or the series ends/delists inside H without either —
  excluded from the primary contrast, count reported (silent-cap rule).
*Robustness labels:* +25% / fixed −7% stop; H = 63.
*Secondary continuous outcomes (reported, not gated):* forward MFE, MAE, MFE/MAE,
time-to-resolution.

## 3. The contrast
**Winners vs FAILED breakouts from the identical entry rule** — configuration-matched by
construction (same pivot geometry requirements). Reported diagnostics: era balance,
delisted share both arms, tightness/liquidity distributions both arms (residual matching
applied only if a diagnostic shows gross imbalance, as a labeled robustness line, never
silently).

## 4. Features
The frozen price/volume net + generic bank, measured **at B−1** (the last bar before
entry — nothing from B itself or later). Labeled secondary views at B−5 and B−21
(pre-pivot posture). Location family included here — at a pivot, distance-from-high is
genuine setup posture, not label echo; the de-leak control (below) adjudicates.

## 5. Harness (all pre-committed)
- Shuffle-null band (25 reps) — chance reference.
- **De-leak: within-ticker shift@5** (integrity-vindicated control; breakout events are
  sparse/non-overlapping so its assumptions hold here). Must collapse into the shuffle
  band for the frame to be declared clean.
- Run-preserving cyclic-roll band (50 reps) — autocorrelation-honest null.
- Univariate: ticker-clustered (BH-FDR); pooled AUC: standardized logistic, era-ordered
  70/30 OOS (auc_fit_score); per-era AUCs reported (pre1990/1990s/2000s/2010s).
- Seed 20260719. All offsets/variants publish together — no cherry-picking.

## 6. Decision matrix (Scott signs the cell after results)
| Cell | Condition | Pre-committed recommendation |
|---|---|---|
| P-A | de-leak clean AND AUC(B−1, OOS) > shuffle_hi + 0.05 AND primary + majority of robustness variants agree in direction | **Setup signature EXISTS at the tradeable anchor** → proceed to Gate 0→A1 re-review with the full evidence stack; A1 discovery re-frames around pivot events |
| P-B | de-leak clean AND AUC in (shuffle_hi, shuffle_hi+0.05] | Life support — signature too weak to carry the study alone; Scott decides scope (e.g., full-universe power test as the single next step) |
| P-C | de-leak clean AND AUC ≤ shuffle_hi | **No separation where it matters.** Winners and failed breakouts are indistinguishable at entry on this net → recommend STOP or radical rescope (Scott rules) |
| P-D | de-leak control does NOT collapse | Frame defect → fix-and-re-run path (Decision-D class), no reading issued |

Base-rate note: the winner rate among breakout events is itself a headline deliverable
(the "how often does a textbook breakout work" number, per era), whatever the cell.

## 7. Runtime & compute scope
Pilot-scale only (~250 names, expected O(10³–10⁴) events); minutes on this box. No
full-universe compute regardless of outcome until the Gate 0→A1 re-review clears.

---

**Scott's signature (spec freeze):** ____________  Date: ________
*Any post-signature change is a dated addendum; results never alter this spec.*
