"""Lineage: Step-0 required-depth gate logic (pure)."""
from gws.phase0.verify_norgate_index_coverage import meets_required_start


def test_required_start_gate():
    assert meets_required_start("1987-03-01", "1990-01-01")      # deep enough
    assert not meets_required_start("2005-06-01", "1990-01-01")  # too shallow -> NO-GO
    assert not meets_required_start(None, "1990-01-01")          # no membership found -> fail
