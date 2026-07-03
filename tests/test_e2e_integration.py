"""End-to-end integration: the full analytical spine recovers a planted signal and stays null-safe."""
from gws.validation.e2e_integration import run_e2e


def test_pipeline_recovers_planted_signal_and_rejects_nulls():
    r = run_e2e(seed=0, n_tickers=12, n_days=900)
    assert r["detection_recall"] >= 0.8                  # detection recovers the planted troughs
    assert r["n_positive"] > 0                           # labeling produced positives
    assert r["planted_significant"]                      # the pipeline RECOVERS the planted signal
    assert not r["null_significant"]                     # and does NOT flag the null feature
    assert not r["planted_significant_under_shuffle"]    # signal vanishes under a null -> no leak
