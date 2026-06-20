# Open Question — Moving-Average Family Discovery (queued for Phase A2/A3)

**Status:** OPEN / queued. Do not act before Phase 0 completes and the A2 pre-committed
spec is written. This note records *where* MA testing belongs and *how* to do it
without polluting the discovery. The MA prohibition still holds: MAs NEVER define move
boundaries (Phase A1); everything here is feature / entry-signal territory.

## The question

Which moving-average **type** (SMA vs EMA) and which **window(s)** carry *independent*
predictive signal for pre-move setups — and does the answer differ **by regime** and
**by stock** (e.g. volatility/liquidity)? Scott specifically wants short EMAs (3/5/8/10)
and EMA-vs-SMA tested, with the recognition that the best MA may not be universal.

## The reframe — characterize the response surface, don't run 60 independent tests

Extracting {SMA,EMA} × ~11 windows × several relationships yields scores of highly
collinear features. Treating each as an independent hypothesis wrecks power (BH-FDR
dilution) and muddies importance. Instead, characterize the **MA-window response
curve**: IC / effect-size as a function of window, per type. The peak(s) are the
discovered relevant windows. This handles collinearity natively and answers
"which MA" directly.

## Where each piece belongs

| Pipeline step | Role |
|---|---|
| **A2 feature extraction** | Generate the family: {SMA, EMA} × windows {3,5,8,10,13,21,30,50,100,150,200} × relationships {distance-to-MA (extension), slope, pair-compression, alignment, crossover recency}. Both types, swept windows — NOT just canonical 50/200. |
| **A3 Method 5 (decay/IC)** | The MA-window **response curve** (IC vs window), separately for SMA and EMA. Peaks = discovered windows. |
| **A3 Method 6 (regime-conditioned)** | Recompute the response curve per regime bucket → does the relevant window shift (short EMA in trends, long SMA in chop)? |
| **A3 Method 3 (ML bake-off)** | Per-stock heterogeneity via interactions (MA-window × stock volatility/liquidity); trees capture "short EMA matters for high-vol names." |
| **A3 Method 2 (neutralization)** | A surviving MA must beat factor + industry neutralization (not momentum repackaged). |
| **A3 Method 8 (entry-point)** | Short-EMA entry configurations (pullback to rising 8-EMA, etc.) tested for edge. |
| **B3 external comparison** | Compare surviving windows/types vs practitioner canon (O'Neil 50/200, Minervini, Webby 8/21). Data landing on those = confirmation; otherwise novel. |

## Bias-control notes

- MA features are tagged `practitioner_derived` in `feature_catalog.motivation`; the
  *window selection* is data-driven (the discovery-clean part). Auditor 4's A3→A4
  cross-tab will show whether MA findings dominate Tier 1.
- Current `features_price_volume.py` uses only canonical windows (20/50/150/200) — this
  must be broadened to the swept family in the A2 build, and the broadening
  pre-committed in the A2 spec, so window choice isn't a contamination vector
  (Auditor-4 lookback-window check).

## Action when the time comes

1. In the A2 pre-committed spec: declare the MA family (types, swept windows,
   relationships) and the response-curve analysis method, before extraction runs.
2. Extend `gws/phase_a2/features_price_volume.py` to emit the swept MA family.
3. Add an MA-window response-curve routine to the A3 decay analysis.
