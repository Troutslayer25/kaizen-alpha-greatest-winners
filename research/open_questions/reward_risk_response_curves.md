# Open question — forward reward/risk response curves over volatility state and MA-extension (for the A3 entry/exit spec)

**Logged 2026-07-11.** Direction-free registration of a measurement question, to be folded into
the Phase A3 entry-point analysis pre-commit (Method 8, `research/entry_point_discovery.md`)
when that [FORWARD] spec is written (post-Gate-0.5). No instrument is built now; the feature
freeze holds — every input named below is already in the frozen A2 net or the inception
catalog. Related directional priors are sealed as h009 and h010 (hashes in
`research/hypothesis_commitments.md`); per the blinding directive, discovery agents read only
the hashes, never the plaintexts.

## The question
Method 8 already scores candidate points along each detected move by forward reward/risk
(forward MFE / forward MAE → `gws.entry_candidates`). Read that surface as RESPONSE CURVES
over two conditioning families, with BOTH tails treated as informative:

1. **Volatility state** — ATR% level and ATR deviation from the stock's own trailing baseline
   (contracted vs expanded relative to its norm). Low tail speaks to entry planning, high tail
   to exit/trim planning. No expected shape is registered here.
2. **MA-extension** — percentage distance from moving averages, using the standard swept
   horizon set (not hand-picked "key" MAs; which horizon matters is discovered, not asserted).
   Includes extension-at-inception for basing stocks (long-horizon MAs) and extension at
   points along the move (all horizons).

## Required control — the mechanical confound
Extension and volatility state both correlate with move-age and gain-so-far by construction,
and a trailing-stop-defined move gives late/extended points worse forward geometry almost
tautologically. The analysis MUST report each response curve conditional on move-age and
gain-so-far (or partial out those terms); an unconditional curve is arithmetic, not signal.
Only incremental effect beyond the mechanical component counts toward the findings hierarchy.

## Constraints already known
- Exit-side analysis is a NEW read of the entry_candidates surface, not a new detector or
  table: a point with poor forward reward/risk is a sell/trim point by definition. Detector
  unchanged; Method 8 machinery unchanged.
- Everything here is `practitioner_derived`-adjacent territory (extension sell rules exist in
  the practitioner corpus); motivation tags apply and framework convergence is reported at B3
  only, never used as validation.
- Settled-list note: pipeline-side graduated-exit backtesting falsified pyramiding, tight
  trails, and volume-confirmation exits — extension-based exits were NOT among the falsified
  set. The withdrawn ATR% screen gate (2026-05-11) concerned production screen FILTERS and
  does not constrain ATR features in discovery.
- Regime split applies as everywhere else: a pooled response curve that flips sign by regime
  is a deployment trap; report per-regime once the regime-conditioned machinery exists.
