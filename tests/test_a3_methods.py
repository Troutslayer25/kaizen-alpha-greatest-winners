import numpy as np

from gws.phase_a3.neutralization import (
    factor_neutralize, industry_neutralize, effect_retention,
)
from gws.phase_a3.decay import information_coefficient, pretrough_actionable
from gws.phase_a3.mutual_info import feature_mutual_info


def _world(seed=0, n=600):
    rng = np.random.default_rng(seed)
    factor = rng.normal(0, 1, n)
    indep = rng.normal(0, 1, n)
    target = 0.6 * factor + 0.6 * indep + rng.normal(0, 0.3, n)
    return rng, factor, indep, target, n


def test_factor_proxy_loses_power():
    rng, factor, indep, target, n = _world(1)
    proxy = 3 * factor + rng.normal(0, 0.05, n)          # essentially the factor
    resid = factor_neutralize(proxy, factor)
    assert effect_retention(proxy, resid, target) < 0.3   # a proxy collapses after neutralization


def test_independent_signal_survives():
    rng, factor, indep, target, n = _world(2)
    feat = 2 * indep + rng.normal(0, 0.05, n)            # uncorrelated with the factor
    resid = factor_neutralize(feat, factor)
    assert effect_retention(feat, resid, target) > 0.7    # genuine signal survives


def test_industry_neutralize_removes_industry_effect():
    rng = np.random.default_rng(3)
    n = 600
    industry = rng.integers(0, 5, n)
    ind_means = rng.normal(0, 1, 5)
    feat = ind_means[industry] + rng.normal(0, 0.01, n)   # almost pure industry effect
    resid = industry_neutralize(feat, industry)
    assert resid.std() < 0.1 * feat.std()                 # industry component removed


def test_mutual_info_separates_signal_from_null():
    rng = np.random.default_rng(4)
    n = 800
    signal = rng.normal(0, 1, n)
    null = rng.normal(0, 1, n)
    y = (signal + rng.normal(0, 0.3, n) > 0).astype(int)
    mi = feature_mutual_info(np.column_stack([signal, null]), y, discrete_target=True)
    assert mi[0] > mi[1]
    assert mi[1] < 0.05


def test_information_coefficient_signal_vs_null():
    rng = np.random.default_rng(5)
    n = 600
    feat = rng.normal(0, 1, n)
    target = feat + rng.normal(0, 0.5, n)
    sig = information_coefficient(feat, target)
    null = information_coefficient(rng.normal(0, 1, n), target)
    assert sig["ic"] > 0.3 and sig["pvalue"] < 0.01
    assert abs(null["ic"]) < 0.15


def test_pretrough_actionability_rejects_hindsight_feature():
    rng = np.random.default_rng(6)
    n = 600
    target = rng.normal(0, 1, n)
    good = {h: 0.5 * target + rng.normal(0, 0.5, n) for h in (0, 5, 10, 20, 30)}
    bad = {0: target.copy()}
    bad.update({h: rng.normal(0, 1, n) for h in (5, 10, 20, 30)})   # signal only at the trough
    assert pretrough_actionable(good, target)[0] is True
    assert pretrough_actionable(bad, target)[0] is False
