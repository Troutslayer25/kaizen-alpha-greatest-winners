# Design Note — Market-Context (Regime) Inputs

**Status:** DESIGN NOTE (2026-06-21). The swept breadth-MA surface (below) is a committed
design decision, built into `gws/regime/breadth.py`. The broader candidate-input list is a
working set to be finalized when the market-context workstream is pre-committed. No analytical
work has begun.

---

## Principle: neutral *measurements*, not frameworks

Market-context inputs are **measurements of the environment** (volatility, breadth, credit,
correlation, trend) — never a practitioner's *rule* about what they mean. Measurements are
legitimate discovery inputs; named timing *frameworks* (IBD Market School / FTD, WoO, DMTS,
"VIX/SPY divergence signals a top") are sealed external frameworks, consulted only at B3.
The same raw series can split: the VIX-vs-SPY *residual* is a neutral feature; the *rule*
about the divergence is a sealed framework. Context inputs travel with each move as features,
are never a discovery-phase filter, and their relationship to outcomes is discovered, not
asserted.

## Availability tiers (matters because the regime thesis needs deep history)

- **Deep-history (1950→, price-derived):** breadth, realized volatility, cross-sectional
  correlation/dispersion, index trend/extension, leadership/rotation ratios, curve slope,
  copper/gold. These carry the deep-history regime work.
- **Primary-window (2010+ / from each effective start date):** VIX family (implied vol, term
  structure, VVIX, vol-risk-premium), implied correlation (COR1M/3M), HY credit spreads, MOVE.
  Mostly *orthogonal* to price features (good — reduces the regime-vs-stock-feature circularity).
- **Deployment-only / PIT-hazardous:** survey sentiment, margin debt, fund flows (lagged/
  revised). Use only over validatable history; flag any pure-overlay use as discretionary.

Effective start dates per input are confirmed by the Phase 0 audit.

## COMMITTED: swept breadth-MA surface ("FOMO indicator" generalized)

Built into `compute_breadth` (`gws/regime/breadth.py`). Decision and rationale:

- Compute **% of the eligible universe above the N-day MA across a SWEEP of N**
  (`SWEEP_PERIODS = 5, 8, 10, 13, 21, 50, 100, 200`) rather than hardcoding the named
  "% above 5-day MA" (the FOMO indicator). Mirrors the stock-level MA-sweep decision
  (`moving_average_discovery.md`): let the data reveal which horizon of participation leads,
  rather than asserting one.
- **Analyze as a response curve** (signal vs MA length), not as N independent collinear
  features (adjacent horizons are near-identical). Find the peak(s), per regime.
- **Both tails are informative:** high % = froth/FOMO, low % = capitulation/washout. Short
  horizons behave like a mean-reverting oscillator (informative at extremes); long horizons
  behave like a regime/level (bull/bear health). The decay/lead-lag analysis discovers which
  horizon *leads* momentum change vs. merely *describes* the current state.
- **Breadth term structure:** the spread between short- and long-horizon breadth
  (`breadth_spread_5_200`) is itself a measurement — fast breadth rolling over while slow
  breadth holds is a candidate *leading-divergence* of trend-momentum change. Captured as a
  continuous gap, never a signal.
- Price-derived → **deep-history computable → a full-study input**, not an overlay.
- Discovery-first: if the short end wins, it independently *confirms* the FOMO concept; if a
  different horizon wins, that is novel. EMA variants are part of the swept family to test at
  the analysis stage.

## Candidate input set (working list — to be pre-committed with the market-context spec)

Breadth (deep-hx): % above swept MA surface [committed], net new highs−lows, A/D + McClellan,
% within X% of 52w high, up/down volume ratio, % outperforming the index.
Volatility: realized vol + percentile [deep-hx]; VIX, term structure, VVIX, vol-risk-premium
[recent, orthogonal]; downside/upside semivariance [deep-hx].
Correlation/dispersion: implied correlation COR1M/3M [recent]; realized cross-sectional
correlation, return dispersion, index-return concentration [deep-hx, orthogonal].
Credit/funding: HY OAS, HY−IG quality spread, HYG/LQD trend [recent, orthogonal]; Treasury
curve slope [deep-hx, orthogonal]; TED/LIBOR-OIS, MOVE [limited].
Trend/extension: index vs long MA (trend anchor), distance from 200d, drawdown-from-high,
time-since-new-high [deep-hx].
Leadership/rotation: small/large, high/low beta, cyclicals/defensives, growth/value,
equal-weight vs cap-weight [deep-hx].
Cross-asset: copper/gold, gold vs equities, dollar trend, stock/bond correlation regime.
Divergences-as-measurements: price-vs-breadth gap, VIX-vs-SPY residual (continuous, neutral).

Sentiment/positioning (PIT-hazardous): put/call [ok]; AAII/NAAIM/II surveys, margin debt,
fund flows [lagged/revised — strict `available_date` discipline].
