import numpy as np
import pandas as pd

from gws.phase_a3.univariate import univariate_screen
from gws.phase0.liquidity_floor import discover_floor, knee_index


def test_univariate_screen_separates_signal_from_null():
    rng = np.random.default_rng(0)
    n = 400
    labels = np.array([1] * 200 + [0] * 200)
    signal = np.concatenate([rng.normal(1.0, 1.0, 200), rng.normal(0.0, 1.0, 200)])
    null = rng.normal(0.0, 1.0, n)
    fm = pd.DataFrame({"signal": signal, "null": null})

    res = univariate_screen(fm, labels)
    sig = res[res["feature"] == "signal"].iloc[0]
    nul = res[res["feature"] == "null"].iloc[0]
    assert sig["significant"] and sig["qvalue"] < 0.05
    assert abs(sig["cohens_d"]) > 0.5
    assert not nul["significant"]


def test_univariate_fdr_controls_false_positives():
    # 50 pure-null features -> BH should flag essentially none as significant.
    rng = np.random.default_rng(1)
    n = 300
    labels = np.array([1] * 150 + [0] * 150)
    fm = pd.DataFrame({f"f{i}": rng.normal(0, 1, n) for i in range(50)})
    res = univariate_screen(fm, labels)
    assert res["significant"].sum() <= 2          # FDR keeps false positives near zero


def test_knee_separates_liquidity_tiers():
    # v2: the knee is a non-gating liquidity-TIER bucketing utility (NOT a universe gate).
    # It should land between a low-ADV mass and a high-ADV mass.
    rng = np.random.default_rng(2)
    low_tier = rng.lognormal(np.log(1e5), 0.3, 500)     # ~$100k ADV bucket
    high_tier = rng.lognormal(np.log(5e7), 0.5, 2000)   # ~$50M ADV bucket
    knee = discover_floor(np.concatenate([low_tier, high_tier]))
    assert np.median(low_tier) < knee < np.median(high_tier)


def test_knee_index_on_elbow_curve():
    # A convex elbow: knee should land away from both endpoints.
    curve = np.concatenate([np.linspace(0, 1, 50), np.linspace(1, 10, 50)])
    k = knee_index(curve)
    assert 10 < k < 90
