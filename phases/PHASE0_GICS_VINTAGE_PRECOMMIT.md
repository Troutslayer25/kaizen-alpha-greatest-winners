# Phase 0 pre-commit — sector/industry classification vintage

**Committed 2026-07-03 (review PIT 3.3 / lineage).** `ka_history.entities.gics_name` is a SINGLE
CURRENT snapshot, overwritten on every upsert. Sector/industry is planned as a matched-control
matching variable and a neutralization group. Using a snapshot for historical dates is a
look-ahead (a 1985 conglomerate gets its 2026 GICS bucket) AND a survivorship tilt (dead names
with NULL/stale classification fall out of control pools, so controls skew to survivors).

## Named Phase-0 output (required before A1)
The Phase-0 completeness audit MUST emit a decision: **is Norgate GICS point-in-time or
snapshot-only?** — verified, not assumed. Record it in the Phase-0 report.

## Rule (pre-committed, applied by the matched-control + neutralization builders)
- **If snapshot-only** (the expected case): sector is DROPPED from the deep-window (pre-~2010)
  matched-control match set — match on date + size + liquidity only — or replaced with an
  era-appropriate coarse bucket derived from a PIT source. Neutralization uses no industry group
  in the deep window. The decision and its date boundary are recorded.
- **If genuinely PIT**: sector may be used as a match/neutralization variable across the full
  window, with the vintage source documented.
- Either way, the matched-control diagnostic reports the DELISTED share of each control pool vs
  the case set, so a survivor-tilted pool is visible (review PIT 3.3 test).

Until the audit confirms PIT, code MUST treat GICS as snapshot-only (fail safe).
