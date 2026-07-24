"""Gate 0.5 pilot — catalog audits, significance percentiles, step-3 clustering + stability.

1. Post-persist audits (audit_moves.run_audits): phantom mega-moves, never-closing opens,
   row-internal inconsistency, cross-domain span collisions. Any failure HALTs (exit 1).
2. magnitude_pctile via the PIT-safe EXPANDING assignment (A1 pre-commit default), decision-
   date keyed. COMPARISON SET = same (detection_system, scale, direction) peers: a trail_2
   swing leg ranked against trail_15 arcs would make percentile mean "which stop width",
   not "how big for its kind". Interpretation logged for the exit memo, basis='expanding'.
3. Clustering (ratified dims: magnitude, duration, uncensored smoothness) on the primary
   scale's RESOLVED moves. Transform: z-scored [log1p(gain), log1p(duration), smoothness]
   (log_magnitude is already the characterization vocabulary; raw heavy tails would let a
   handful of 100x moves own the metric). HDBSCAN(min_cluster_size=15, method defaults) +
   mandatory bootstrap stability; marginal verdicts resolved by resolve_representation
   (the math decides discrete vs continuous, not the analyst).

    python -m gws.phase_a1.run_gate05_catalog
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\scott\kaizen-alpha")  # reuse production ka_lib

from gws.phase_a1.audit_moves import run_audits                      # noqa: E402
from gws.phase_a1.clustering import (cluster_stability, make_hdbscan,  # noqa: E402
                                     resolve_representation, zscore)
from gws.phase_a1.significance import assign                          # noqa: E402

RUN_ID = "gate05_pilot"
PRIMARY_SCALE = "trail_6"
INPUT_DIMS = "log1p_magnitude,log1p_duration,smoothness"
NATURAL_KEY = "id_domain=%s AND ticker_id=%s AND start_date=%s AND scale=%s " \
              "AND detection_system=%s AND direction=%s"


def step_audits(conn) -> bool:
    a = run_audits(conn)
    print("audits:", a, flush=True)
    ok = (a["phantom_moves"] == 0 and a["open_move_violations"] == 0
          and a["magnitude_inconsistencies"] == 0 and a["cross_domain_span_ids"] == 0)
    if not ok:
        print("AUDIT FAILURE — investigate before trusting the catalog", file=sys.stderr)
    return ok


def step_significance(conn) -> None:
    df = pd.DataFrame(conn.execute(
        "SELECT id_domain, ticker_id, start_date, scale, detection_system, direction, "
        "total_pct_gain, resolved_date, is_open FROM gws.moves WHERE run_id=%s",
        (RUN_ID,)).fetchall())
    df["total_pct_gain"] = df["total_pct_gain"].astype(float)
    n_upd = 0
    with conn.cursor() as cur:
        for (_, scale, _), g in df.groupby(["detection_system", "scale", "direction"]):
            pct, basis = assign(g, "expanding")
            rows = [(None if np.isnan(pct[i]) else float(pct[i]), basis[i],
                     g.at[i, "id_domain"], int(g.at[i, "ticker_id"]), g.at[i, "start_date"],
                     g.at[i, "scale"], g.at[i, "detection_system"], g.at[i, "direction"])
                    for i in g.index]
            cur.executemany(
                f"UPDATE gws.moves SET magnitude_pctile=%s, pctile_basis=%s WHERE {NATURAL_KEY}",
                rows)
            n_upd += len(rows)
            resolved = g[~g["is_open"]]
            print(f"  significance {scale:9} n={len(g):>6} resolved={len(resolved):>6} "
                  f"p99_gain={resolved['total_pct_gain'].quantile(0.99):8.2f}", flush=True)
    print(f"significance updated on {n_upd} moves (expanding, same-scale comparison set)")


def step_clustering(conn) -> dict:
    df = pd.DataFrame(conn.execute(
        "SELECT id_domain, ticker_id, start_date, scale, detection_system, direction, "
        "total_pct_gain, duration_days, smoothness_metric, max_intra_drawdown "
        "FROM gws.moves WHERE run_id=%s AND scale=%s AND NOT is_open "
        "AND smoothness_metric IS NOT NULL", (RUN_ID, PRIMARY_SCALE)).fetchall())
    for c in ("total_pct_gain", "duration_days", "smoothness_metric", "max_intra_drawdown"):
        df[c] = df[c].astype(float)
    X = zscore(np.column_stack([
        np.log1p(df["total_pct_gain"].to_numpy()),
        np.log1p(df["duration_days"].to_numpy()),
        df["smoothness_metric"].to_numpy()]))
    clusterer = make_hdbscan()
    labels = clusterer(X)
    stab = cluster_stability(X, clusterer, n_boot=50, seed=20260719)
    rep = resolve_representation(X, clusterer, labels, n_boot=50, seed=20260719)
    print(f"clustering: n={len(df)} clusters={stab['n_clusters']} "
          f"noise={int((labels == -1).sum())} ARI={stab['mean_adj_rand_index']:.3f} "
          f"verdict={stab['stability_verdict']} representation={rep['representation']}",
          flush=True)

    with conn.cursor() as cur:
        cur.execute("INSERT INTO gws.cluster_stability (detection_system, input_dimensions, "
                    "n_clusters, n_bootstrap_samples, mean_adj_rand_index, mean_variation_info, "
                    "stability_verdict, notes) VALUES ('mfe', %s, %s, %s, %s, %s, %s, %s)",
                    (INPUT_DIMS, stab["n_clusters"], stab["n_bootstrap_samples"],
                     stab["mean_adj_rand_index"], stab["mean_variation_info"],
                     stab["stability_verdict"],
                     f"run_id={RUN_ID}; scale={PRIMARY_SCALE}; representation="
                     f"{rep['representation']}; noise={int((labels == -1).sum())}"))
        cur.execute("DELETE FROM gws.move_clusters WHERE detection_system='mfe' "
                    "AND input_dimensions=%s", (INPUT_DIMS,))
        cur.executemany(
            f"UPDATE gws.moves SET cluster_id=%s, cluster_label=%s WHERE {NATURAL_KEY}",
            [(None if labels[j] < 0 else int(labels[j]),
              "noise" if labels[j] < 0 else f"c{int(labels[j])}",
              df.at[i, "id_domain"], int(df.at[i, "ticker_id"]), df.at[i, "start_date"],
              df.at[i, "scale"], df.at[i, "detection_system"], df.at[i, "direction"])
             for j, i in enumerate(df.index)])
        if rep["representation"] == "discrete":
            for cid in sorted(set(labels) - {-1}):
                m = df[labels == cid]
                cur.execute(
                    "INSERT INTO gws.move_clusters (cluster_id, cluster_label, detection_system, "
                    "input_dimensions, magnitude_p25, magnitude_p50, magnitude_p75, duration_p25, "
                    "duration_p50, duration_p75, drawdown_p50, smoothness_p50, n_moves, "
                    "stability_score) VALUES (%s,%s,'mfe',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (int(cid), f"c{int(cid)}", INPUT_DIMS,
                     *[float(m["total_pct_gain"].quantile(q)) for q in (0.25, 0.5, 0.75)],
                     *[float(m["duration_days"].quantile(q)) for q in (0.25, 0.5, 0.75)],
                     float(m["max_intra_drawdown"].quantile(0.5)),
                     float(m["smoothness_metric"].quantile(0.5)),
                     len(m), stab["mean_adj_rand_index"]))
    return {"stability": stab, "representation": rep}


def main() -> int:
    import psycopg
    from psycopg.rows import dict_row
    from ka_lib import config as cfg

    conn = psycopg.connect(cfg.load().local_db_url, row_factory=dict_row, autocommit=True)
    if not step_audits(conn):
        return 1
    step_significance(conn)
    step_clustering(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
