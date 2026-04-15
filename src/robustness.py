"""
robustness.py

Step 5: sensitivity checks on Comparison 1 (pairwise corpus differences).

The point is not to produce a new finding, it is to show that the main
claim, that the four labMT source corpora differ in mean word
happiness, does not hinge on a single operational choice. I re-run the
six pairwise bootstrap differences from Comparison 1 under four
conditions and plot them side by side:

    A  baseline: neutral filter ON at Δh = 1.0   (matches the main analysis)
    B  no neutral filter                          (use all words)
    C  broader filter Δh = 0.5                    (keep more near-neutral words)
    D  drop "contested" words with high rater SD  (std > 1.5)

If the six pairwise differences all stay on the same side of zero
across A–D, the main claim is robust to these choices. If any of them
crosses zero, the corresponding pair is reported as fragile in the
README.

Outputs:
    tables/robustness_comparison_1.csv
    figures/robustness_forest.png
"""

from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
TAB = ROOT / "tables"

IN = PROC / "labmt_clean.csv"

N_BOOT = 5_000
RNG = np.random.default_rng(19930101)  # deliberately different seed from main
CORPORA = ["twitter", "google", "nyt", "lyrics"]


def boot_diff(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan"), float("nan")
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        boot[i] = (RNG.choice(a, size=a.size, replace=True).mean()
                   - RNG.choice(b, size=b.size, replace=True).mean())
    return (float(a.mean() - b.mean()),
            float(np.percentile(boot, 2.5)),
            float(np.percentile(boot, 97.5)))


def pairwise_table(df: pd.DataFrame, condition: str) -> list[dict]:
    rows = []
    for a, b in combinations(CORPORA, 2):
        xa = df.loc[df[f"in_{a}"], "happiness_average"].to_numpy()
        xb = df.loc[df[f"in_{b}"], "happiness_average"].to_numpy()
        obs, lo, hi = boot_diff(xa, xb)
        rows.append({
            "condition": condition,
            "pair": f"{a} − {b}",
            "observed_diff": obs,
            "ci_lower": lo,
            "ci_upper": hi,
            "n_a": int(xa.size),
            "n_b": int(xb.size),
        })
    return rows


# ----- four conditions -----

def cond_A_baseline(df: pd.DataFrame) -> list[dict]:
    mask = (df["happiness_average"] - 5.0).abs() > 1.0
    return pairwise_table(df[mask], "A baseline (Δh=1 filter)")


def cond_B_no_filter(df: pd.DataFrame) -> list[dict]:
    return pairwise_table(df, "B no neutral filter")


def cond_C_half_filter(df: pd.DataFrame) -> list[dict]:
    mask = (df["happiness_average"] - 5.0).abs() > 0.5
    return pairwise_table(df[mask], "C broader filter (Δh=0.5)")


def cond_D_drop_high_sd(df: pd.DataFrame) -> list[dict]:
    # "contested" words, where the 50 raters disagreed a lot. I drop
    # them to see whether those words are driving the corpus means.
    mask = (
        ((df["happiness_average"] - 5.0).abs() > 1.0)
        & (df["happiness_standard_deviation"] <= 1.5)
    )
    return pairwise_table(df[mask], "D drop high-SD words (std ≤ 1.5)")


def main() -> None:
    df = pd.read_csv(IN)

    all_rows: list[dict] = []
    for fn in [cond_A_baseline, cond_B_no_filter, cond_C_half_filter, cond_D_drop_high_sd]:
        rows = fn(df)
        for r in rows:
            print(f"{r['condition']:32s}  {r['pair']:22s}  "
                  f"{r['observed_diff']:+.4f}  "
                  f"CI [{r['ci_lower']:+.4f}, {r['ci_upper']:+.4f}]")
        all_rows.extend(rows)

    out = pd.DataFrame(all_rows)
    out.to_csv(TAB / "robustness_comparison_1.csv", index=False)

    # forest plot: one row per (pair, condition). Group by pair, offset by condition.
    pairs = [f"{a} − {b}" for a, b in combinations(CORPORA, 2)]
    conditions = [
        "A baseline (Δh=1 filter)",
        "B no neutral filter",
        "C broader filter (Δh=0.5)",
        "D drop high-SD words (std ≤ 1.5)",
    ]
    colors = ["black", "tab:blue", "tab:orange", "tab:green"]
    offsets = [-0.27, -0.09, 0.09, 0.27]

    fig, ax = plt.subplots(figsize=(8, 6))
    ypos_base = np.arange(len(pairs))[::-1]
    for cond, color, off in zip(conditions, colors, offsets):
        sub = out[out["condition"] == cond]
        for y, pair in zip(ypos_base, pairs):
            row = sub[sub["pair"] == pair].iloc[0]
            ax.errorbar(
                row["observed_diff"], y + off,
                xerr=[[row["observed_diff"] - row["ci_lower"]],
                      [row["ci_upper"] - row["observed_diff"]]],
                fmt="o", capsize=3, color=color,
                label=cond if pair == pairs[0] else None,
            )
    ax.axvline(0, color="red", linestyle="--", linewidth=1)
    ax.set_yticks(ypos_base, pairs)
    ax.set_xlabel("Difference in mean happiness (A − B) with 95% bootstrap CI")
    ax.set_title("Robustness of Comparison 1 under four operational choices")
    ax.legend(fontsize=8, loc="best")
    plt.tight_layout()
    plt.savefig(FIG / "robustness_forest.png", dpi=200)
    plt.close()

    print(f"[save] {TAB / 'robustness_comparison_1.csv'}")
    print(f"[save] {FIG / 'robustness_forest.png'}")


if __name__ == "__main__":
    main()
