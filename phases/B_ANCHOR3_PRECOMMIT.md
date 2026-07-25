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

## 1. Anchor events (points of strength) — FOUR frozen families
*(Amended pre-signature 2026-07-25 at Scott's direction: the Caruso Swing Trading Guide /
Buy Patterns catalog defines multiple mechanizable point-of-strength types, not just the
classic base pivot. Four families are frozen below — count FIXED at four; no family added,
dropped, or re-parameterized after signature. Caruso's context gates (FOMO zone, market
trend) are deliberately NOT encoded as event gates — whether context separates winners
from failures is a DISCOVERY question, so context enters as features, not filters.)*

Common preconditions for any event bar **B**: hash-guarded cleaned series, pre-lockbox,
≥252 bars history, bar data-valid, volume(B) > 0. De-dup: one event per ticker per family
per 21 bars (first wins); the same bar may qualify for multiple families (tagged, reported).
Universe: the 250 stratified pilot names (adversarial 50 = pipeline stress only).

**Family A — Base Breakout** (O'Neil-style consolidation exit; the classic pivot):
- close(B) > max(high) over base window **[B−65, B−6]** (≈13-week range untouched ≥5 bars);
- base depth (max high − min low)/max high over [B−65, B−6] ≤ **35%**;
- volume(B) ≥ **1.5 ×** ADV50(B−1).
*Robustness (one axis at a time):* depth 25%/45%; volume 1.25×/2.0×; window 40/90 bars.

**Family B — Coil Exit** (Caruso Mini Coil; volatility contraction resolving up):
- expansion bar E: range(E) ≥ **1.5 × ATR21(E−1)**, volume(E) ≥ 1.5 × ADV50(E−1),
  close(E) in the top **40%** of E's range;
- ≥ **2** subsequent sessions trading FULLY inside E's high–low range;
- B = first bar with close(B) > high(E).
*Robustness:* inside-sessions ≥3; expansion range ≥2.0×ATR.

**Family C — Pullback Reclaim** (Caruso Failed-Breakout Pullback to the rising 21-EMA):
- a Family-A event occurred within **[B−30, B−5]**;
- post-breakout high H*; price pulled back **8–15%** from H* and traded at/below the
  **21-EMA** while the 21-EMA was rising (21-EMA(t) > 21-EMA(t−5));
- B = first bar after the touch with close(B) > max(high) over the prior 5 bars.
*Robustness:* pullback 5–12%; reclaim window prior 3 bars.

**Family D — Expectation Breaker** (Caruso Kicker; trapped sellers):
- bar R: close(R) < open(R), range(R) ≥ **1.5 × ATR21(R−1)** (a large red candle);
- B = R+1 with open(B) > **open(R)** (gap above the red candle's open).
*Robustness:* red-candle range ≥2.0×ATR; gap above high(R).

Family-native stops (Caruso: 5% flat for C; low-of-prior-bar for B; prior close for D;
2×ATR for A) run as a LABELED robustness set; the primary label (§2) is uniform across
families so outcomes are comparable.

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
**Winners vs FAILED events from the identical entry rule, per family and pooled** —
configuration-matched by construction. Primary gate (§6) evaluates **Family A**; Families
B–D publish as pre-committed co-exhibits (per-family cells, same harness); the pooled
analysis (family as a categorical feature) is a labeled secondary view. Families with
< 200 resolved events are reported as UNDERPOWERED, not silently dropped. Per-family ×
per-era win rate / MFE / MAE tables are a headline deliverable regardless of cells — this
IS the "classify moves by how they begin" catalog Scott asked for. Reported diagnostics:
era balance, delisted share both arms, tightness/liquidity distributions both arms
(residual matching only as a labeled robustness line, never silently).

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
