"""Harness B — scaling/performance measurement (review, compute aspect).

The full-universe run happens on ONE box (Threadripper 5975WX, 32c/64t, 256 GB, 4 TB NVMe),
not a cluster. A stage that is O(n^2) or single-threaded will die hours into a full run. This
harness measures each heavy stage at increasing sizes and estimates its empirical scaling
exponent (log-log slope of time vs n), so a superlinear step is caught on a laptop-sized panel
before it is hit at 50M ticker-days. It is hardware-independent by design: the ACCEPTANCE
CRITERION is the exponent (linear ~1.0, quadratic ~2.0), not seconds on any particular machine.

    from gws.validation.perf_harness import scaling_report
    rep = scaling_report(make_input=lambda n: rng.normal(size=(n, 20)),
                         stage=lambda X: some_stage(X), sizes=[10_000, 20_000, 40_000])
    assert rep["exponent"] < 1.3     # must scale ~linearly
"""
from __future__ import annotations

import time
import tracemalloc

import numpy as np


def time_stage(stage, *args, measure_mem: bool = True):
    """Run `stage(*args)`; return (result, seconds, peak_python_mb). Peak MB is tracemalloc's
    Python-allocation peak — it undercounts raw numpy buffers, so treat it as a lower bound and
    trust the exponent for the real signal."""
    if measure_mem:
        tracemalloc.start()
    t0 = time.perf_counter()
    result = stage(*args)
    seconds = time.perf_counter() - t0
    peak_mb = float("nan")
    if measure_mem:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / 1e6
    return result, seconds, peak_mb


def estimate_scaling_exponent(sizes, times) -> float:
    """Least-squares slope of log(time) vs log(size) — the empirical big-O exponent."""
    s = np.log(np.asarray(sizes, float))
    t = np.log(np.asarray(times, float))
    return float(np.polyfit(s, t, 1)[0])


def scaling_report(make_input, stage, sizes, *, repeats: int = 1) -> dict:
    """Time `stage(make_input(n))` at each n in `sizes` (min over `repeats`), and estimate the
    scaling exponent. Returns per-size timings, peak MB, and the fitted exponent."""
    times, peaks = [], []
    for n in sizes:
        best = float("inf"); peak_mb = float("nan")
        for _ in range(repeats):
            inp = make_input(n)
            _, sec, mb = time_stage(stage, inp)
            if sec < best:
                best, peak_mb = sec, mb
        times.append(best); peaks.append(peak_mb)
    return {"sizes": list(sizes), "seconds": times, "peak_mb": peaks,
            "exponent": estimate_scaling_exponent(sizes, times)}
