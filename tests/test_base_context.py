"""MC-2: PIT base/stage context — stage logic, MA stack, and forward-invariance."""
import numpy as np

from gws.phase_a1.base_context import BASE_FIELDS, base_context


def test_stage2_uptrend_above_rising_200ma():
    close = np.linspace(50, 150, 300)                    # steady advance: above a rising 200-day
    ctx = base_context(close, 299)
    assert ctx["incept_stage"] == 2.0
    assert ctx["incept_ma_stack"] == 1.0                 # 50 > 150 > 200 in an uptrend


def test_stage4_downtrend_below_falling_200ma():
    close = np.linspace(150, 50, 300)                    # steady decline: below a falling 200-day
    ctx = base_context(close, 299)
    assert ctx["incept_stage"] == 4.0
    assert ctx["incept_ma_stack"] == 0.0


def test_days_since_high_low_and_prior_leg():
    rng = np.random.default_rng(0)
    close = np.concatenate([np.linspace(50, 120, 200), np.linspace(120, 100, 100)])  # peak at 199
    ctx = base_context(close, 299)
    assert ctx["incept_days_since_252high"] == 100.0     # peak was 100 bars ago
    assert ctx["incept_prior_leg_gain"] > 0.5            # a real prior up-leg (within the 252 window)


def test_base_context_is_future_invariant():
    rng = np.random.default_rng(1)
    close = np.abs(100 * np.cumprod(1 + rng.normal(0, 0.01, 400)))
    i = 300
    base = base_context(close, i)
    mut = close.copy(); mut[i + 1:] *= rng.uniform(0.3, 2.0, len(close) - i - 1)
    after = base_context(mut, i)
    for k in BASE_FIELDS:
        assert (np.isnan(base[k]) and np.isnan(after[k])) or base[k] == after[k]
