# Phase A2 pre-commit — the feature-family map is frozen before A3

**Committed 2026-07-03 (review M-1).** `hierarchical_fdr` (gws/phase_a3/research_path.py)
corrects for multiplicity at the FAMILY level first, then at the member level within selected
families at the Benjamini–Bogomolov-reduced level `alpha * n_selected / n_families`. Because
family membership decides what clears correction, the family taxonomy is a load-bearing
statistical object and must be **frozen before any A3 result is examined** — otherwise
regrouping a strong feature out of a noisy family is an undetectable way to game the FDR.

## Rule
- The authoritative family map is the `PRICE_VOLUME_MOTIVATION` keys + `GENERIC_PREFIXES` in
  `gws/phase_a2/feature_catalog.py` **plus** the explicit family assignment used when building
  the `families` dict passed to `hierarchical_fdr`. The trailing-`_<lookback>` prefix strip is
  only the default; the frozen mapping below is authoritative where it differs.
- No feature may move between families, and no family may be split or merged, after the first
  A3 run — except via a committed change to this file (GitHub timestamp = proof), reviewed as a
  methodology change, never bundled with a results-inspection commit.
- A feature whose family is ambiguous is assigned at registration (pre-commit), not at analysis.

## Frozen families (as of A2 freeze, 2026-06-21 feature net)
Price/volume: `volatility` (atr_pct, ret_std), `location` (dist_from_high, dist_from_low,
range_position), `moving_average` (price_to_ma, ma_compression), `volume` (vol_ratio, vol_surge,
vol_trend, updown_vol, accum_vol_share, up_vs_down_vol_extreme, cmf), `base_structure`
(base_depth, vol_contraction, tight_days_share, range_tightness), `relative_strength` (rel_strength,
rs_line_slope, rs_at_high), `group_strength` (sector_rs, sector_rs_slope, group_strength).
Generic bank: one family `generic` (all `GENERIC_PREFIXES`).

Any addition to the feature net (currently FROZEN, master §13) must land here with its family
assignment before it is computed on real data.
