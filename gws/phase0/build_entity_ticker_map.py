"""Phase 0 — populate gws.entity_ticker_map (entity_id <-> public.tickers.id crosswalk).

Lineage artifact consumed by the completeness audit (FMP<->Norgate return cross-validation).
Only ACTIVE equities get a row: a live Norgate symbol and a live FMP symbol are the same
company today, so symbol equality is safe. Delisted / pre-2010 entities deliberately have NO
row and are joined by entity_id against ka_history only (see 001_gws_schema.sql) — mapping
them by symbol would reintroduce the recycled-symbol mis-attribution CF-1 exists to prevent.

Symbol normalization: Norgate share classes use '.' (BRK.A), FMP uses '-' (BRK-A).

    python -m gws.phase0.build_entity_ticker_map
"""
from __future__ import annotations

import sys

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib
from ka_lib import config as cfg  # noqa: E402


def main() -> int:
    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    n = conn.execute(
        "INSERT INTO gws.entity_ticker_map (entity_id, ticker_id, match_method, confidence) "
        "SELECT e.entity_id, t.id, 'assetid_symbol', 1.0 "
        "FROM ka_history.entities e "
        "JOIN public.tickers t ON t.symbol = replace(e.norgate_symbol, '.', '-') AND t.active "
        "WHERE e.subtype1 = 'Equity' AND NOT e.is_delisted "
        "ON CONFLICT (entity_id) DO NOTHING").rowcount
    active = conn.execute(
        "SELECT count(*) AS n FROM ka_history.entities "
        "WHERE subtype1 = 'Equity' AND NOT is_delisted").fetchone()["n"]
    mapped = conn.execute("SELECT count(*) AS n FROM gws.entity_ticker_map").fetchone()["n"]
    print(f"active equities: {active}; mapped: {mapped} (+{n} new); "
          f"unmapped active: {active - mapped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
