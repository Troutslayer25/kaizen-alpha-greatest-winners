"""Apply the gws.* study schema to the live kaizen_alpha DB (idempotent).

All DDL is CREATE TABLE/INDEX IF NOT EXISTS, so this is safe to re-run and
additive only — it never touches public.* or ka_history.* data.

Run from anywhere with DB access (reuses ka_lib config):
    python -m gws.phase0.apply_gws_schema
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib
from ka_lib.db import ka_execute, ka_query  # noqa: E402

DDL_PATH = pathlib.Path(__file__).resolve().parents[2] / "gws" / "schema" / "001_gws_schema.sql"


def main() -> None:
    sql = DDL_PATH.read_text(encoding="utf-8")
    ka_execute("CREATE SCHEMA IF NOT EXISTS gws")
    # ka_execute passes `params or ()` — the empty tuple makes psycopg scan for placeholders,
    # so literal % in DDL (LIKE 'frozen_train:%' CHECK) must be doubled (found 2026-07-24).
    ka_execute(sql.replace("%", "%%"))  # psycopg3 runs the multi-statement DDL block in one shot
    tables = ka_query(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='gws' ORDER BY table_name"
    )
    print(f"gws schema applied — {len(tables)} tables present:")
    for t in tables:
        print("  ", t["table_name"])


if __name__ == "__main__":
    main()
