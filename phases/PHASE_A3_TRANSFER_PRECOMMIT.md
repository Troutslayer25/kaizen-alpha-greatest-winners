# Phase A3 pre-commit — the emotional-invariance transfer test (corrected instrument)

**Committed 2026-07-03 (review C-2).** The transfer test is the study's central instrument
(master §1, §12.1) and the Gate 0.5 memo turns on it. The prior design could not cleanly
confirm or deny the hypothesis; this freezes the corrected instrument (implemented in
`gws/regime/transfer_test.py`) before it is run on real data.

## The three corrections (all mandatory)
1. **Symmetric normalization.** BOTH feature classes are expressed regime-relative
   (`regime_relative_normalize`, z-scored within era) before the test. Emotional features may
   NOT be normalized while structural features are left as raw magnitudes — otherwise "emotion
   transfers" is indistinguishable from "z-scored features transfer." Structural features are
   expressed regime-relative too (sector share vs era distribution, fundamentals vs era
   cross-section, duration percentile within era).
2. **In-era baseline (transfer RATIO).** The statistic is `transfer_ratio = (AUC_out - 0.5) /
   (AUC_in - 0.5)`, not raw out-of-era AUC. A structural feature that is weak everywhere must
   not be scored as "failed to transfer"; the ratio is NaN when in-era skill is absent.
3. **>= 3 era pairs.** The conclusion is the DISTRIBUTION of transfer ratios across ordered era
   pairs (`transfer_distribution`), never a single early->late split. Pilot: >=3 pairs; A3:
   the full era-pair matrix over Norgate deep history. Feature-set capacity is matched across
   classes (equal counts or a capacity-controlled model) so class comparisons are not
   dimensionality artifacts.

## Decision rule (frozen)
Invariance is **SUPPORTED** iff there are >= 3 comparable era pairs AND the emotional-class
transfer ratio exceeds the structural-class ratio in a MAJORITY of them
(`invariance_supported`). If NOT supported, the study switches to regime-conditional discovery
as the primary mode (master §12.1). This verdict, with the per-pair ratio table attached, is
part of the signed Gate 0.5 memo.

## Feature-class assignment note (review P-5)
`rs_at_high` and the group-strength family are assigned to the EMOTIONAL class (herding /
leadership) for this test — they are the strongest cross-era-invariance candidates and the
hypothesis should be tested on its best candidates, not accidentally filed as structural.
