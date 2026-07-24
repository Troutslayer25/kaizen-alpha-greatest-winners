# Gate 0.5 — Real-Data Pilot: Exit Memo (DRAFT for Scott's signature)

**Drafted:** 2026-07-24, KA-Workstation, by the implementation agent per
`GATE05_PILOT_PRECOMMIT.md` (commit `783c8d8`). Pilot universe locked at `292524d`
BEFORE any pilot compute. Evidence artifacts: `phases/gate05_evidence/`.
**The agent does not self-certify** — the cell determination and signature are Scott's.

---

## The question the memo must answer

*"Is the study learning a transferable winner setup, or merely rediscovering
regime-specific historical artifacts?"*

Pilot-scale answer: **the measured signal transfers across eras almost losslessly — but a
material share of that signal is the trough anchor itself, and the emotional-vs-structural
differential the thesis predicts is absent at pilot scale.** Both facts below.

## Break-the-pipeline checklist (pre-committed, all items)

| Item | Result |
|---|---|
| End-to-end on all 300 incl. every adversarial class | **PASS** — 0 errors; 2 fully-sub-$1 names correctly zero-move |
| Idempotent re-run, identical counts/IDs | **PASS** — fingerprint rows=68593 sha=113b19f960593f64, twice |
| Every stage logs row counts, no silent-empty stages | **PASS** — counts in KA_PROJECT_LOG + runner output |
| PIT harness green; available_date violations = 0 | **PASS with scope note** — price/volume branch is PIT-by-construction + outcome quarantine enforced at the matrix choke point; the fundamentals branch (where available_date lives) was NOT exercised in the pilot |
| Negative controls produce null bands; no planted-signal leakage | **BANDS PRODUCED; FLAG RAISED** — see finding F2. Shuffle-null clean at 0.50 (no machinery leakage); the within-ticker shift control scored 0.83, which is the trough-anchor encoding, not classic leakage. Strict reading = investigate; both readings presented |
| No detected move spans zero-volume/stale/excluded bars | **PASS by construction** — such bars are forward-filled flat (cannot seed or extend a move); moves may span flat-filled bars, which is the fill design, noted honestly |
| Full-universe runtime projection < 7 days | **PASS** — pilot stages ≈ 7 min wall for 300 names on this box; naive ×107 ≈ ~13 h serial, ~1–2 h with the 16-way parallelism already used. Detection+eligibility for all 32,234 equities already ran in minutes |

**Decision-D events during the pilot (pre-committed response to a broken pipeline; both fixed, re-run, committed):**
1. RAW high/low paired with adjusted close (ATR split-ratio-wrong) — fixed pre-compute, regression test.
2. 46 phantom mega-moves from sub-penny prints — the ratified $1 raw-close validity floor was
   never consumed at detection; enforced, re-run, audits all-zero.

## §12.1 transfer experiment (pre-committed metrics, stratified names only)

| Split | Family | Sign agree | Spearman ρ | AUC cross-era | AUC within-train |
|---|---|---|---|---|---|
| 2010 primary | emotional (61f) | 0.82 | 0.95 | 0.873 | 0.890 |
| 2010 primary | structural (17f) | 1.00 | 0.94 | 0.875 | 0.888 |
| 2000 robustness | emotional | 0.80 | 0.95 | 0.885 | 0.898 |
| 2000 robustness | structural | 1.00 | 0.96 | 0.880 | 0.899 |

Shuffle-null band: (0.488, 0.517). All transfer metrics sit far above it; cross-era
degradation vs within-era is ≈ 0.01–0.02 AUC. **Per the pre-committed reading bands this is
FOR transfer, in both families, on both splits.**

## Findings that qualify the FOR reading (the important part)

**F1 — No emotional/structural differential.** The central thesis predicts emotional
features transfer and structural degrade. At pilot scale BOTH transfer equally (structural
sign agreement 1.00). The thesis is neither confirmed nor falsified — the instrument
produced no separation on this frame.

**F2 — The trough anchor contaminates the discovery frame.** Within-ticker label-shift
(k=5 bars) still scores AUC 0.832 vs shuffle-chance 0.50: points near a trough look like
troughs ("distance from rolling low" is definitionally case-like), so part of the measured
— and transferred — signal is the detector's own definition, which transfers across eras
trivially. This is snowball risk #2 (trough-vs-breakout anchoring) materializing in the
harness. **Consequence: the pre-committed trough-vs-breakout / point-of-strength anchor
experiment must run FIRST in Phase A1, before any finding is read as a setup signature.**
Permute-within-date band (0.52–0.55) additionally shows a small era-composition base rate.

**F3 — Clustering is fragmented at pilot N.** 27 clusters, 35% noise, ARI 0.710 (marginal;
tie-break selected discrete). Cluster-count stability is a full-universe question.

**F4 — Ratifications requested with this memo:** primary scale `trail_6` (A1 pre-commit
never pinned the value); NDU-runtime `$SPX` as the standing benchmark; the D1–D3 selection
deviations (log 2026-07-24); the same-scale significance comparison-set interpretation.

## Decision matrix (Scott signs ONE cell)

| Cell | Condition | Fired? |
|---|---|---|
| A | checklist green + transfer FOR | **Formally yes**, with F1/F2 caveats above |
| B | checklist green + transfer MIXED | Only under a strict reading that scores F2's flag as a failed leak item AND F1 as "no per-thesis separation" |
| C | transfer AGAINST | No |
| D | checklist failed | Fired twice DURING the pilot; both resolved per the pre-committed D path |

**Agent's recommendation (not a certification):** treat as **A with mandates** — proceed to
the Gate 0→A1 four-auditor review, with (1) the anchor experiment as the FIRST pre-committed
A1 analysis, (2) F1 carried as the open state of the central thesis, (3) the F4
ratifications recorded. Alternative defensible reading: B (regime-conditional primary) if
you weigh F1 as "the universal-vs-regime question is unresolved, so don't default to
universal." The pre-commit's own note applies: pilot N is powered for pipeline-breaking and
directional evidence, not significance claims.

---

**Scott's determination:** cell ____ .  Signature: ____________  Date: ________
