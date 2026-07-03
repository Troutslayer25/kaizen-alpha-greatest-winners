"""Exhibit: the end-to-end synthetic integration dress rehearsal.

Runs the full spine (generate -> detect -> label -> feature store -> clustered screen -> shuffled
control) and reports whether the pipeline recovers the planted signal and stays null-safe. Run this
before the Gate 0.5 pilot as the integration smoke test.

    python scripts/run_e2e_synthetic.py
    python scripts/run_e2e_synthetic.py --seeds 5
"""
from __future__ import annotations

import argparse

from gws.validation.e2e_integration import run_e2e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    print(f"{'seed':>4} {'recall':>7} {'pos/pts':>10} {'planted':>8} {'null':>6} {'shuffle':>8}")
    print("-" * 50)
    ok = True
    for s in range(args.seeds):
        r = run_e2e(seed=s)
        row_ok = (r["detection_recall"] >= 0.8 and r["planted_significant"]
                  and not r["null_significant"] and not r["planted_significant_under_shuffle"])
        ok = ok and row_ok
        print(f"{s:>4} {r['detection_recall']:>7.2f} {r['n_positive']:>4}/{r['n_points']:<5} "
              f"{str(r['planted_significant']):>8} {str(r['null_significant']):>6} "
              f"{str(r['planted_significant_under_shuffle']):>8}")
    print("\nPASS — spine wired, planted signal recovered, null-safe." if ok
          else "\nFAIL — integration issue; inspect the failing seed.")


if __name__ == "__main__":
    main()
