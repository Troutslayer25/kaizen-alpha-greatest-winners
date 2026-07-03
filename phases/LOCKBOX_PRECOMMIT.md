# Lockbox pre-commit — the sealed final-holdout era

**Committed 2026-07-03 (review C-1).** The true lockbox is a final out-of-sample era **never
examined until the very end** — the #7 snowball-risk control that bounds the researcher degrees of
freedom FDR cannot reach. It was prose-only (no date, no code); this file sets the boundary and
`gws/phase0/lockbox.py` enforces it.

## Boundary (RATIFY)
- **`LOCKBOX_START = 2022-01-01`** (recommended default in `gws/phase0/lockbox.py`).
- **Scott must ratify or change this ONE date before the Gate 0.5 pilot**, and it is then frozen
  forever. Moving it after any examination is itself a forking path and voids the control.
- Rationale for the default: the final ~few years of the modern FMP era, held entirely aside; the
  bulk of the distinct regimes the emotional-invariance thesis depends on sit before it.
  Alternative to consider: a hash-sealed *random* era rather than the tail (harder to rationalize
  away, but complicates walk-forward). If you prefer the tail, keep 2022-01-01 or adjust.

## Enforcement (mechanical)
- `gws.phase0.lockbox.assert_not_in_lockbox(dates, unlock=False)` raises on any lockbox date; the
  detector driver, universe builder, and feature extraction call it (or `drop_lockbox`) so the
  holdout cannot be touched by accident.
- `unlock=True` is the SINGLE auditable act of opening the holdout, performed only at the terminal
  validation step, in a committed change with Scott's sign-off.
- Unit test: `assert_not_in_lockbox` raises inside the window and passes outside it; `drop_lockbox`
  truncates to the pre-lockbox span.

## Status
Boundary date **PENDING SCOTT'S RATIFICATION**. The mechanism is live; wiring `unlock`/`drop_lockbox`
into the (forthcoming) production orchestrator's Phase-0 and detection entry points is required
before the first full run.
