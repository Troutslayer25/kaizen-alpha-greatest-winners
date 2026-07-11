# Open question — transfer as a function of temporal distance (for the regime-conditioned pre-commit)

**Logged 2026-07-11.** Direction-free registration of a measurement question, to be folded into
the Phase A3 regime-conditioned analysis pre-commit when that [FORWARD] spec is written
(post-Gate-0.5). No instrument is built now; the feature freeze and Gate 0.5 sequencing are
unaffected. A related directional prior is sealed as h008 (see
`research/hypothesis_commitments.md`) — per the blinding directive, discovery agents read only
the hash, never the plaintext.

## The question
The pre-committed transfer test (master §12.1) measures ONE early-window → late-window split.
That answers "does it transfer at all?" but not the SHAPE of transfer over time. Extend it,
marginally (one axis, per the marginal-sensitivity discipline), to a transfer CURVE:

- Train on window/cycle t, test on t+k for a ladder of temporal distances k; plot OOS transfer
  (AUC / top-decile lift) vs k. Possible shapes — flat, decaying, non-monotonic — are all
  informative; no expected direction is registered here.
- Run the curve separately for the emotional vs structural feature classes (§1), so any
  distance effect can be attributed by feature class.
- Compare two deployment-facing transfer models where they disagree: (a) temporal-proximity
  weighting (calendar-time recency — PIT-clean), vs (b) similarity-matched regime analogy
  (the master-doc regime-analogy engine). Score both OOS on identical folds.

## Constraints already known
- **Cycle boundaries are hindsight-defined** (a bear is only knowable months in), so any
  production/deployment claim must be expressible in calendar time, not cycle counts. Cycle-unit
  framing is descriptive/post-hoc only.
- **Circularity guard** (master §6): cycle/era boundaries must not be derived from the same
  price data whose within-era efficacy is being measured, or must be exogenously anchored.
  Market School FTD/distribution machinery is an external framework sealed until B3 and cannot
  define eras for discovery.
- Deep history (Norgate 1950–) is load-bearing here: the k-ladder needs many distinct
  windows/cycles to have any resolution.
