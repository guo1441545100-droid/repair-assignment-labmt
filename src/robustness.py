"""
robustness.py

Step 6: sensitivity checks on Comparison 1 (era pairwise differences).

The point is not to find a new result, it is to show that the main
claim (the Broadcast era SOTUs score higher than the earlier two eras)
does not hinge on a single measurement choice. I re-run the three
pairwise bootstrap differences under four conditions:

    A  baseline                 Δh = 1 filter, weighted score
                                (matches bootstrap_inference.py)
    B  no neutral filter        score every labMT-matched token
    C  broader filter Δh = 0.5  keep more near-neutral words
    D  drop low-coverage docs   require per-doc coverage >= 18%

Condition D is the one I added specifically for this corpus. Coverage
varies from ~18% in the Founding era to ~29% in the Broadcast era,
and a reviewer could reasonably worry that the era effect is an
artefact of labMT seeing more of the newer speeches than the older
ones. Condition D re-runs the comparison on the subset where every
document has at least 18% of its tokens matched, which halves the
Founding-era n but keeps the coverage roughly comparable across
eras.

If any of the three pairwise differences flips sign or crosses zero
under A–D, I say so in README §6.

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

LABMT_CSV = PROC / "labmt_clean.csv"
SOTU_CSV = PROC / "sotu_scored.csv"
SOTU_DIR = ROOT / "data" / "raw" / "sotu"

N_BOOT = 5_000
RNG = np.random.default_rng(19930101)
ERA_ORDER = ["Founding", "Industrial", "Broadcast"]

# Import the scoring primitives from the step-3 script, so the
# conditions that need to rescore documents use the same tokeniser.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tokenize_and_score import (  # noqa: E402
    parse_filename, strip_preamble, tokenize, score_document,
    era_of,
)


def boot_diff(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float, float]:
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        boot[i] = (RNG.choice(a, size=a.size, replace=True).mean()
                   - RNG.choice(b, size=b.size, replace=True).mean())
    obs = float(a.mean() - b.mean())
    return (obs,
            float(np.percentile(boot, 2.5)),
            float(np.percentile(boot, 97.5)),
            float((boot > 0).mean()))


def pairwise_table(df: pd.DataFrame, condition: str, score_col: str) -> list[dict]:
    rows = []
    for a, b in combinations(ERA_ORDER, 2):
        xa = df.loc[df["era"] == a, score_col].dropna().to_numpy()
        xb = df.loc[df["era"] == b, score_col].dropna().to_numpy()
        obs, lo, hi, pp = boot_diff(xa, xb)
        rows.append({
            "condition": condition,
            "pair": f"{a} − {b}",
            "observed_diff": obs,
            "ci_lower": lo,
            "ci_upper": hi,
            "prob_diff_positive": pp,
            "n_a": int(xa.size),
            "n_b": int(xb.size),
        })
    return rows


def rescore_with_filter(delta: float) -> pd.DataFrame:
    """Rescore every SOTU document with a different neutral filter."""
    labmt = pd.read_csv(LABMT_CSV)
    if delta is None:
        mask = pd.Series(True, index=labmt.index)
    else:
        mask = (labmt["happiness_average"] - 5.0).abs() > delta
    filt = dict(zip(labmt.loc[mask, "word"].astype(str),
                    labmt.loc[mask, "happiness_average"].astype(float)))
    rows = []
    for p in sorted(SOTU_DIR.glob("*.txt")):
        meta = parse_filename(p.name)
        if meta is None:
            continue
        _, year = meta
        body = strip_preamble(p.read_text(encoding="utf-8", errors="replace"))
        tokens = tokenize(body)
        s = score_document(tokens, filt)
        rows.append({
            "year": year,
            "era": era_of(year),
            "happiness_weighted": s["happiness_weighted"],
            "coverage": s["coverage"],
        })
    return pd.DataFrame(rows)


def main() -> None:
    baseline = pd.read_csv(SOTU_CSV)

    all_rows: list[dict] = []

    # A baseline
    all_rows.extend(pairwise_table(baseline,
                                   "A baseline (Δh=1, full corpus)",
                                   "happiness_weighted"))

    # B no filter
    df_b = rescore_with_filter(None)
    all_rows.extend(pairwise_table(df_b,
                                   "B no neutral filter",
                                   "happiness_weighted"))

    # C Δh=0.5
    df_c = rescore_with_filter(0.5)
    all_rows.extend(pairwise_table(df_c,
                                   "C broader filter (Δh=0.5)",
                                   "happiness_weighted"))

    # D drop low-coverage docs
    df_d = baseline[baseline["coverage"] >= 0.18].copy()
    all_rows.extend(pairwise_table(df_d,
                                   "D drop coverage < 0.18",
                                   "happiness_weighted"))

    for r in all_rows:
        print(f"{r['condition']:32s}  {r['pair']:24s}  "
              f"{r['observed_diff']:+.4f}  "
              f"CI [{r['ci_lower']:+.4f}, {r['ci_upper']:+.4f}]  "
              f"p>0={r['prob_diff_positive']:.3f}  "
              f"n={r['n_a']}/{r['n_b']}")

    out = pd.DataFrame(all_rows)
    out.to_csv(TAB / "robustness_comparison_1.csv", index=False)

    # forest plot
    pairs = [f"{a} − {b}" for a, b in combinations(ERA_ORDER, 2)]
    conditions = [
        "A baseline (Δh=1, full corpus)",
        "B no neutral filter",
        "C broader filter (Δh=0.5)",
        "D drop coverage < 0.18",
    ]
    colors = ["black", "tab:blue", "tab:orange", "tab:green"]
    offsets = [-0.27, -0.09, 0.09, 0.27]

    fig, ax = plt.subplots(figsize=(8, 4.5))
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
    ax.set_xlabel("Difference in mean happiness_weighted (A − B) with 95% CI")
    ax.set_title("Robustness of era pairwise comparisons (four conditions)")
    ax.legend(fontsize=8, loc="lower right")
    plt.tight_layout()
    plt.savefig(FIG / "robustness_forest.png", dpi=200)
    plt.close()

    print(f"[save] {TAB / 'robustness_comparison_1.csv'}")
    print(f"[save] {FIG / 'robustness_forest.png'}")


if __name__ == "__main__":
    main()
