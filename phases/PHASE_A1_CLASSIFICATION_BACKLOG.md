# Phase A1 — move-classification enrichment backlog (post-review, additive)

**Opened 2026-07-03** after the four-auditor review of the move-classification substrate. Every
item is ADDITIVE (a new descriptor/inception field or a query/DB affordance) and freeze-safe by
the module's additive contract — add the field + a JSONB key and re-characterize (cheap; no
re-detection). Bump `persist_moves.CHAR_VERSION` on any formula change. Land the high-value trader
descriptors BEFORE the first full characterization pass so the catalog answers real queries.

## Practitioner enrichments (highest value first)
- **Deep base / pivot / stage context (MC-2).** Beyond `incept_base_depth_63`: base LENGTH (weeks),
  distance to the nearest prior pivot/consolidation high at inception, tightness/VCP signature
  (successive contraction), prior-move (base-on-base) context, Weinstein stage. This is what
  distinguishes flat-base Stage-2 launch vs V-recovery vs high-tight-flag — the taxonomy Scott
  actually trades. Needs a light base detector run ≤ trough.
- **Theme's OWN move (thematic comparison).** `.tickers_in(members)` slices by a theme's members,
  but there is no theme composite move to compare against. Build a theme/sector composite series →
  characterize the theme's move → lead/lag and rs-vs-theme per member move.
- **Inception adds:** anchored-VWAP distance (from the base low / prior pivot); market-cap /
  dollar-volume / liquidity tier; sector/industry at inception (PIT — gated on the GICS-vintage
  pre-commit); 126/252-day RS and the confirmed 40/20/20/20 RS composite; RS-line-new-high flag;
  MA stack order (50>150>200); days-since-52w-low.
- **True overnight gaps from opens** (rename kept as `big_day_*` for close-to-close): add
  `overnight_gap_count`/`largest_overnight_gap` computed from `open` when the open series is loaded.

## Data-lineage follow-ups
- `run_id` / `detect_params JSONB` on `gws.moves` (records `atr_period`/`min_duration`, not just
  `scale`) so two parameter runs are distinguishable (Lineage m-10).
- Expression btree indexes on hot JSONB fields — GIN(jsonb_ops) does not serve `(bag->>k)::numeric`
  range predicates (Lineage m-3); harmless at current scale.
- The 5 step_09-style audit checks (Lineage report §): phantom-move canary (`total_pct_gain>100`),
  ≤1 open move per (ticker,scale), row-internal `descriptors->>'magnitude' ≈ total_pct_gain`,
  cross-domain span probe, per-JSONB-field null-coverage report.
- Cross-domain span translation policy via `gws.entity_ticker_map` for `completeness_audit` spans
  (FMP-keyed) consumed by a Norgate-domain detection (Lineage C-1 note).

## Compute
- Vectorized-builder integration: route `build_feature_matrix` through
  `gws.phase_a2.features_vectorized` for the proven families (needs `compute_features` family-
  selection so the per-point path skips them) — already gated on `gws.validation.feature_equality`.

## Minor
- `_json_safe` recursion / numpy-scalar `default=` handler when descriptors grow nested.
- `MoveQuery.order_by`/`select` column whitelist if the query layer ever backs an API.
- `duration_days` is a trading-bar count (document vs calendar `peak_date - start_date`).
