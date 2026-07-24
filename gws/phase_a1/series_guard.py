"""Date-vector composition guard (Gate 0→A1 review, integration M3).

Stages that rebuild as_of_index<->date by re-running the detection loader must prove they
are looking at the SAME cleaned series the catalog was persisted from. Detection writes
gws.detection_series_hash; every consumer calls assert_series_hash and refuses to compose
on mismatch — drift otherwise silently NULLs setup_labels.linked_move_id and shrinks
transfer samples."""
from __future__ import annotations

import hashlib


def dates_sha(dates) -> str:
    return hashlib.sha256("|".join(str(d) for d in dates).encode()).hexdigest()[:32]


def assert_series_hash(conn, run_id: str, ticker_id: int, dates) -> None:
    row = conn.execute(
        "SELECT n_bars, dates_sha FROM gws.detection_series_hash "
        "WHERE run_id=%s AND ticker_id=%s", (run_id, ticker_id)).fetchone()
    if row is None:
        raise RuntimeError(
            f"series_guard: no detection hash for run_id={run_id} ticker={ticker_id} — "
            f"detection has not run (or predates the guard); re-run detection first")
    if row["n_bars"] != len(dates) or row["dates_sha"] != dates_sha(dates):
        raise RuntimeError(
            f"series_guard: date-vector drift for ticker {ticker_id} "
            f"(catalog {row['n_bars']} bars sha {row['dates_sha']}; now {len(dates)} bars "
            f"sha {dates_sha(dates)}). The cleaned series changed since detection — "
            f"re-run detection before composing this stage")
