import numpy as np
import pandas as pd

from gws.synthetic.generate import generate_panel
from gws.phase_a1.trough_detector import detect_moves
from gws.phase_a1.move_detector_mfe import detect_moves_mfe
from gws.phase_a1.labeling import build_setup_labels
from gws.phase_a2.feature_matrix import build_feature_matrix
from gws.phase_a2.features_price_volume import compute_features
from gws.phase_a2.feature_catalog import catalog_rows
from gws.phase_a3.ml_bakeoff import build_estimators, run_walk_forward
from gws.common.pit_audit import assert_future_invariant

N_DAYS = 2200


def _series_and_bench(panel):
    tickers = sorted(panel["ticker_id"].unique())
    series = {}
    for tk in tickers:
        sub = panel[panel["ticker_id"] == tk].sort_values("date")
        series[tk] = {k: sub[k].to_numpy() for k in ("close", "high", "low", "volume")}
    bench = panel.groupby("date")["adjusted_close"].mean().to_numpy()
    return tickers, series, {tk: bench for tk in tickers}


def test_end_to_end_pipeline_recovers_planted_setups():
    # detector -> forward labels -> feature matrix -> walk-forward ML, on synthetic data
    # with known planted setups. The whole chain must recover the signal out-of-sample.
    panel, truth = generate_panel(n_tickers=6, n_days=N_DAYS, seed=11, planted_per_ticker=2)
    tickers, series, bench_by_ticker = _series_and_bench(panel)

    moves_by_ticker = {tk: detect_moves(series[tk]["high"], series[tk]["low"], series[tk]["close"])
                       for tk in tickers}
    assert sum(len(v) for v in moves_by_ticker.values()) > 0

    K = 20
    labels = build_setup_labels(moves_by_ticker, N_DAYS, forward_window_k=K,
                                sample_every=5, min_index=210)
    assert labels["label"].sum() > 0                     # some positive pre-move setups labeled

    fm = build_feature_matrix(labels[["ticker_id", "as_of_index"]], series,
                              bench_by_ticker=bench_by_ticker)   # includes the generic bank
    fm = fm.dropna(axis=1, how="any")                    # keep features defined at every point
    assert fm.shape[1] >= 8

    # The generic/auto bank must actually be present in the matrix the model consumes,
    # and the catalog cross-tab must be non-trivial (>=1 auto_generated feature) — else the
    # feature-selection-contamination control is defeated (Auditor 4 §28).
    cat = catalog_rows(list(fm.columns), branch="price_volume")
    motivations = {r["feature_name"]: r["motivation"] for r in cat}
    assert any(m == "auto_generated" for m in motivations.values()), "generic bank missing from matrix"
    assert any(m == "practitioner_derived" for m in motivations.values())

    X = fm.to_numpy()
    y = labels["label"].astype(int).to_numpy()
    t = labels["as_of_index"].to_numpy()
    assert not np.isnan(X).any()

    res = run_walk_forward(X, y, t, [1400, 1700, 2000], label_horizon=K,
                           build_estimator=build_estimators()["random_forest"])
    assert res["auc"] > 0.65                             # end-to-end recovery, out-of-sample


def test_mfe_detector_end_to_end():
    # The canonical (MFE) detector must also drive the full pipeline, at a single primary
    # scale (a smoke-test choice; the production scale set is a Phase-A1 pre-commit item).
    panel, _ = generate_panel(n_tickers=6, n_days=N_DAYS, seed=12, planted_per_ticker=2)
    tickers, series, bench_by_ticker = _series_and_bench(panel)

    PRIMARY_SCALE = 15.0
    moves_by_ticker = {
        tk: detect_moves_mfe(series[tk]["high"], series[tk]["low"], series[tk]["close"],
                             trail_atr=PRIMARY_SCALE, min_duration=10)
        for tk in tickers
    }
    assert sum(len(v) for v in moves_by_ticker.values()) > 0

    K = 20
    labels = build_setup_labels(moves_by_ticker, N_DAYS, forward_window_k=K,
                                sample_every=5, min_index=210)
    assert labels["label"].sum() > 0

    fm = build_feature_matrix(labels[["ticker_id", "as_of_index"]], series,
                              bench_by_ticker=bench_by_ticker).dropna(axis=1, how="any")
    X, y, t = fm.to_numpy(), labels["label"].astype(int).to_numpy(), labels["as_of_index"].to_numpy()
    res = run_walk_forward(X, y, t, [1400, 1700, 2000], label_horizon=K,
                           build_estimator=build_estimators()["random_forest"])
    assert res["auc"] > 0.60                             # MFE-driven pipeline recovers signal OOS


def test_features_pit_clean_in_pipeline():
    # The pipeline's features must be future-invariant on real (synthetic) series.
    panel, _ = generate_panel(n_tickers=2, n_days=600, seed=3, planted_per_ticker=1)
    sub = panel[panel["ticker_id"] == 0].sort_values("date")
    s = {k: sub[k].to_numpy() for k in ("close", "high", "low", "volume")}
    bench = panel.groupby("date")["adjusted_close"].mean().to_numpy()
    assert_future_invariant(
        compute_features,
        {"close": s["close"], "high": s["high"], "low": s["low"],
         "volume": s["volume"], "bench_close": bench},
        i=400,
    )
