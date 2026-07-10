# Phase A1 — move-classification enrichment backlog (status)

**Opened 2026-07-03** after the four-auditor review; **worked down 2026-07-03.** Items are ADDITIVE
(new descriptor/inception field or a query/DB affordance) and freeze-safe. Bump
`persist_moves.CHAR_VERSION` on any formula change.

## DONE
- **MC-2 base / pivot / stage context** — `gws/phase_a1/base_context.py`: days-since-52w-high/low,
  prior-leg gain, VCP contraction ratio, tightness, Weinstein stage, MA stack order — PIT, merged
  into the inception bag, future-invariance tested.
- **Inception RS** — 63/126/252-day RS vs bench, the 40/20/20/20 composite, RS-line-new-high flag.
- **True overnight gaps from opens** — `overnight_gap_count`/`largest_overnight_gap` (open vs prior
  close), distinct from the close-to-close `big_day_*`; `open_` threaded through characterize/persist.
- **During-move MA interaction** — `pct_days_above_sma50/200`, `first_close_below_sma50_frac`.
- **Theme-own-move** — `gws/phase_a1/theme_move.py`: composite index + rs-vs-theme + theme-move
  detection (pure; DB membership wiring is the caller's job).
- **Detection provenance** — `detect_params JSONB` + `run_id` on `gws.moves` and `persist_moves`.
- **Catalog audits** — `gws/phase_a1/audit_moves.py`: the 5 step_09-style checks (phantom canary,
  open-move, magnitude consistency, cross-domain span probe, null coverage).
- **Vectorized-builder integration** — `build_feature_matrix(vectorized=True)` sources the proven
  families from `features_vectorized`, skipping their per-point recompute; end-to-end equality with
  the pure build is unit-tested. `compute_features(exclude=...)` added.
- **Minor** — `_json_safe` numpy-scalar/nested-safe; `MoveQuery.order_by/select` column whitelist;
  expression btree indexes on hot JSONB fields.

## REMAINING (small, honest)
- **Candlestick bar-anatomy descriptor family (2026-07-10):** per-bar demand tells, aggregated over
  the move and snapshotted at inception — closing range within bar ((close−low)/(high−low)), upper/
  lower tail ratios, bar spread vs ATR, share of days closing in the top quartile of their range,
  count of high-volume+high-closing-range days. Daily bars only (intraday is a separate, audit-gated
  workstream — see project log 2026-07-10). Additive; bump CHAR_VERSION; future-invariance tested.
- **Driver open-loading:** `detect_moves_for_ticker` doesn't yet SELECT `open`; the overnight-gap
  fields populate only when a caller passes `open_` to persist. One-line SELECT add when the
  orchestrator is written.
- **Cross-domain span translation:** `completeness_audit` spans are FMP-keyed; a Norgate-domain
  detection consuming them needs a `gws.entity_ticker_map` translation (source filter is in place;
  the translation policy is the remaining decision — Lineage C-1 note).
- **Sector/industry + cap/liquidity tier at inception** — gated on the GICS-vintage pre-commit
  (PHASE0_GICS_VINTAGE_PRECOMMIT.md) and a PIT market-cap source.
- **AVWAP-from-base-low distance** — needs an anchor-selection rule; deferred.
- **Deeper base geometry** (explicit pivot/consolidation-high detection, base-on-base count) beyond
  the current days-since-high / VCP / stage proxies.
- **Expensive-family vectorization** (polyfit slopes, CMF, generic bank) — where the real compute
  win is; each extends the vectorized path under `gws/validation/feature_equality`.

## HYPOTHESIS-TESTING FIDELITY (for the sealed practitioner priors h002–h006)
The sealed convergence hypotheses lean on four signatures we currently only PROXY. Adding these as
real PIT inception fields lets the B3 convergence check credit the actual method, not a loose stand-in.
All are additive inception fields (bump `persist_moves.CHAR_VERSION`); all must be future-invariant.
- **Literal TTM squeeze (h003, Carter):** `incept_ttm_squeeze` (Bollinger-14 inside Keltner-14×ATR =
  compression on/off) + `incept_squeeze_bars` (duration in compression) computed PIT from the price
  series. `incept_vcp_ratio_63` is the current fallback proxy but is not Bollinger-in-Keltner.
- **Beta-normalized adaptive RS (h005, Caruso):** `incept_adaptive_rs` = alpha from a rolling
  regression of stock vs benchmark returns (actual − beta×index), volatility-adjusted — Caruso's CARS.
  The current `incept_rs_composite` is raw 40/20/20/20 return; the DIVERGENCE between the two is itself
  a test, so keep both.
- **Group / industry leadership (h004, h006 — Tanner, Webster):** `incept_group_rs` = median RS of the
  ticker's PIT industry/sector cohort at inception (leading-group tell). Gated on PIT sector history
  (PHASE0_GICS_VINTAGE_PRECOMMIT.md) — currently a covariate, not a gate, in both hypotheses.
- **Breakout-bar volume expansion (h002, h004 — the Minervini/Tanner "dry pivot" tension):** distinguish
  DRY base volume (pre-pivot, at the trough) from EXPANSION volume ON the breakout bar. Add a
  breakout-anchored `vol_vs_avg` at the point-of-strength entry (ties into the §12.2 trough-vs-breakout
  anchor), so "volume dries up into the pivot, then surges on the breakout" is testable as one signature.
