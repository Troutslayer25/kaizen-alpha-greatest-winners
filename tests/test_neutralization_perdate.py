"""M-4: neutralization must be per-date. A time-varying industry effect is removed by
per-(date,industry) demeaning but survives a pooled (all-time) demean."""
import numpy as np

from gws.phase_a3.neutralization import effect_retention, industry_neutralize


def test_perdate_removes_timevarying_industry_effect_that_pooled_retains():
    rng = np.random.default_rng(0)
    n_dates, n_ind, per_ind = 30, 5, 10
    industry = np.tile(np.repeat(np.arange(n_ind), per_ind), n_dates)
    dates = np.repeat(np.arange(n_dates), n_ind * per_ind)

    feat, targ = [], []
    for _ in range(n_dates):
        eff = rng.normal(0.0, 1.0, n_ind)                 # industry effect varies each date
        base = np.repeat(eff, per_ind)
        feat.append(base + rng.normal(0, 0.05, n_ind * per_ind))
        targ.append(base + rng.normal(0, 0.30, n_ind * per_ind))
    feat = np.concatenate(feat)
    targ = np.concatenate(targ)

    pooled = industry_neutralize(feat, industry)                    # all-time demean
    perdate = industry_neutralize(feat, industry, dates=dates)      # contemporaneous demean

    ret_pooled = effect_retention(feat, pooled, targ)
    ret_perdate = effect_retention(feat, perdate, targ)

    # pooled leaves the date-varying industry structure -> still predicts target; per-date
    # removes it -> residual is noise.
    assert ret_pooled > 0.5
    assert ret_perdate < 0.2
