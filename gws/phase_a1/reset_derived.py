"""Tear down the gws.moves FK children BEFORE any detection re-run (Gate 0→A1 review C1).

move_id is SERIAL and persist_moves does delete-before-insert, so a re-detect REASSIGNS
every move_id. matched_controls / setup_labels / entry_candidates reference move_id with
NO ACTION: with children present, the per-ticker DELETE raises an FK violation that the
detection runner's per-ticker isolation swallows — leaving the catalog silently stale
WHILE THE FINGERPRINT STILL MATCHES (proven live in the review). Rule: children are
derived artifacts; they are rebuilt after detection, never preserved across it.

    python -m gws.phase_a1.reset_derived            # truncate the three children
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

CHILDREN = ("gws.matched_controls", "gws.setup_labels", "gws.entry_candidates")


def reset(conn) -> None:
    for t in CHILDREN:
        n = conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]
        conn.execute(f"TRUNCATE {t}")
        print(f"truncated {t} ({n} rows)")


def children_row_count(conn) -> int:
    return sum(conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"]
               for t in CHILDREN)


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg
    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    reset(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
