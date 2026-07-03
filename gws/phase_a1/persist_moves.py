"""Persist detected + characterized moves into gws.moves (Phase A1 materialization).

Turns the [FORWARD] "detector output -> queryable catalog" step into code. For each detected
MoveMFE it computes the full characterization (gws.phase_a1.move_characterization) and the PIT
inception context, maps bar indices to calendar dates, and upserts a gws.moves row keyed on the
natural key (ticker_id, start_date, scale, detection_system) so re-persisting is idempotent.

The pure core (`move_to_row`) is unit-tested without a DB; `persist_moves` does the DB write with
a lazy ka_lib import. Significance percentile (magnitude_pctile) and regime context are filled by
later steps (gws.phase_a1.significance, the regime join), not here."""
from __future__ import annotations

import json
import math

import numpy as np

from gws.phase_a1.move_characterization import characterize_move, inception_context

# Methodology version stamped into both JSONB bags (review F7): bump on ANY formula/window/threshold
# change so a partial re-characterization never silently mixes conventions. Re-characterize is cheap.
CHAR_VERSION = "a1.0"


def _clean(v):
    """Recursively coerce a value to JSON/JSONB-safe form (review m-5): NaN/Inf -> None, numpy
    scalars -> Python scalars, nested dict/list handled — so a future descriptor returning
    np.int64/np.bool_/nested structures can never crash json.dumps or Postgres NUMERIC/JSONB."""
    if isinstance(v, (np.floating, float)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, np.ndarray)):
        return [_clean(x) for x in v]
    return v


def _json_safe(d: dict) -> dict:
    """Make a dict valid JSONB (NaN/Inf -> None, numpy -> Python, nested-safe)."""
    return {k: _clean(v) for k, v in d.items()}


def move_to_row(move, ticker_id, index_to_date, descriptors: dict, inception: dict, *,
                is_primary_scale: bool, id_domain: str = "norgate") -> dict:
    """Map a MoveMFE + its characterization to a gws.moves row dict. `index_to_date` maps a bar
    index to a calendar date (date object). `id_domain` (review C1) tags the ID domain so a
    cross-domain persist can never collide on the natural key."""
    return {
        "id_domain": id_domain,
        "ticker_id": int(ticker_id),
        "start_date": index_to_date(int(move.trough_idx)),
        "peak_date": index_to_date(int(move.peak_idx)),
        "resolved_date": (index_to_date(int(move.resolved_idx))     # stop-fire date; NULL if open (C-2)
                          if getattr(move, "resolved_idx", None) is not None else None),
        "total_pct_gain": float(move.magnitude),
        "duration_days": int(move.duration_days),
        "smoothness_metric": float(move.smoothness),
        "early_smoothness": float(move.early_smoothness),
        "drawdown_timing": float(move.drawdown_timing),
        "mae": float(move.mae),
        "max_intra_drawdown": descriptors.get("max_intra_drawdown"),
        "detection_system": "mfe",
        "scale": move.scale,
        "trail_atr": float(move.trail_atr),
        "is_primary_scale": bool(is_primary_scale),
        "is_open": bool(move.is_open),
        "descriptors": json.dumps({**_json_safe(descriptors), "_char_version": CHAR_VERSION}),
        "inception": json.dumps({**_json_safe(inception), "_char_version": CHAR_VERSION}),
    }


def build_rows(moves, ticker_id, dates, close, high=None, low=None, volume=None,
               bench_close=None, open_=None, *, primary_scale: str | None = None,
               id_domain: str = "norgate") -> list[dict]:
    """Characterize every move for one ticker/scale and return gws.moves row dicts.

    All series MUST be aligned to `dates` (same length, same trading-date vector). A misaligned
    benchmark makes b[i] a future calendar date while staying index-PIT — a look-ahead the
    index-based invariance test cannot see (review F2/m-8). Enforced here."""
    n = len(dates)
    for name, arr in (("close", close), ("high", high), ("low", low), ("volume", volume),
                      ("bench_close", bench_close), ("open_", open_)):
        if arr is not None and len(arr) != n:
            raise ValueError(f"build_rows: {name} length {len(arr)} != dates length {n} — every "
                             f"series must be aligned to the ticker's own trading-date vector")

    def idx_to_date(i):
        return dates[i]
    rows = []
    for m in moves:
        desc = characterize_move(m, close, high, low, volume=volume, bench_close=bench_close,
                                 open_=open_)
        inc = inception_context(m, close, high, low, volume=volume, bench_close=bench_close)
        rows.append(move_to_row(m, ticker_id, idx_to_date, desc, inc, id_domain=id_domain,
                                is_primary_scale=(primary_scale is not None and m.scale == primary_scale)))
    return rows


def persist_moves(conn, ticker_id, moves, dates, close, high=None, low=None, volume=None,
                  bench_close=None, open_=None, *, primary_scale: str | None = None,
                  detection_system: str = "mfe", detect_params: dict | None = None,
                  run_id: str | None = None, id_domain: str = "norgate") -> int:
    """Characterize + persist a ticker's ENTIRE current move set into gws.moves.

    DELETE-before-insert per (id_domain, ticker_id, detection_system) in one transaction (review
    F4/M-1): upsert-only would orphan stale moves when a data correction shifts a trough by a day
    (the step_02 orphan bug). `moves` must be ALL scales detected for this ticker on the current
    clean series, computed from COMPLETE inputs — a re-persist REPLACES the whole set, so calling
    it with an optional feed (volume/bench) missing writes NULL families and there is no merge to
    save you (review M3: the DELETE runs first, so ON CONFLICT can only fire on an intra-batch
    natural-key duplicate — which would itself be a bug, not something to silently merge)."""
    rows = build_rows(moves, ticker_id, dates, close, high, low, volume, bench_close, open_,
                      primary_scale=primary_scale, id_domain=id_domain)
    dp = json.dumps(detect_params) if detect_params is not None else None
    for r in rows:                                       # detection provenance (Lineage m-10)
        r["detect_params"] = dp
        r["run_id"] = run_id
    cols = list(rows[0].keys()) if rows else []
    key = ("id_domain", "ticker_id", "start_date", "scale", "detection_system")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gws.moves WHERE id_domain=%s AND ticker_id=%s AND detection_system=%s",
                    (id_domain, ticker_id, detection_system))
        if not rows:
            return 0
        placeholders = ", ".join(f"%({c})s" for c in cols)
        sets = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in key)
        sql = (f"INSERT INTO gws.moves ({', '.join(cols)}) VALUES ({placeholders}) "
               f"ON CONFLICT ({', '.join(key)}) DO UPDATE SET " + sets)
        cur.executemany(sql, rows)
    return len(rows)
