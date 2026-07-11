# Open Question — Episodic-Pivot Entry Timing: Gap vs. Pullback-to-Anchor (queued for Phase A3)

**Status:** OPEN / queued. Do not act before Phase 0 completes and the A3 entry-point
spec is written. This note records a candidate entry-timing question and *where* it
belongs. It is an **analysis / entry-signal** question, not a move-detection change —
the Phase A1 trough-anchored detector is unchanged (an EP is a point of strength, never
a local low). Directly extends `research/entry_point_discovery.md` (Method 8 expansion).

## What an "episodic pivot" is (corpus grounding)

The term **episodic pivot (EP)** is Stockbee (Pradeep Bonde) / Qullamaggie vocabulary and
does **not** appear verbatim in our trader-skill corpus. The concept it names — a stock
**gapping up on a genuine fundamental catalyst** (earnings, guidance, FDA, contract, new
product) that produces a **step-change in the story**, then continuing to trend — maps
cleanly onto two skills we already have distilled:

- **Morales & Kacher — Buyable Gap-Up (BGU)** (`morales-kacher/methodology/04_buyable_gap_ups.md`).
  Qualifying rules: bulls decisively win on *tremendous* upside volume; **gap ≥ 0.75 × 40-day
  ATR**; **volume ≥ 1.5× 50-day avg**; need not emerge from a base (can fire from a clean
  uptrend channel); **built-in sell guide = intraday low of the gap-up day**, with **2–3%
  porosity**; buyable **day-of or day-after**. Resets the seven-week clock.
- **Matt Caruso — 8-EMA Gap Pullback** (`matt-caruso/methodology/02_buy_patterns_catalog.md`,
  pattern #2). Explicit rationale: *volatility is too high AT the gap to control risk;
  short-term momentum buyers get shaken out almost immediately.* Wait for the retreat to the
  **rising 8 EMA**, buy as the stock **tightens near the line**, stop 5%. PIT features already
  named: `had_recent_gap_up_flag`, `dist_to_8ema_atr_normalized`.

So our own corpus already encodes **both sides of the exact tension this question tests**:
M&K say buy the gap (the strength persists, "too high to buy" is the crowd's mistake); Caruso
says the gap itself is un-risk-controllable and the edge is the shallow reset. This question
resolves that disagreement empirically on our winner population instead of by authority.

## The question

For stocks whose large advance was **initiated by a catalyst gap-up** (an EP), which entry
gives the better **risk-adjusted forward path** (forward MFE / forward MAE, tracked through
to exit)?

- **Entry A — buy the gap.** Enter on the EP day (open / close) or the day-after while still
  in range (BGU construction). Fast, but you accept the gap bar's full volatility as risk.
- **Entry B — pullback to the anchor.** Wait for the stock to retreat and **return to the
  initial high-volume EP close** (the gap-day closing level as the anchor), then enter on the
  reclaim/tightening. Later, tighter risk, but pays the chance the stock never comes back.

The **anchor** for Entry B is pre-committed as the **EP-day closing price** (the "initial high
volume close" in Scott's framing). Test the rising-8-EMA reference (Caruso) as a **robustness
variant**, not the primary — the EP-close anchor is a fixed price level and is PIT-cleaner than
a moving line. Do not grid both plus N others; primary anchor + one robustness variant.

## How to test it (fits Method 8, hindsight-free)

Reuse the entry-point-discovery machinery verbatim — no new methodology, just a candidate
family:

1. **Population.** From the A1 move set, subset moves whose **start window contains a
   qualifying EP** (gap ≥ 0.75 × 40-day ATR **and** volume ≥ 1.5× 50-day avg, computed PIT at
   the gap bar's close). This EP flag is a neutral feature, not a hand-drawn pattern.
2. **Candidate entries per EP move.**
   - A: EP-day close (and day-after-in-range as a variant).
   - B: first bar that trades back down to the EP close and reclaims it (the pullback-return),
     within a pre-committed lookahead window (e.g. ≤ N days; commit N in the A3 spec).
   - Include a **"no valid B"** outcome: some EPs never pull back to the anchor — that
     non-fill is itself part of B's expectancy and must NOT be dropped (survivorship /
     conditioning-on-fill bias). Score B's edge on the **full EP population**, counting
     missed entries as forgone trades, not as excluded rows.
3. **Score each candidate** by the standard A3 reward-for-risk: **reward = forward MFE** to the
   eventual peak, **risk = forward MAE** (worst drawdown before the gain), tracked **through to
   the exit rule**, so the comparison is entry-to-exit realized, not entry-to-hypothetical-top.
   Use the study's canonical exit; if an exit sensitivity is wanted, it's a separate robustness
   axis (one axis at a time).
4. **Neutralize the obvious confounds.** Factor/industry/beta neutralization (an EP is a
   momentum + volatility-expansion event; strip "it's just momentum/vol"), then ask whether
   **entry timing** carries *independent* signal beyond simply being in an EP name.
5. **Regime split.** The study's central thesis is that structural features are regime-
   dependent and behavioral ones invariant. Gap-continuation is plausibly regime-sensitive
   (EPs work in risk-on, fail in corrections). Report A-vs-B **conditional on regime**, not
   just pooled — a pooled winner that flips sign by regime is a deployment trap.

## Why this is worth queuing (not a re-litigation)

- It operationalizes the **trough-vs-breakout / point-of-strength experiment**
  (`research/regime_conditional_discovery.md` §12.2, `entry_point_discovery.md`) on the single
  most-tradeable strength entry Scott actually uses.
- The answer is **directly actionable**: it tells the eventual production entry model whether,
  for catalyst-gap names, to fire on the gap or to wait for the anchor reclaim — a real
  execution decision, not a descriptive curio.
- Both candidate anchors are **PIT-safe, close-computed, no third-party data** (same surface as
  the Caruso pattern features already scoped for `step_12`).

## Bias guards (unchanged from the rest of the study)

- Purged/embargoed walk-forward; findings-hierarchy Tier-1 tolerances; negative controls;
  `motivation` tag = `practitioner_derived` (M&K/Caruso-motivated, so it does NOT get to claim
  discovery novelty).
- **Validation ≠ agreement with M&K or Caruso.** Whether A or B wins is decided by our own
  A3/B2 statistics. Matching a framework is convergence to *report at B3*, never evidence.
- Pre-commit the EP thresholds, the anchor definition, the B lookahead window N, and the exit
  in the **A3 spec** before touching data. This note is the pre-data record; the git commit
  time is its precedence proof.

## Sequence

Phase 0 complete → A1 moves (EP flag falls out of existing gap/volume features) → A2 feature
store → **A3: subset EP moves, score A vs B candidate entries through to exit, neutralize,
regime-split** → A4 lock → B3 convergence check vs M&K BGU / Caruso 8-EMA-pullback and any
sealed priors. Entry-timing discovery is an A3 activity; framework comparison is B3 only.
