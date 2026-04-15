"""
bootstrap_inference.py

Step 4: inferential comparisons, all word-level, all bootstrap.

The unit of analysis is a single labMT word. The score attached to that
word is `happiness_average`. The four groups are the four source corpora
(Twitter, Google Books, NYT, song lyrics). A single word can belong to
more than one group — this is intrinsic to labMT 1.0, and the analyses
below account for it differently in each of three comparisons.

Comparison 1: pairwise difference in mean happiness between corpora.
    Six pairs (T-G, T-N, T-L, G-N, G-L, N-L). For each pair I draw
    bootstrap samples independently from the two corpus word sets
    (with replacement) and compute the difference in means. This is
    NOT a paired comparison: words shared between corpora contribute
    to both marginal samples, which means the two samples are
    correlated. I treat this as the price of using the corpus-flag
    column instead of pretending the four sets are disjoint. The
    alternative (restricting to corpus-exclusive words only) is
    reported as Comparison 3 below.

Comparison 2: frequency bucket × corpus.
    Inside each corpus I split the 5,000 ranked words into
    {top-1000, middle 1000–4000, bottom 4000–5000} by rank, and
    compute the bootstrap difference in mean happiness between the
    top bucket and the bottom bucket. This tests whether a more
    frequent word in a given corpus is systematically closer to
    neutrality — the "neutral common word" effect that Dodds
    discusses in the 2015 positivity paper.

Comparison 3: corpus-exclusive vs universal words.
    Group words by n_corpora ∈ {1, 2, 3, 4} and bootstrap the mean
    happiness within each bucket. This is the "shared words behave
    differently from exclusive words" check.

Output:
    tables/comparison_1_pairwise_corpus.csv
    tables/comparison_2_frequency_buckets.csv
    tables/comparison_3_overlap_buckets.csv
    tables/readme_fill_in.md
    figures/bootstrap_comparison_1.png
    figures/bootstrap_comparison_2.png
    figures/bootstrap_comparison_3.png
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

N_BOOT = 10_000
RNG = np.random.default_rng(20260414)  # seed = today's date
CORPORA = ["twitter", "google", "nyt", "lyrics"]

# neutral-word filter for the PRIMARY analysis.
# I apply it at the word level: any word with |h - 5| <= 1 is excluded
# from the mean calculations below. This matches Dodds et al. (2011).
DELTA_H = 1.0


def apply_filter(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["happiness_average"] - 5.0).abs() > DELTA_H].copy()


# -----------------------------------------------------------------------------
# bootstrap primitives
# -----------------------------------------------------------------------------

def boot_diff(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, float, float, float, float]:
    if a.size == 0 or b.size == 0:
        return np.array([]), float("nan"), float("nan"), float("nan"), float("nan")
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        ra = RNG.choice(a, size=a.size, replace=True)
        rb = RNG.choice(b, size=b.size, replace=True)
        boot[i] = ra.mean() - rb.mean()
    observed = float(a.mean() - b.mean())
    lo = float(np.percentile(boot, 2.5))
    hi = float(np.percentile(boot, 97.5))
    prob_pos = float((boot > 0).mean())
    return boot, observed, lo, hi, prob_pos


def boot_mean(x: np.ndarray) -> tuple[float, float, float]:
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        boot[i] = RNG.choice(x, size=x.size, replace=True).mean()
    return float(x.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


# -----------------------------------------------------------------------------
# Comparison 1 — pairwise corpus difference (filtered happiness)
# -----------------------------------------------------------------------------

def comparison_1(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    print("\n== Comparison 1: pairwise corpus differences ==")
    dff = apply_filter(df)
    rows = []
    boot_store: dict[str, tuple[np.ndarray, float, float, float]] = {}
    for a, b in combinations(CORPORA, 2):
        xa = dff.loc[dff[f"in_{a}"], "happiness_average"].to_numpy()
        xb = dff.loc[dff[f"in_{b}"], "happiness_average"].to_numpy()
        boot, obs, lo, hi, pp = boot_diff(xa, xb)
        label = f"{a} − {b}"
        rows.append({
            "comparison": label,
            "n_a": int(xa.size),
            "n_b": int(xb.size),
            "mean_a": float(xa.mean()),
            "mean_b": float(xb.mean()),
            "observed_diff": obs,
            "ci_lower": lo,
            "ci_upper": hi,
            "prob_diff_positive": pp,
        })
        boot_store[label] = (boot, obs, lo, hi)
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "comparison_1_pairwise_corpus.csv", index=False)
    print(out.to_string(index=False))

    # Forest plot: observed diff ± CI for each pair
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ypos = np.arange(len(rows))[::-1]
    for y, r in zip(ypos, rows):
        xerr = [[r["observed_diff"] - r["ci_lower"]],
                [r["ci_upper"] - r["observed_diff"]]]
        ax.errorbar(r["observed_diff"], y, xerr=xerr, fmt="o",
                    capsize=4, color="black")
    ax.axvline(0, color="red", linestyle="--", linewidth=1)
    ax.set_yticks(ypos, [r["comparison"] for r in rows])
    ax.set_xlabel("Difference in mean happiness (A − B), filtered (Δh=1)")
    ax.set_title("Comparison 1 — pairwise corpus differences")
    plt.tight_layout()
    plt.savefig(FIG / "bootstrap_comparison_1.png", dpi=200)
    plt.close()
    return out, boot_store


# -----------------------------------------------------------------------------
# Comparison 2 — frequency bucket within each corpus
# -----------------------------------------------------------------------------

def comparison_2(df: pd.DataFrame) -> pd.DataFrame:
    print("\n== Comparison 2: frequency-bucket difference within each corpus ==")
    dff = apply_filter(df)
    rows = []
    for c in CORPORA:
        rank_col = f"{c}_rank"
        sub = dff[dff[f"in_{c}"]].copy()
        # buckets by rank (rank 1 is most frequent)
        top = sub[sub[rank_col] <= 1000]["happiness_average"].to_numpy()
        bot = sub[sub[rank_col] > 4000]["happiness_average"].to_numpy()
        boot, obs, lo, hi, pp = boot_diff(top, bot)
        rows.append({
            "corpus": c,
            "n_top1000": int(top.size),
            "n_bottom1000": int(bot.size),
            "mean_top1000": float(top.mean()) if top.size else float("nan"),
            "mean_bottom1000": float(bot.mean()) if bot.size else float("nan"),
            "observed_diff": obs,
            "ci_lower": lo,
            "ci_upper": hi,
            "prob_diff_positive": pp,
        })
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "comparison_2_frequency_buckets.csv", index=False)
    print(out.to_string(index=False))

    # Bar plot: observed top-minus-bottom difference per corpus with CI
    fig, ax = plt.subplots(figsize=(7, 4))
    xpos = np.arange(len(rows))
    diffs = [r["observed_diff"] for r in rows]
    lows = [r["observed_diff"] - r["ci_lower"] for r in rows]
    highs = [r["ci_upper"] - r["observed_diff"] for r in rows]
    ax.bar(xpos, diffs, yerr=[lows, highs], capsize=5,
           color=["tab:blue", "tab:orange", "tab:green", "tab:red"])
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(xpos, [r["corpus"] for r in rows])
    ax.set_ylabel("mean(top-1000) − mean(bottom-1000)\n"
                  "(happiness, filtered Δh=1)")
    ax.set_title("Comparison 2 — top- vs bottom-ranked words per corpus")
    plt.tight_layout()
    plt.savefig(FIG / "bootstrap_comparison_2.png", dpi=200)
    plt.close()
    return out


# -----------------------------------------------------------------------------
# Comparison 3 — overlap-bucket means
# -----------------------------------------------------------------------------

def comparison_3(df: pd.DataFrame) -> pd.DataFrame:
    print("\n== Comparison 3: mean happiness by n_corpora (exclusive vs shared) ==")
    dff = apply_filter(df)
    rows = []
    # labMT 1.0 contains a handful of words (e.g. "b-day", "cupcake",
    # "x-mas") that are in the scoring table but not in any of the four
    # rank lists, so n_corpora == 0 for them. I exclude that bucket from
    # Comparison 3 because it is orthogonal to the corpus comparison.
    for n in sorted(dff.loc[dff["n_corpora"] >= 1, "n_corpora"].unique()):
        x = dff.loc[dff["n_corpora"] == n, "happiness_average"].to_numpy()
        m, lo, hi = boot_mean(x)
        rows.append({
            "n_corpora": int(n),
            "n_words": int(x.size),
            "mean_happiness": m,
            "ci_lower": lo,
            "ci_upper": hi,
        })
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "comparison_3_overlap_buckets.csv", index=False)
    print(out.to_string(index=False))

    # Error-bar plot: mean ± CI per overlap bucket
    fig, ax = plt.subplots(figsize=(6.5, 4))
    xpos = np.arange(len(rows))
    means = [r["mean_happiness"] for r in rows]
    yerr_lo = [r["mean_happiness"] - r["ci_lower"] for r in rows]
    yerr_hi = [r["ci_upper"] - r["mean_happiness"] for r in rows]
    ax.errorbar(xpos, means, yerr=[yerr_lo, yerr_hi], fmt="o-",
                capsize=5, color="tab:purple")
    ax.axhline(5.0, color="red", linestyle=":", linewidth=0.8,
               label="scale midpoint (5)")
    ax.set_xticks(xpos, [str(r["n_corpora"]) for r in rows])
    ax.set_xlabel("n_corpora (1 = exclusive to one corpus, 4 = universal)")
    ax.set_ylabel("mean happiness (filtered Δh=1)")
    ax.set_title("Comparison 3 — exclusive vs shared words")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIG / "bootstrap_comparison_3.png", dpi=200)
    plt.close()
    return out


# -----------------------------------------------------------------------------
# README fill-in
# -----------------------------------------------------------------------------

def dump_fill_in(c1: pd.DataFrame, c2: pd.DataFrame, c3: pd.DataFrame) -> None:
    lines = ["# README fill-in values",
             "",
             "Values produced by bootstrap_inference.py. Copy these into",
             "the [[...]] placeholders in README.md §6.",
             ""]
    lines.append("## Comparison 1 — pairwise corpus differences (filtered)")
    for _, r in c1.iterrows():
        lines.append(
            f"- {r['comparison']}: diff = {r['observed_diff']:+.4f}, "
            f"CI = [{r['ci_lower']:+.4f}, {r['ci_upper']:+.4f}], "
            f"mean_a = {r['mean_a']:.4f}, mean_b = {r['mean_b']:.4f}, "
            f"prob>0 = {r['prob_diff_positive']:.3f}"
        )
    lines.append("")
    lines.append("## Comparison 2 — top-1000 minus bottom-1000 per corpus (filtered)")
    for _, r in c2.iterrows():
        lines.append(
            f"- {r['corpus']}: diff = {r['observed_diff']:+.4f}, "
            f"CI = [{r['ci_lower']:+.4f}, {r['ci_upper']:+.4f}], "
            f"n_top = {int(r['n_top1000'])}, n_bot = {int(r['n_bottom1000'])}"
        )
    lines.append("")
    lines.append("## Comparison 3 — mean happiness by n_corpora (filtered)")
    for _, r in c3.iterrows():
        lines.append(
            f"- n_corpora = {int(r['n_corpora'])}: "
            f"mean = {r['mean_happiness']:.4f}, "
            f"CI = [{r['ci_lower']:.4f}, {r['ci_upper']:.4f}], "
            f"n_words = {int(r['n_words'])}"
        )
    lines.append("")
    (TAB / "readme_fill_in.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[save] {TAB / 'readme_fill_in.md'}")


def main() -> None:
    df = pd.read_csv(IN)
    c1, _ = comparison_1(df)
    c2 = comparison_2(df)
    c3 = comparison_3(df)
    dump_fill_in(c1, c2, c3)


if __name__ == "__main__":
    main()
