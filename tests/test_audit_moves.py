"""Catalog audit predicate cores (pure)."""
import json

from gws.phase_a1.audit_moves import (cross_domain_span_ids, magnitude_consistency_violations,
                                      null_coverage, open_move_violations, phantom_move_rows)


def test_phantom_move_canary():
    rows = [{"total_pct_gain": 0.9}, {"total_pct_gain": 5000.0}, {"total_pct_gain": None}]
    assert len(phantom_move_rows(rows)) == 2


def test_open_move_violations():
    rows = [{"ticker_id": 1, "scale": "trail_6", "detection_system": "mfe", "is_open": True},
            {"ticker_id": 1, "scale": "trail_6", "detection_system": "mfe", "is_open": True},
            {"ticker_id": 1, "scale": "trail_2", "detection_system": "mfe", "is_open": True}]
    v = open_move_violations(rows)
    assert v == {(1, "trail_6", "mfe"): 2}               # two opens at one scale = ATR-poison flag


def test_magnitude_consistency():
    rows = [{"total_pct_gain": 0.9, "descriptors": json.dumps({"magnitude": 0.9})},
            {"total_pct_gain": 0.9, "descriptors": json.dumps({"magnitude": 0.5})}]  # inconsistent
    assert len(magnitude_consistency_violations(rows)) == 1


def test_cross_domain_span_probe():
    exc = [{"ticker_id": 42, "source": "fmp"}, {"ticker_id": 42, "source": "norgate"},
           {"ticker_id": 7, "source": "fmp"}]
    assert cross_domain_span_ids(exc) == {42}            # 42 collides across ID domains


def test_null_coverage():
    rows = [{"inception": json.dumps({"incept_above_sma200": 1.0})},
            {"inception": json.dumps({"incept_above_sma200": None})}]
    cov = null_coverage(rows, "inception", ["incept_above_sma200"])
    assert cov["incept_above_sma200"] == 0.5
