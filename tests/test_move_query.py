"""Query layer: composable, injection-safe SQL over the move catalog (pure build)."""
import pytest

from gws.query.moves import MoveQuery


def test_inception_and_shape_and_magnitude_compose():
    sql, params = (MoveQuery()
                   .above_ma(200)
                   .descriptor("num_pullbacks", "<=", 1)
                   .magnitude_between(1.0, None)
                   .primary_scale_only()
                   .order_by("total_pct_gain").limit(50)
                   .build())
    assert "(inception ->> %s)::numeric > %s" in sql
    assert "(descriptors ->> %s)::numeric <= %s" in sql
    assert "total_pct_gain >= %s" in sql and "is_primary_scale = TRUE" in sql
    assert "ORDER BY total_pct_gain DESC" in sql and "LIMIT 50" in sql
    assert params == ["incept_price_to_sma200", 0, "num_pullbacks", 1, 1.0]


def test_thematic_and_time_slice():
    sql, params = MoveQuery().tickers_in([1, 2, 3]).date_range("2020-01-01", "2021-01-01").build()
    assert "ticker_id = ANY(%s)" in sql and "start_date >= %s" in sql and "start_date <= %s" in sql
    assert params == [[1, 2, 3], "2020-01-01", "2021-01-01"]


def test_operator_whitelist_blocks_injection():
    with pytest.raises(ValueError):
        MoveQuery().descriptor("num_pullbacks", "; DROP TABLE gws.moves; --", 1)


def test_outcome_filter_tripwire():
    # F5: PIT-only slices don't set the flag; any outcome predicate does.
    assert MoveQuery().above_ma(200).inception("incept_rsi_14", "<", 30).uses_outcome_filters is False
    assert MoveQuery().descriptor("num_pullbacks", "<=", 1).uses_outcome_filters is True
    assert MoveQuery().magnitude_between(1.0, None).uses_outcome_filters is True
    assert MoveQuery().cluster(3).uses_outcome_filters is True     # M-4: cluster_id is post-hoc shape


def test_min_trend_quality_filter():
    q = MoveQuery().min_trend_quality(0.6)
    sql, params = q.build()
    assert "(descriptors ->> %s)::numeric >= %s" in sql
    assert params == ["trend_quality", 0.6] and q.uses_outcome_filters is True


def test_has_missing_make_availability_explicit():
    # M-3: NULL semantics — has/missing let the analyst partition instead of silently dropping.
    sql, params = MoveQuery().missing("incept_price_to_sma200").build()
    assert "(inception ->> %s) IS NULL" in sql and params == ["incept_price_to_sma200"]


def test_order_by_and_select_are_column_whitelisted():
    # m-4: order_by/select are interpolated, so only known columns are allowed.
    with pytest.raises(ValueError):
        MoveQuery().order_by("total_pct_gain; DROP TABLE gws.moves")
    with pytest.raises(ValueError):
        MoveQuery().build(select="ticker_id, (SELECT password FROM users)")
    MoveQuery().order_by("total_pct_gain").build(select="ticker_id, total_pct_gain")   # allowed


def test_run_executes_against_a_connection():
    class _Cur:
        def fetchall(self):
            return [{"ticker_id": 7, "total_pct_gain": 1.4}]

    class _Conn:
        def __init__(self):
            self.sql = None; self.params = None
        def execute(self, sql, params):
            self.sql, self.params = sql, params; return _Cur()

    conn = _Conn()
    rows = MoveQuery().ticker(7).above_ma(50).run(conn)
    assert rows[0]["ticker_id"] == 7
    assert "ticker_id = %s" in conn.sql and conn.params[0] == 7
