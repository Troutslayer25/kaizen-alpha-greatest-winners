# Design Note — Trend-Following Foundations (comprehensiveness, not bias)

**Status:** DESIGN DECISION (2026-06-21). Code pieces BUILT + tested; data-capture pieces
pre-committed for Phase 0. All are *comprehensiveness / capability* additions — wider neutral
net and more raw material — never assertions of which edge wins. Discovery still decides;
every feature is motivation-tagged, neutralized, walk-forward validated, and frameworks stay
sealed until B3. No analytical work has begun.

The "do it now" rationale: **data capture (Phase 0)** and **feature families (A2)** are the
expensive-to-backtrack layers (adding either late means re-ingesting / re-extracting over the
whole universe). New statistical methods are cheap to add anytime, so they are not front-loaded.

---

## 1. Failed-lookalike negatives in the control/label set  [DESIGN — implement in A1]
The trend-following question is separating the breakout that *holds* from the one that
*fails*. A negative set of random non-events makes the model learn "winner vs nothing" (easy,
weak). The negatives must explicitly include **observations with breakout/entry-like
configurations that did NOT lead to a successful move** — i.e., configuration-matched failures,
not just random dates. Definition is by *configuration* (not by the outcome we expect), so it
stays bias-clean. Implemented in A1 control/label construction (`matched_controls` + the
`setup_labels` negative sampling): ensure failed-setup observations are represented and
labeled. The entry-point analysis (Method 8) already scores by forward reward/risk, so failed
entries fall out naturally — this makes them a first-class part of the negative population.

## 2. Sector / group strength  [DATA = Phase 0; FEATURE FN = BUILT]
"Leading stocks in leading groups." Two parts:
- **Data (Phase 0):** ingest sector/industry classification + build sector return series.
  Norgate carries historical classifications, so this is *potentially deep-history-capable*
  (effective depth confirmed by the Phase 0 audit) — unlike earnings/float below.
- **Feature fn (BUILT):** `gws/phase_a2/group_strength.py` — `sector_rs_{lb}` (stock vs its
  sector), `sector_rs_slope_{lb}`, `group_strength_{lb}` (sector vs the market). Reuses the RS
  math vs an arbitrary reference; PIT-clean; tagged.

## 3. Consolidation / base-structure feature family  [A2 — BUILT]
`compute_features`: `base_depth_{lb}` (range depth), `range_position_{lb}` (where price sits in
the range; ~1 = top/breakout area), `vol_contraction_{lb}` (recent-half vs earlier-half ATR;
<1 = tightening), `tight_days_share_{lb}` (share of below-median-range days). Measures base /
contraction structure from first principles — clustering finds the base-like shapes; no named
pattern (e.g. VCP) asserted.

## 4. Relative-strength line family  [A2 — BUILT]
`compute_features`: beyond `rel_strength_{lb}` (outperformance) — `rs_line_slope_{lb}` and
`rs_at_high_{lb}` (RS line at a new high = the RS-leads-price leading tell). Rank-within-
universe/sector needs the cross-sectional panel and is added at extraction time.

## 5. Earnings / event date markers  [DATA = Phase 0, MODERN-WINDOW ONLY]
Capture earnings report *dates* (not the numbers — those are already gated by `available_date`)
as event markers, so the study can discover earnings-gap / post-earnings-drift entries (a major
trend catalyst). FMP earnings calendar is likely already ingested in the KA pipeline. **Modern
window only** (FMP ~1985/2010+); joins the fundamental/limited branch — NULL in deep history,
which the branch-availability-by-window design already handles. Earnings-driven edges are
discoverable only in the modern window (honest and acceptable).

## 6. Float / supply  [DATA = Phase 0, MODERN-WINDOW ONLY]
Capture **free float** (FMP shares-float likely already ingested) so the study can discover
whether supply relates to move explosiveness. Recorded as a feature (like liquidity), never a
gate. Modern-window only; same branch handling as #5.

## 7. Multi-timeframe (weekly + daily)  [INFRA = BUILT helper; wiring later]
`gws/common/resample.py` — `resample_weekly` produces weekly OHLCV (causal: a week's bar uses
only that week's days, so PIT holds). The feature families are timeframe-agnostic, so A2 runs
the SAME families on both daily and weekly series — roughly doubling the neutral net with no
new feature code. Lower-priority items deferred: trendline / linear-channel break features;
explicit antecedent-trend-state (largely covered by the swept MA-configuration family).

---

## Bias discipline (applies to all)
Each is a first-principles measurement or a neutral data capture, motivation-tagged in
`feature_catalog`, run through factor/industry neutralization and walk-forward, with the
research-path/family-FDR correction and negative-control harness. We add (e.g.) a comprehensive
RS family because RS is a natural thing to measure — not because "RS works." The net is wide;
the answer stays the data's.
