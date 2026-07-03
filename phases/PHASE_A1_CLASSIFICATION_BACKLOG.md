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
