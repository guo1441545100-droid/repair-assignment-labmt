"""
run_all.py

One-command entry point. Runs the whole pipeline end-to-end:

    fetch_data.py          (just checks the raw inputs exist)
    load_labmt.py          (load + enrich labMT 1.0)
    descriptive.py         (tables + distribution figures)
    bootstrap_inference.py (three word-level comparisons)
    robustness.py          (four filter conditions on Comparison 1)
    qualitative_exhibit.py (distinctive / anchor word tables)

The bottleneck is bootstrap_inference.py (N_BOOT=10,000 resamples per
cell × three comparisons). The whole pipeline runs in well under a
minute on my laptop because labMT is only ~10k rows. I have kept
everything in pandas + numpy + matplotlib so the only hard dependency
is requirements.txt.

Run from the repo root:
    python src/run_all.py
"""

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent

STEPS = [
    "fetch_data.py",
    "load_labmt.py",
    "descriptive.py",
    "bootstrap_inference.py",
    "robustness.py",
    "qualitative_exhibit.py",
]


def main() -> int:
    for step in STEPS:
        print("\n" + "=" * 72)
        print(f"Running {step}")
        print("=" * 72)
        rc = subprocess.call([sys.executable, str(SRC / step)])
        if rc != 0:
            print(f"\n{step} exited with code {rc}. Stopping.")
            return rc
    print("\nAll steps finished. Check figures/ and tables/.")
    print("Remember to copy the numbers from tables/readme_fill_in.md "
          "into the [[placeholder]] slots in README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
