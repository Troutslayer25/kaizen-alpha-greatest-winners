# Design Note — Regime-Conditional Discovery & the Emotional-Invariance Hypothesis

**Status:** DESIGN DECISION (2026-06-20). Captures Scott's reframing of the study's
organizing principle in response to an external critique (ChatGPT) on target
non-stationarity. To be folded into the Phase A1/A3 pre-committed specs when those phases
are reached. No analytical work has begun.

---

## The reframe

A critique correctly identified that the biggest risk to the study is not an execution bug
(survivorship, look-ahead, validation) — those are well-hardened — but the **premise**: that
a "great winner setup" is a stable, universal phenomenon across decades. It probably is not.
The antecedents of 1999 speculative momentum, 2003 recovery, 2020 liquidity-fueled growth,
and 2022 energy leadership may be genuinely different mechanisms; averaging them produces a
classifier that fits none.

**Resolution (Scott):** do not assume one universal target. Make **regime a first-class
discovery axis.** Discover the move taxonomy *per environment*, map how it morphs across eras,
and build a regime-analogy capability: "What past regime are we in now, and which move-types
worked then — are today's leaders showing that signature?" Non-stationarity becomes the thing
the study characterizes, not the thing that breaks it.

The "greatest winner" obviously moves far and fast — but its *definition within a cycle*
changes across decades and will keep changing. The study should discover, classify, and
relate those changing move-types rather than collapse them into one average.

---

## The central hypothesis — emotional invariance

Working hypothesis (to be TESTED, not assumed — discovery-first discipline applies to this
prior too): **regimes and market structure change, but human emotion does not.** The
emotional substrate of a pre-move setup (anticipation, fear, capitulation, conviction,
herding) should be more stable across eras than the structural surface (price levels,
fundamental magnitudes, sector identity, durations).

**Operationalization — split features into two classes:**
- **Behavioral / emotional (hypothesized regime-INVARIANT):** volatility contraction
  (coiling/anticipation), shakeout depth & timing (fear/capitulation — the `mae`,
  `early_smoothness`, `drawdown_timing` dims), volume surge vs. dry-up (conviction/
  participation), path smoothness (orderly accumulation vs. panic), relative-strength
  persistence (herding/leadership).
- **Structural (hypothesized regime-DEPENDENT):** absolute price levels, specific
  fundamental magnitudes, sector composition, specific durations.

**The sharp, falsifiable prediction:** emotional features TRANSFER across regimes; structural
features do not. A classifier built on emotional features in regime A should still identify
winners in regime B; one built on structural features should degrade. If confirmed, the study
has found a regime-invariant emotional signature with regime-dependent structural overlays —
the most valuable possible outcome.

**The measurement instrument is the stationarity transfer-test** (below) — the same test the
critique proposed, repurposed to confirm/deny the emotional-invariance thesis.

---

## Regime-relative normalization

To compare a 1999 setup's emotional signature with a 2021 setup's on equal footing, express
features *relative to their own era*: volatility contraction relative to that period's typical
volatility, RS relative to that regime's cross-sectional dispersion, move magnitude relative
to the period's move distribution. Regime-relative normalization strips the regime's surface
scale so the invariant substrate (if any) is visible. (Side benefit: resolves the
percentile-significance drift concern — significance defined within-period/within-regime,
not globally.)

---

## The regime-analogy engine (deployable output)

Falls out of the existing `regime_daily` workstream:
1. Characterize each date by its market-context vector (breadth, volatility, credit, trend,
   dispersion, ...).
2. At any current date, find the nearest historical analog(s) by continuous similarity (no
   forced regime buckets).
3. Surface: "in that analog, which move-types worked, and are today's leaders exhibiting that
   pre-move signature?" — presented with explicit uncertainty (few analogs → wide bands).

---

## Pre-committed early experiments (Phase A1/A3 — go/no-go diagnostics, run on the real-data
pilot BEFORE the full-scale compute)

From the critique + this reframe. These are decision gates, not just robustness checks:

1. **Target stationarity / transfer test.** Train a setup classifier on an early window
   (e.g. 2010–2014), test on a later one (e.g. 2020–2024). If it does not transfer at all,
   universal discovery is not viable → switch to regime-conditional discovery as primary.
   Run the test separately for emotional vs. structural feature sets (the invariance test).
2. **Move-definition / anchor sensitivity — trough vs. breakout.** Compare trough-anchored
   move definitions against breakout/consolidation-exit-anchored ones. Scott trades buyable
   *pivots* (O'Neil/Minervini/Webby), not bottoms; a trough-anchored study may measure the
   setup at the wrong reference point. Test which yields more tradeable, more identifiable
   setups; consider supporting both anchors.
3. **Universe-definition sensitivity.** Quantify how findings change with the index set and
   the data-validity thresholds. Be explicit that the population is "future winners *among
   already-institutional names*," not future winners in general.
4. **Multiple significance definitions.** Store and test percentile, raw return, ATR-adjusted,
   benchmark-relative, and within-regime percentile — confirm findings are not artifacts of
   one definition.
5. **Multiple control constructions.** Run several matched-control variable sets; keep only
   findings robust across them (no single control framework is "correct").
6. **Continuous vs. discrete characterization, co-equal.** Run continuous latent-factor
   characterization (e.g. factor analysis / PCA on the move-dimension manifold) as a primary
   path alongside clustering — not merely a fallback. Expect a mostly-continuous manifold.
7. **True lockbox.** Reserve a final period never examined until the very end, to bound the
   (large) researcher-degrees-of-freedom risk that BH-FDR does not cover.

---

## Implications

- **Deep history (Norgate 1950–2009) is now load-bearing**, not a nicety: a regime taxonomy
  needs enough distinct regimes, which needs decades. This raises the stakes on the Norgate
  extension's completeness and correctness.
- **Regime definition should lean on partly-exogenous factors** (credit/macro), to avoid
  defining regimes from the same price data whose move-types we then discover within them
  (circularity). Connects to the collinearity diagnostic.
- **Sample size** per regime is the binding statistical constraint; small-bucket power rules
  (provisional 50, confirmed at Gate A1→A2) apply with extra force.
- The emotional-invariance thesis is held as a hypothesis and tested, not assumed — the
  study's own discovery-first discipline applies to it.

---

## The paradox, resolved

We filter human emotion/bias OUT of our *process* precisely so we can observe market
participants' emotion IN the *data* without contaminating it. Two different emotions:
bias-elimination protects the instrument; participant emotion is the subject the instrument
measures. The two instincts — eliminate bias, capture emotion — are not in tension; the first
exists to enable the second.
