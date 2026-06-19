import numpy as np
import pandas as pd

from gws.synthetic.generate import generate_panel
from gws.phase_a1.trough_detector import detect_moves
from gws.phase_a1.labeling import build_setup_labels
from gws.phase_a2.feature_matrix import build_feature_matrix
from gws.phase_a2.features_price_volume import compute_features
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
                              bench_by_ticker=bench_by_ticker)
    fm = fm.dropna(axis=1, how="any")                    # keep features defined at every point
    assert fm.shape[1] >= 8
    X = fm.to_numpy()
    y = labels["label"].astype(int).to_numpy()
    t = labels["as_of_index"].to_numpy()
    assert not np.isnan(X).any()

    res = run_walk_forward(X, y, t, [1400, 1700, 2000], label_horizon=K,
                           build_estimator=build_estimators()["random_forest"])
    assert res["auc"] > 0.65                             # end-to-end recovery, out-of-sample


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
