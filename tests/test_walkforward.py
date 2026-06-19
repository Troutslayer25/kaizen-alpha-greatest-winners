import numpy as np

from gws.common.walkforward import expanding_splits, ticker_disjoint_folds


def test_expanding_splits_purge_and_disjoint_tests():
    t = np.arange(0, 1000)
    K = 20
    folds = list(expanding_splits(t, [600, 700, 800], label_horizon=K, embargo=5))
    assert len(folds) == 3

    train0, test0 = folds[0]
    assert t[test0].min() == 600 and t[test0].max() == 699
    # purge: every training obs's label window must finish before test start
    assert np.all(t[train0] + K < 600)
    # the purge gap [580, 600) contains no training observations
    assert not np.any((t[train0] >= 580) & (t[train0] < 600))
    assert set(train0).isdisjoint(set(test0))

    tests = [set(f[1].tolist()) for f in folds]
    assert tests[0].isdisjoint(tests[1])
    assert tests[1].isdisjoint(tests[2])


def test_final_fold_drops_incomplete_labels():
    t = np.arange(0, 1000)
    K = 20
    folds = list(expanding_splits(t, [800], label_horizon=K, embargo=0))
    _, test = folds[0]
    # final-fold test obs must have a fully-formed forward label (t + K <= max(t))
    assert t[test].max() <= 999 - K


def test_keeping_incomplete_labels_is_opt_in():
    t = np.arange(0, 1000)
    folds = list(expanding_splits(t, [800], label_horizon=20, drop_incomplete_labels=False))
    _, test = folds[0]
    assert t[test].max() == 999


def test_empty_t_yields_no_folds():
    assert list(expanding_splits(np.array([], dtype=int), [10], label_horizon=5)) == []


def test_ticker_disjoint_probe():
    tickers = np.repeat(np.arange(10), 5)
    seen_test = set()
    for train_idx, test_idx in ticker_disjoint_folds(tickers, n_splits=5):
        train_tk = set(tickers[train_idx])
        test_tk = set(tickers[test_idx])
        assert train_tk.isdisjoint(test_tk)
        seen_test |= test_tk
    assert seen_test == set(range(10))
