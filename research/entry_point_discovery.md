# Design Note — Entry-Point Discovery Along the Move (Phase A3, Method 8 expansion)

**Status:** DESIGN DECISION (2026-06-21). Pre-committed before any Phase A3 implementation
(timestamp = proof of precedence). Expands the existing Method 8 (entry-point analysis); the
move detector (Phase A1) is **unchanged**. No analytical work has begun.

---

## The gap this closes

The move detector anchors every move at a **trough** (a local low, at some scale). Two
consequences:
- **Pullback / dip entries are already captured.** Multi-scale detection finds the smaller
  moves nested inside a larger trend; their troughs are the pullback lows within the trend.
  Buying one of those = buying a dip to a rising trend. No change needed — they are already
  detected and feature-extracted as move start-dates.
- **Breakout / earnings-gap / MA-reclaim entries are NOT captured as anchors.** These are
  *points of strength* — by definition never local lows, at any scale — so no trough-anchored
  detector reaches them. A breakout to new highs is a point *along* a move that is itself
  anchored at a much earlier, much lower trough.

Capturing the *move* (which we do, 100%, gaps included) is not the same as flagging the
*entry*. The user trades buyable pivots (breakouts, MA crossovers, trendline breaks), not
bottoms. So the study must be able to discover low-risk entries at points of strength — which
is an **analysis** problem, not a detection problem.

## The expansion (what Method 8 now does)

For each detected move, evaluate candidate entries at points **along** the advance — not only
the pre-trough window — **including points of strength**. Score each candidate empirically:
- **Reward = forward MFE** — upside remaining from that point to the eventual peak.
- **Risk = forward MAE** — worst drawdown from that point before the gain materializes.
- **Low-risk entry = the best forward MFE/MAE (risk-adjusted forward return).** Defined from
  data; no chart pattern is pre-defined as "the entry."

Then extract the same neutral features (the `(ticker, as_of_date)` store works at any date) at
the winning entry points and discover which feature configurations predict a high forward
reward-for-risk. If the data lands on "near new highs after a quiet consolidation, on rising
volume," the breakout has been **independently rediscovered** — not asserted. If it lands on
the trough, that is an equally valid (and surprising) finding.

## Deployment discipline (hindsight-free)

Discovering the best entry within a *known* winner is hindsight-conditioned (descriptive). The
**production** entry model forward-labels arbitrary `(ticker, as_of_date)` points by their
forward reward/risk — "from here, not knowing the future, does this configuration predict a
good risk-adjusted forward path?" — exactly the construction used for the setup classifier.
This keeps it deployable and leakage-free.

## Bias guards (unchanged from the rest of the study)

- Same machinery: factor/industry neutralization (strip "it's just momentum"), purged/embargoed
  walk-forward, findings hierarchy (Tier-1 tolerances), `motivation` tagging (a breakout entry
  feature is tagged `practitioner_derived`), negative controls.
- **Validation ≠ agreement with a framework.** Whether an entry has edge is decided by our own
  statistics (A3 + B2), *never* by whether it matches CANSLIM. Using framework-agreement as
  evidence would be confirmation bias.
- **CANSLIM / sealed hypotheses opened only at B3**, after the A4 lock, to ask convergence
  (our data confirms tradition) vs. novelty (we found something tradition missed) — the
  layering goal.

## Relationship to existing items
- Operationalizes the **trough-vs-breakout experiment** (`research/regime_conditional_discovery.md`
  §12.2): scoring entries along the path directly measures whether the trough or a point of
  strength gives the better risk-adjusted entry.
- Uses the multi-scale move population from A1 as its substrate (no detector change).

## Schema implication
New table `gws.entry_candidates` (one row per candidate entry point per move) — see schema DDL.
Outputs feed the findings hierarchy / scoring like any other A3 finding.

## Sequence
A1 detect & characterize moves → A2 features → **A3 discover + statistically validate low-risk
entries along the moves** → A4 lock → B3 compare to CANSLIM/sealed hypotheses (convergence vs
novelty). Entry discovery is an A3 activity; framework comparison is B3 only.
