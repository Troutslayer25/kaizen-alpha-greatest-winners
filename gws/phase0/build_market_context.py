"""Build gws.market_context — daily survivorship-free breadth + $SPX posture (B-anchor-3
§4b; reusable by any future study). Breadth = % of ELIGIBLE universe names above their own
5-bar / 200-bar SMA, computed from ka_history over the full deep history. $SPX columns
from NDU at runtime. Idempotent full rebuild (TRUNCATE + insert).

    python -m gws.phase0.build_market_context
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")

BREADTH_SQL = """
INSERT INTO gws.market_context (date, breadth_pct_above_5d, breadth_pct_above_200d, n_universe)
SELECT s.date,
       100.0 * avg((s.close > s.sma5)::int),
       100.0 * avg((s.close > s.sma200)::int),
       count(*)
FROM (
  SELECT h.entity_id, h.date, h.close,
         avg(h.close) OVER w5   AS sma5,
         avg(h.close) OVER w200 AS sma200,
         row_number() OVER (PARTITION BY h.entity_id ORDER BY h.date) AS rn
  FROM ka_history.eod_history h
  JOIN ka_history.entities e ON e.entity_id = h.entity_id AND e.subtype1 = 'Equity'
  WHERE h.close IS NOT NULL
  WINDOW w5   AS (PARTITION BY h.entity_id ORDER BY h.date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW),
         w200 AS (PARTITION BY h.entity_id ORDER BY h.date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW)
) s
JOIN gws.universe_eligibility u ON u.ticker_id = s.entity_id AND u.date = s.date AND u.eligible
WHERE s.rn >= 200
GROUP BY s.date
"""


def main() -> int:
    import norgatedata
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    conn.execute("TRUNCATE gws.market_context")
    print("computing deep breadth (one window pass over eod_history) ...", flush=True)
    conn.execute(BREADTH_SQL)
    n = conn.execute("SELECT count(*) AS n FROM gws.market_context").fetchone()["n"]
    print(f"breadth rows: {n}", flush=True)

    spx = norgatedata.price_timeseries("$SPX", timeseriesformat="pandas-dataframe")["Close"]
    df = pd.DataFrame({"close": spx})
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    df["hi252"] = df["close"].rolling(252).max()
    df["ret"] = np.log(df["close"]).diff()
    df["std21"] = df["ret"].rolling(21).std()
    rows = [(float(r.close),
             float(r.close / r.sma50 - 1) if r.sma50 == r.sma50 else None,
             float(r.close / r.sma200 - 1) if r.sma200 == r.sma200 else None,
             float(r.close / r.hi252 - 1) if r.hi252 == r.hi252 else None,
             float(r.std21) if r.std21 == r.std21 else None,
             ts.date()) for ts, r in df.iterrows()]
    with conn.cursor() as cur:
        cur.executemany(
            "UPDATE gws.market_context SET spx_close=%s, spx_vs_50d=%s, spx_vs_200d=%s, "
            "spx_dist_52w_high=%s, spx_ret_std_21=%s WHERE date=%s", rows)
    print(f"$SPX posture stamped ({len(rows)} bars available)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
