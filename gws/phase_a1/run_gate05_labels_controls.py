"""Gate 0.5 pilot — step 4: forward labeling (setup_labels) + matched controls.

Labeling (T1 production frame): per pilot ticker, sample (ticker, date) points every 5 bars
after a 252-bar burn-in, label positive iff a PRIMARY-SCALE (trail_6) confirmed trough falls
within the next K=20 trading days (house/method-library default — K is a decay-analysis
output later, LOGGED as pilot default now). Indices are rebuilt by re-running the (fixed,
deterministic) detection loader so as_of_index maps to the exact cleaned date vector the
catalog was persisted from.

Matched controls (discovery frame): cases = resolved trail_6 troughs. Pilot constructions per
the pre-commit — PRIMARY 'minimal' = same-date eligible point on a different pilot ticker;
ONE robustness = 'liquidity' adding same within-date dollar-volume-quintile. Pool is
pilot-internal (300 names' eligible dates): features exist only for pilot names in step 5;
a full-universe pool is a full-run concern, logged. Construction rows are distinguished by
match_liquidity_bucket NULL (minimal) vs set (liquidity). Seed 20260719.

    python -m gws.phase_a1.run_gate05_labels_controls
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib

from gws.phase_a1.detect_driver import detect_moves_for_ticker      # noqa: E402
from gws.phase_a1.labeling import build_setup_labels                # noqa: E402
from gws.phase_a1.matched_controls import build_matched_controls    # noqa: E402
from gws.phase_a1.run_gate05_detection import SCALES, load_pilot    # noqa: E402

RUN_ID = "gate05_pilot"
PRIMARY_TRAIL = 6.0
K = 20
SEED = 20260719


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    pilot = load_pilot()
    eids = [int(r["entity_id"]) for r in pilot]

    move_ids = {}                     # (eid, start_date) -> move_id, primary scale only
    for r in conn.execute(
            "SELECT move_id, ticker_id, start_date FROM gws.moves "
            "WHERE run_id=%s AND scale='trail_6'", (RUN_ID,)):
        move_ids[(r["ticker_id"], r["start_date"])] = r["move_id"]

    n_lab = n_pos = 0
    with conn.cursor() as cur:
        for eid in eids:
            dates, close, high, low, volume, by_scale = detect_moves_for_ticker(
                conn, eid, source="norgate", scales=SCALES)
            moves = by_scale.get(PRIMARY_TRAIL, [])
            if not dates:
                continue
            from gws.phase_a1.series_guard import assert_series_hash  # M3 composition guard
            assert_series_hash(conn, RUN_ID, eid, dates)
            df = build_setup_labels({eid: moves}, n_days=len(dates), forward_window_k=K)
            cur.execute("DELETE FROM gws.setup_labels WHERE ticker_id=%s AND forward_window_k=%s",
                        (eid, K))
            rows = []
            for _, r in df.iterrows():
                d = dates[int(r["as_of_index"])]
                linked = (move_ids.get((eid, dates[int(r["linked_trough_index"])]))
                          if r["linked_trough_index"] is not None
                          and not pd.isna(r["linked_trough_index"]) else None)
                rows.append((eid, d, bool(r["label"]), K, linked,
                             None if pd.isna(r["lead_time_days"]) else int(r["lead_time_days"])))
            cur.executemany(
                "INSERT INTO gws.setup_labels (ticker_id, date, label, forward_window_k, "
                "linked_move_id, lead_time_days) VALUES (%s,%s,%s,%s,%s,%s)", rows)
            n_lab += len(rows)
            n_pos += sum(1 for r in rows if r[2])
    print(f"setup_labels: {n_lab} points, {n_pos} positive ({n_pos / max(1, n_lab):.1%}), K={K}",
          flush=True)

    # ---- matched controls -------------------------------------------------------------
    pool = pd.DataFrame(conn.execute(
        "SELECT u.ticker_id, u.date, u.dollar_volume_50d, e.is_delisted "
        "FROM gws.universe_eligibility u JOIN ka_history.entities e ON e.entity_id=u.ticker_id "
        "WHERE u.eligible AND u.ticker_id = ANY(%s)", (eids,)).fetchall())
    pool["dollar_volume_50d"] = pool["dollar_volume_50d"].astype(float)
    pool["liq_q"] = (pool.groupby("date")["dollar_volume_50d"]
                     .transform(lambda s: pd.qcut(s.rank(method="first"),
                                                  min(5, max(1, len(s))), labels=False)))
    cases = pd.DataFrame(conn.execute(
        "SELECT m.move_id, m.ticker_id, m.start_date AS date FROM gws.moves m "
        "WHERE m.run_id=%s AND m.scale='trail_6' AND NOT m.is_open", (RUN_ID,)).fetchall())
    cases = cases.merge(pool[["ticker_id", "date", "liq_q", "is_delisted"]],
                        on=["ticker_id", "date"], how="left")
    print(f"cases: {len(cases)} troughs; {cases['liq_q'].isna().sum()} at non-eligible dates "
          f"(kept for minimal, dropped for liquidity construction)", flush=True)

    with conn.cursor() as cur:
        cur.execute("DELETE FROM gws.matched_controls")
        for tag, match_cols, sub in (
                ("minimal", ["date"], cases),
                ("liquidity", ["date", "liq_q"], cases.dropna(subset=["liq_q"]))):
            controls, diag = build_matched_controls(
                sub.reset_index(drop=True), pool, match_cols, n_per_setup=1, seed=SEED)
            rows = [(int(sub.reset_index(drop=True).at[c["matched_setup_id"], "move_id"]),
                     int(c["ticker_id"]), c["date"],
                     None if tag == "minimal" else f"q{int(c['liq_q'])}")
                    for c in controls.to_dict("records")]
            cur.executemany(
                "INSERT INTO gws.matched_controls (matched_move_id, ticker_id, date, "
                "match_liquidity_bucket) VALUES (%s,%s,%s,%s)", rows)
            print(f"controls[{tag}]: {len(rows)} rows; diag={diag}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
