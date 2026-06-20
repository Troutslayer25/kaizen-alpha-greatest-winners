import numpy as np

from gws.synthetic.generate import generate_panel, MIN_START_GAP
from gws.phase_a1.trough_detector import detect_moves


def test_generator_is_deterministic_and_shaped():
    p1, t1 = generate_panel(n_tickers=3, n_days=1500, seed=1, planted_per_ticker=2)
    p2, t2 = generate_panel(n_tickers=3, n_days=1500, seed=1, planted_per_ticker=2)
    assert len(p1) == 3 * 1500
    assert p1["close"].equals(p2["close"])           # deterministic under seed
    assert len(t1) == 6                              # 3 tickers x 2 planted moves
    assert {"planted_signal", "null_feature"}.issubset(p1.columns)


def test_planted_starts_respect_min_spacing():
    _, truth = generate_panel(n_tickers=8, n_days=2520, seed=3, planted_per_ticker=3)
    for _, grp in truth.groupby("ticker_id"):
        days = np.sort(grp["trough_day"].to_numpy())
        if len(days) > 1:
            assert np.all(np.diff(days) >= MIN_START_GAP - 30)  # troughs are well separated


def test_adversarial_panel_is_messier_but_still_scoreable():
    clean, t_clean = generate_panel(n_tickers=4, n_days=1500, seed=2, planted_per_ticker=2)
    adv, t_adv = generate_panel(n_tickers=4, n_days=1500, seed=2, planted_per_ticker=2,
                                adversarial=True)
    # same planting structure (same seed) -> same number of planted moves, re-derived troughs
    assert len(t_adv) == len(t_clean)
    # adversarial paths are genuinely rougher (higher daily-return dispersion)
    clean_std = clean.groupby("ticker_id")["close"].apply(lambda c: c.pct_change().std()).mean()
    adv_std = adv.groupby("ticker_id")["close"].apply(lambda c: c.pct_change().std()).mean()
    assert adv_std > clean_std


def test_signal_recovers_under_adversarial_noise():
    # The whole point: A3 must still isolate the planted signal from the null when the data
    # is actively messy. Use the planted realized-volatility contraction as the signal proxy.
    from gws.phase_a3.mutual_info import feature_mutual_info
    adv, _ = generate_panel(n_tickers=8, n_days=2000, seed=4, planted_per_ticker=3,
                            adversarial=True)
    # per-row 10-day realized vol (low before a planted move = signal); null is the noise col
    sig, null, y = [], [], []
    for tk, sub in adv.groupby("ticker_id"):
        sub = sub.sort_values("date")
        rv = sub["close"].pct_change().rolling(10).std().to_numpy()
        lab = sub["planted_signal"].to_numpy()
        nf = sub["null_feature"].to_numpy()
        m = ~np.isnan(rv)
        sig.append(-rv[m]); null.append(nf[m]); y.append(lab[m])     # -rv: contraction -> high
    X = np.column_stack([np.concatenate(sig), np.concatenate(null)])
    yv = (np.concatenate(y) > 0).astype(int)
    mi = feature_mutual_info(X, yv, discrete_target=True)
    assert mi[0] > mi[1]                       # signal still beats null under chaos
    assert mi[0] > 0.01


def test_detector_localizes_planted_troughs():
    # Real recall test: detected trough must land near the planted trough, not just
    # "some move exists". start_date is the feature-extraction anchor, so localization
    # is what matters.
    panel, truth = generate_panel(n_tickers=6, n_days=2200, seed=7, planted_per_ticker=2)
    hits, total = 0, 0
    for tk, grp in truth.groupby("ticker_id"):
        sub = panel[panel["ticker_id"] == tk]
        troughs = [m.trough_idx for m in detect_moves(
            sub["high"].to_numpy(), sub["low"].to_numpy(), sub["close"].to_numpy())]
        for trough_day in grp["trough_day"]:
            total += 1
            if any(abs(td - trough_day) <= 20 for td in troughs):
                hits += 1
    assert total > 0
    assert hits / total >= 0.5, f"localization recall too low: {hits}/{total}"
