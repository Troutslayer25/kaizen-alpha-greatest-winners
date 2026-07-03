"""C-2: the corrected emotional-invariance transfer instrument."""
import numpy as np

from gws.regime.transfer_test import (invariance_supported, regime_relative_normalize,
                                      transfer_distribution, transfer_ratio)


def _auc(Xtr, ytr, Xte, yte):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    Xtr = np.asarray(Xtr, float).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte, float).reshape(len(Xte), -1)
    m = LogisticRegression().fit(Xtr, ytr)
    return float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))


def test_regime_relative_normalize_zscore_per_era():
    v = np.array([10.0, 12.0, 14.0, 100.0, 102.0, 104.0])   # era 1 ~10s, era 2 ~100s
    era = np.array([1, 1, 1, 2, 2, 2])
    z = regime_relative_normalize(v, era)
    assert abs(z[:3].mean()) < 1e-9 and abs(z[3:].mean()) < 1e-9   # each era centered
    assert np.allclose(z[:3], z[3:])                              # identical shape, era-relative


def test_transfer_ratio_math():
    assert transfer_ratio(0.7, 0.7) == 1.0
    assert transfer_ratio(0.5, 0.7) == 0.0
    assert np.isnan(transfer_ratio(0.7, 0.5))     # no in-era skill -> undefined


def test_invariance_rule_needs_majority_across_min_pairs():
    emo = [0.9, 0.8, 0.85, 0.7]
    struct = [0.1, -0.2, 0.0, 0.3]
    out = invariance_supported(emo, struct)
    assert out["supported"] and out["emotional_wins"] == 4
    # too few pairs -> not supported even if emotional wins
    assert not invariance_supported([0.9, 0.8], [0.1, 0.0])["supported"]


def test_end_to_end_emotional_transfers_structural_does_not():
    rng = np.random.default_rng(0)
    eras, per = [0, 1, 2], 400
    emo_all, struct_all, y_all, era_all = [], [], [], []
    for e in eras:
        emo = rng.normal(0, 1, per)
        y = (emo + rng.normal(0, 0.5, per) > 0).astype(int)
        sign = 1.0 if e % 2 == 0 else -1.0            # structural relationship flips by era
        struct = sign * emo + rng.normal(0, 0.2, per)
        emo_all.append(emo); struct_all.append(struct); y_all.append(y)
        era_all.append(np.full(per, e))
    emo_all = np.concatenate(emo_all); struct_all = np.concatenate(struct_all)
    y_all = np.concatenate(y_all); era_all = np.concatenate(era_all)

    emo_dist = transfer_distribution(_auc, emo_all, y_all, era_all)
    struct_dist = transfer_distribution(_auc, struct_all, y_all, era_all)
    assert emo_dist["median"] > 0.7                   # emotional feature transfers
    assert struct_dist["median"] < 0.3                # structural feature does not

    out = invariance_supported(list(emo_dist["pairwise"].values()),
                               list(struct_dist["pairwise"].values()))
    assert out["supported"]
