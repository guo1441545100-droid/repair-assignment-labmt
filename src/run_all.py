"""
run_all.py

One-command entry point. Runs the whole pipeline end-to-end:

    fetch_data.py          (checks raw inputs, downloads SOTU if needed)
    load_labmt.py          (load + enrich labMT 1.0 lexicon)
    tokenize_and_score.py  (one row per SOTU with labMT weighted score)
    descriptive.py         (per-era tables + distribution figures)
    bootstrap_inference.py (three document-level bootstrap comparisons)
    robustness.py          (four conditions on the era comparisons)
    qualitative_exhibit.py (labMT anchor + era-distinctive word tables)

The bottleneck is bootstrap_inference.py plus robustness.py (together
roughly 10,000 + 4×5,000 resamples). The whole pipeline runs in under
90 seconds on my laptop. Dependencies stay in pandas + numpy +
matplotlib so the only hard requirement is requirements.txt.

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
    "tokenize_and_score.py",
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
