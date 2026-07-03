"""CF-1: membership keys on assetid and never silently drops delisted constituents."""
import pandas as pd

from gws.phase0.ingest_index_membership import build_interval_rows, close_open_interval


def _series(flags, start="2000-01-03"):
    idx = pd.bdate_range(start, periods=len(flags))
    return pd.DataFrame({"Index Constituent": flags}, index=idx)


def test_delisted_open_interval_closes_at_last_traded_date():
    last = pd.Timestamp("2008-09-15").date()   # e.g. Lehman
    assert close_open_interval(None, is_delisted=True, last_quoted_date=last) == last


def test_current_member_stays_open():
    assert close_open_interval(None, is_delisted=False, last_quoted_date=None) is None


def test_delisted_member_is_ingested_not_dropped():
    # A dead ex-member exists in ka_history (by assetid) but NOT in the FMP tickers table.
    # The old symbol-map path dropped it; the assetid path must keep it.
    entities = {111: {"is_delisted": True, "last_quoted_date": pd.Timestamp("2010-06-30").date()},
                222: {"is_delisted": False, "last_quoted_date": None}}
    assetids = {"DEADCO-201006": 111, "LIVECO": 222}
    series = {"DEADCO-201006": _series([1, 1, 1]), "LIVECO": _series([1, 1, 1])}

    rows, unmapped = build_interval_rows(
        ["DEADCO-201006", "LIVECO"], entities, index_name="sp500",
        constituent_series=series.get, assetid_of=assetids.get)

    by_entity = {r["entity_id"]: r for r in rows}
    assert 111 in by_entity and 222 in by_entity          # delisted name is NOT dropped
    assert by_entity[111]["to_date"] == pd.Timestamp("2010-06-30").date()   # closed at death
    assert by_entity[222]["to_date"] is None               # live member stays open
    assert unmapped == []


def test_unmapped_are_recorded_with_reason_not_dropped_silently():
    entities = {111: {"is_delisted": False, "last_quoted_date": None}}
    assetids = {"KNOWN": 111, "NOASSET": None, "ORPHAN": 999}   # 999 not in ka_history
    series = {"KNOWN": _series([1, 1])}

    rows, unmapped = build_interval_rows(
        ["KNOWN", "NOASSET", "ORPHAN"], entities, index_name="sp500",
        constituent_series=lambda s: series.get(s), assetid_of=assetids.get)

    reasons = dict(unmapped)
    assert reasons["NOASSET"] == "no_assetid"
    assert reasons["ORPHAN"] == "assetid_not_in_ka_history"
    assert [r["entity_id"] for r in rows] == [111]
