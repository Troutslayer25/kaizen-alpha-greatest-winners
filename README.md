# Kaizen Alpha — Greatest Winners Study

Discovery-first quantitative study of the pre-move characteristics of stocks before significant price advances. Move types are discovered empirically (no pre-defined cohorts); external frameworks (CANSLIM/IBD/Minervini/Zanger) are consulted only in Phase B3, after independent findings are locked.

## Governing documents

- **Master design (definitive):** `KA_GREATEST_WINNERS_MASTER.md` — consolidated methodology, validation architecture, and ranked risk register (current to auditor V11).
- **Study design (original):** `KA_GREATEST_WINNERS_STUDY_V10.md` (source doc held outside the repo)
- **Audit framework:** `KA_AUDITOR_PROMPTS_V11.md` (four independent phase-gate auditors)
- **Regime-conditional design note:** `research/regime_conditional_discovery.md`
- **Entry-point discovery note:** `research/entry_point_discovery.md` (Method 8 expansion — low-risk entries along the move)
- **Market-context inputs note:** `research/market_context_inputs.md` (regime measurements; swept breadth-MA surface)
- **Trend-following foundations note:** `research/trend_following_foundations.md` (base/RS/group/volume families; failed-lookalikes; data capture)
- **Phase 0 pre-commit:** `phases/PHASE0_PRECOMMIT.md`
- **Project log:** `KA_PROJECT_LOG.md` (every HALT / escalation / gate decision)

Every phase runs: pre-committed spec (GitHub timestamp = proof) → Sprint-Mode build → four-auditor gate. No phase proceeds until all four auditors CLEAR.

## Layout

```
gws/
  common/      indicators, walk-forward splitter, statistics helpers
  phase0/      universe construction + data completeness audit (DB-dependent)
  phase_a1/    move detection, characterization, clustering, controls
  phase_a2/    feature extraction (price/volume, fundamental, context)
  phase_a3/    statistical discovery (univariate, neutralization, ML, decay)
  synthetic/   synthetic panel generator for leakage/labeling validation
  schema/      gws.* Postgres DDL
tests/         unit + integration tests
```

## Data layer

Study tables live in a dedicated `gws` schema inside the `kaizen_alpha` Postgres DB (parallel to `public` and `ka_history`). DB/FMP/logging reuse the existing `ka_lib` package from the production pipeline (`C:\Users\scott\kaizen-alpha`); add it to `PYTHONPATH` or install it editable. The pure-code modules in `gws/common`, `gws/phase_a1`, and `gws/synthetic` have **no DB dependency** and are unit-testable standalone.

## Prior-code reuse governance (bias control)

Reused KA code is classified A (framework-neutral math — attest once), B (parameterized — re-derive parameters, never inherit), or C (framework-embedded — excluded from discovery). Every reuse is recorded in `gws.code_provenance` and reviewed by Auditors 2 and 4. See `KA_AUDITOR_PROMPTS_V11.md` §1A.

## Running tests

```
pip install -r requirements.txt
pytest
```
