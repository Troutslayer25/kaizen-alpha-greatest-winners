"""CI gate — run the full test suite from a clean checkout and fail on any red.

The suite is the study's correctness gate: it includes the standing guards (PIT future-invariance,
null-calibration of the discovery funnel, outcome quarantine, survivorship, sub-quadratic compute).
Wire this into a pre-push hook or CI runner. Coverage is reported when pytest-cov is installed.

    python scripts/ci.py            # run the gate
    python scripts/ci.py --cov      # also emit a coverage summary if pytest-cov is present
"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    args = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if "--cov" in sys.argv:
        try:
            import pytest_cov  # noqa: F401
            args += ["--cov=gws", "--cov-report=term-missing:skip-covered"]
        except ImportError:
            print("[ci] pytest-cov not installed; running without coverage", file=sys.stderr)
    print("[ci] running:", " ".join(args))
    rc = subprocess.call(args)
    print("[ci] PASS" if rc == 0 else f"[ci] FAIL (pytest exit {rc})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
