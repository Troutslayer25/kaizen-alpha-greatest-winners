"""Trial registry (review M-2) — makes the deflated-Sharpe `n_trials` a COUNTED quantity, not
a recalled guess. Every strategy/model variant evaluated (5 models x 3 architectures x
parameter sweeps x sensitivity runs) is one trial; the true multiple-testing count is their
sum. `TrialLog` accumulates trials in-process during a run; `record_trial`/`count_trials`
persist and read them from gws.experiments (DB access is lazy so this module imports without a
connection). Pass `count_trials(...)` straight into deflated_sharpe_ratio's `n_trials`.
"""
from __future__ import annotations

import json


class TrialLog:
    """In-process counter of trials for a single run. Deterministic, no DB. The final count is
    the `n_trials` for that run's deflated Sharpe."""

    def __init__(self):
        self._trials: list[dict] = []

    def record(self, hypothesis: str, phase: str, parameters: dict, sharpe: float | None = None):
        self._trials.append({"hypothesis": hypothesis, "phase": phase,
                             "parameters": parameters, "sharpe": sharpe})
        return self

    def __len__(self) -> int:
        return len(self._trials)

    @property
    def n_trials(self) -> int:
        return len(self._trials)

    def sharpes(self) -> list[float]:
        return [t["sharpe"] for t in self._trials if t["sharpe"] is not None]


def record_trial(hypothesis: str, phase: str, parameters: dict, *,
                 commit_hash: str | None = None, result_summary: str | None = None,
                 outcome: str | None = None) -> None:
    """Persist one trial to gws.experiments (ka-runner / workstation)."""
    from ka_lib.db import ka_upsert  # lazy: no DB needed to import this module
    ka_upsert("gws.experiments", [{
        "hypothesis": hypothesis, "phase": phase, "parameters": json.dumps(parameters),
        "commit_hash": commit_hash, "result_summary": result_summary, "outcome": outcome,
    }], conflict_columns=[])


def count_trials(phase: str | None = None) -> int:
    """Mechanical trial count from gws.experiments for the DSR haircut."""
    from ka_lib.db import ka_query  # lazy
    if phase is None:
        rows = ka_query("SELECT count(*) AS n FROM gws.experiments")
    else:
        rows = ka_query("SELECT count(*) AS n FROM gws.experiments WHERE phase = %s", (phase,))
    return int(rows[0]["n"])
