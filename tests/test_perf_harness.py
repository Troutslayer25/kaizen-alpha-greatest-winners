"""Harness B self-test: the scaling-exponent estimator recovers known big-O."""
import numpy as np

from gws.validation.perf_harness import estimate_scaling_exponent, scaling_report


def test_exponent_recovers_linear_and_quadratic():
    assert abs(estimate_scaling_exponent([100, 200, 400], [1.0, 2.0, 4.0]) - 1.0) < 0.05
    assert abs(estimate_scaling_exponent([100, 200, 400], [1.0, 4.0, 16.0]) - 2.0) < 0.05


def test_scaling_report_separates_quadratic_from_linear():
    # Wall-clock exponents drift with machine load, so we assert a RELATIVE gap measured under
    # the SAME conditions (load-invariant) rather than absolute cutoffs: a genuinely O(n^2) stage
    # must land a clearly higher exponent than a ~linear one.
    rng = np.random.default_rng(0)
    sizes = [1000, 2000, 4000]

    def quadratic_stage(X):
        return float((X[:, None] + X[None, :]).sum())     # O(n^2)

    quad = scaling_report(lambda n: rng.normal(size=n), quadratic_stage, sizes, repeats=3)
    lin = scaling_report(lambda n: rng.normal(size=n), lambda X: float(np.sort(X)[-1]),
                         sizes, repeats=3)
    assert quad["exponent"] > lin["exponent"] + 0.5
