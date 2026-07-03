"""Exhibit: realized false-positive rate of the discovery funnel under the global null.

Runs the univariate screen over many pure-null panels and reports the family-wise rejection
rate. The naive (i.i.d.) screen on ticker-clustered panels is the C-1 miscalibration exhibit;
once ticker-clustered inference is wired in (task C-1), re-run with the clustered screen and
the rate should fall back toward alpha.

    python scripts/run_null_calibration.py
    python scripts/run_null_calibration.py --trials 500
"""
from __future__ import annotations

import argparse

from gws.phase_a3.univariate import univariate_screen
from gws.validation.null_calibration import make_iid_panel, make_null_panel, run_calibration


def _naive(fm, labels, tickers):
    return univariate_screen(fm, labels)


def _clustered(fm, labels, tickers):
    return univariate_screen(fm, labels, cluster_ids=tickers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args()

    print(f"Null-calibration exhibit ({args.trials} trials, alpha={args.alpha})\n")
    print(f"{'panel':28} {'screen':10} {'familywise':>11} {'fp_rate':>9} {'mean_rej':>9}")
    print("-" * 70)

    cases = [
        ("iid (independent rows)", make_iid_panel, {}, _naive, "naive"),
        ("ticker-clustered (null)", make_null_panel, {}, _naive, "naive"),
        ("ticker-clustered (null)", make_null_panel, {}, _clustered, "clustered"),
    ]
    for name, panel_fn, kw, fn, label in cases:
        r = run_calibration(fn, n_trials=args.trials, alpha=args.alpha,
                            panel_fn=panel_fn, **kw)
        print(f"{name:28} {label:10} {r['familywise_rate']:>11.3f} "
              f"{r['fp_rate']:>9.4f} {r['mean_rejections']:>9.2f}")

    print("\nInterpretation: familywise ~ alpha on iid = the screen is calibrated when rows are\n"
          "independent. familywise >> alpha on ticker-clustered = i.i.d. p-values are\n"
          "anti-conservative under within-ticker dependence (C-1). Target after the clustered-\n"
          "inference fix: ticker-clustered familywise back down toward alpha.")


if __name__ == "__main__":
    main()
