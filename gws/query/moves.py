"""Composable query layer over the move catalog (gws.moves) — ad-hoc, unforeseen analysis.

The classification goal is only useful if the catalog is easy to interrogate later. `MoveQuery`
builds a parameterized SQL query by chaining predicates over the typed columns AND the descriptor
/ inception JSONB bags, so a move population can be sliced by:
  * WHAT THE TAPE LOOKED LIKE AT INCEPTION (PIT, bias-free): .above_ma(200), .inception('incept_rsi_14','<',30)
  * MOVE SHAPE/STRUCTURE (post-hoc): .descriptor('num_pullbacks','<=',1), .magnitude_between(1.0, None)
  * CLUSTER / REGIME / SCALE: .cluster(3), .regime('risk_on'), .primary_scale_only()
  * THEME (thematic comparison): .tickers_in(theme_member_ids)  # pass a theme/sector's ticker_ids
  * TIME: .date_range(a, b)

The builder is pure (emits SQL + params) and unit-tested without a DB; `.run(conn)` executes it.
Operators are whitelisted, and JSONB field names are passed as bound parameters, so predicates are
injection-safe.

    q = MoveQuery().above_ma(200).descriptor('num_pullbacks', '<=', 1).magnitude_between(1.0, None)
    rows = q.run(conn)                        # "tight, above-200MA-at-inception, 100%+ winners"
"""
from __future__ import annotations

_OPS = {"<", "<=", ">", ">=", "=", "!=", "<>"}
# order_by/select are interpolated (not bindable), so restrict them to a known column set (m-4).
_COLUMNS = {"move_id", "ticker_id", "start_date", "peak_date", "total_pct_gain", "duration_days",
            "smoothness_metric", "early_smoothness", "drawdown_timing", "mae", "max_intra_drawdown",
            "detection_system", "scale", "trail_atr", "is_primary_scale", "is_open", "cluster_id",
            "cluster_label", "context_score", "context_label", "magnitude_pctile", "pctile_basis",
            "descriptors", "inception", "detect_params", "run_id"}


class MoveQuery:
    def __init__(self):
        self._where: list[str] = []
        self._params: list = []
        self._order: str | None = None
        self._limit: int | None = None
        # True once any OUTCOME (post-hoc) predicate is added (review F5). An analysis that turns
        # query rows into observations/features/signals must assert this is False (or route through
        # setup_labels/matched_controls) — filtering moves by their own future is selection bias.
        self.uses_outcome_filters = False

    # --- typed-column predicates ------------------------------------------------------------
    def ticker(self, ticker_id):
        self._where.append("ticker_id = %s"); self._params.append(ticker_id); return self

    def tickers_in(self, ticker_ids):
        ids = list(ticker_ids)
        self._where.append("ticker_id = ANY(%s)"); self._params.append(ids); return self

    def date_range(self, start=None, end=None):
        if start is not None:
            self._where.append("start_date >= %s"); self._params.append(start)
        if end is not None:
            self._where.append("start_date <= %s"); self._params.append(end)
        return self

    def magnitude_between(self, lo=None, hi=None):
        self.uses_outcome_filters = True                 # magnitude is a post-hoc outcome
        if lo is not None:
            self._where.append("total_pct_gain >= %s"); self._params.append(lo)
        if hi is not None:
            self._where.append("total_pct_gain <= %s"); self._params.append(hi)
        return self

    def duration_between(self, lo=None, hi=None):
        self.uses_outcome_filters = True                 # duration is a post-hoc outcome
        if lo is not None:
            self._where.append("duration_days >= %s"); self._params.append(lo)
        if hi is not None:
            self._where.append("duration_days <= %s"); self._params.append(hi)
        return self

    def cluster(self, cluster_id):
        # cluster_id is fit on post-hoc move shape (magnitude/duration/path), so filtering by it is
        # outcome selection exactly like .descriptor() (PHASE_A1_PRECOMMIT §3) — set the tripwire.
        self.uses_outcome_filters = True
        self._where.append("cluster_id = %s"); self._params.append(cluster_id); return self

    def regime(self, label):
        self._where.append("context_label = %s"); self._params.append(label); return self

    def primary_scale_only(self):
        self._where.append("is_primary_scale = TRUE"); return self

    def scale(self, scale):
        self._where.append("scale = %s"); self._params.append(scale); return self

    def significant_above(self, pctile):
        # outcome-derived AND only valid under the CF-3 rule — require a non-full-sample basis.
        self.uses_outcome_filters = True
        self._where.append("magnitude_pctile >= %s AND pctile_basis IS NOT NULL "
                           "AND pctile_basis <> 'full_sample'")
        self._params.append(pctile); return self

    # --- JSONB predicates (descriptor = post-hoc shape; inception = PIT tape-state) ----------
    # NULL SEMANTICS (review M-3): (bag->>k)::numeric is NULL when the key is absent/NaN, so a
    # predicate silently EXCLUDES those moves from BOTH sides — .above_ma(200) and .below_ma(200)
    # do NOT partition (moves with <200 bars of history, the IPO/young-leader profile, vanish from
    # both). Use .has()/.missing() to make availability explicit.
    def _jsonb(self, bag, field, op, value):
        if op not in _OPS:
            raise ValueError(f"operator {op!r} not allowed")
        self._where.append(f"({bag} ->> %s)::numeric {op} %s")
        self._params.extend([field, value]); return self

    def has(self, field, bag="inception"):
        self._where.append(f"({bag} ->> %s) IS NOT NULL"); self._params.append(field); return self

    def missing(self, field, bag="inception"):
        self._where.append(f"({bag} ->> %s) IS NULL"); self._params.append(field); return self

    def descriptor(self, field, op, value):
        self.uses_outcome_filters = True                 # descriptors are post-hoc outcomes
        return self._jsonb("descriptors", field, op, value)

    def inception(self, field, op, value):
        return self._jsonb("inception", field, op, value)

    def above_ma(self, period: int):
        """Moves that began ABOVE the `period`-day SMA (PIT tape-state at the trough)."""
        return self.inception(f"incept_price_to_sma{period}", ">", 0)

    def below_ma(self, period: int):
        return self.inception(f"incept_price_to_sma{period}", "<", 0)

    # --- terminal ---------------------------------------------------------------------------
    def order_by(self, expr, desc=True):
        if expr not in _COLUMNS:
            raise ValueError(f"order_by column {expr!r} not allowed")
        self._order = f"{expr} {'DESC' if desc else 'ASC'}"; return self

    def limit(self, n):
        self._limit = int(n); return self

    def build(self, select: str = "*"):
        if select != "*":
            bad = [c.strip() for c in select.split(",") if c.strip() not in _COLUMNS]
            if bad:
                raise ValueError(f"select columns not allowed: {bad}")
        sql = f"SELECT {select} FROM gws.moves"
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        if self._order:
            sql += f" ORDER BY {self._order}"
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        return sql, list(self._params)

    def run(self, conn, select: str = "*"):
        sql, params = self.build(select)
        return conn.execute(sql, params).fetchall()
