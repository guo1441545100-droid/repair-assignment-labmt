"""
qualitative_exhibit.py

Step 7: a qualitative exhibit so the numbers in Comparisons 1–3 do not
sit in the README as pure numbers divorced from meaning.

Two panels:

 Panel A: the labMT instrument itself.
     I show a 20-word "anchor exhibit" grouped by four categories that
     come up repeatedly in the README:
         very positive (h >= 7.5, low SD)
         very negative (h <= 2.5, low SD)
         contested     (std >= 2.3, any h)
         near-neutral  (|h - 5| <= 0.2)   (these are the ones the
                                           filter drops)
     This is the panel that lets a reader judge the instrument without
     taking my word for it.

 Panel B: the corpus side, era-distinctive words.
     For each of the three eras (Founding, Industrial, Broadcast) I
     compute the empirical token frequency per word across all SOTU
     documents in that era, then for each word compute a distinctive
     score:
         distinct(w, era) = freq(w | era) − max(freq(w | other eras))
     I intersect this with the labMT filtered vocabulary and report
     the 10 most "happy era-distinctive" words and the 10 most "sad
     era-distinctive" words per era. These are the words that move the
     era mean up or down the most.

Outputs:
    tables/anchor_exhibit.csv
    tables/era_distinctive_words.csv
    figures/anchor_exhibit.png
    figures/era_distinctive_grid.png
"""

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
TAB = ROOT / "tables"
SOTU_DIR = ROOT / "data" / "raw" / "sotu"

LABMT_CSV = PROC / "labmt_clean.csv"
SOTU_CSV = PROC / "sotu_scored.csv"

ERA_ORDER = ["Founding", "Industrial", "Broadcast"]
TOP_K = 10

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tokenize_and_score import (  # noqa: E402
    parse_filename, strip_preamble, tokenize,
)


# ------------------------------------------------------------------
# Panel A, labMT anchor exhibit
# ------------------------------------------------------------------

def anchor_exhibit(labmt: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def pick(subset: pd.DataFrame, category: str, n: int = 5) -> None:
        for _, r in subset.head(n).iterrows():
            rows.append({
                "category": category,
                "word": r["word"],
                "happiness": round(float(r["happiness_average"]), 3),
                "std": round(float(r["happiness_standard_deviation"]), 3),
            })

    very_pos = labmt[(labmt["happiness_average"] >= 7.5)
                     & (labmt["happiness_standard_deviation"] <= 1.3)]\
        .sort_values("happiness_average", ascending=False)
    very_neg = labmt[(labmt["happiness_average"] <= 2.5)
                     & (labmt["happiness_standard_deviation"] <= 1.3)]\
        .sort_values("happiness_average", ascending=True)
    contested = labmt[labmt["happiness_standard_deviation"] >= 2.3]\
        .sort_values("happiness_standard_deviation", ascending=False)
    near_neutral = labmt[(labmt["happiness_average"] - 5.0).abs() <= 0.2]\
        .sort_values("happiness_standard_deviation", ascending=True)

    pick(very_pos, "very positive (h >= 7.5, low SD)")
    pick(very_neg, "very negative (h <= 2.5, low SD)")
    pick(contested, "contested (std >= 2.3)")
    pick(near_neutral, "near-neutral (|h-5| <= 0.2)")

    out = pd.DataFrame(rows)
    out.to_csv(TAB / "anchor_exhibit.csv", index=False)
    return out


def plot_anchor(anchor: pd.DataFrame) -> None:
    cats = anchor["category"].unique().tolist()
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5))
    for ax, cat in zip(axes.flat, cats):
        sub = anchor[anchor["category"] == cat].sort_values(
            "happiness", ascending=True)
        colors = ["#55A868" if h > 5 else "#C44E52" for h in sub["happiness"]]
        ax.barh(sub["word"], sub["happiness"] - 5.0, color=colors)
        ax.axvline(0, color="black", linewidth=0.6)
        ax.set_xlim(-4.0, 4.0)
        ax.set_title(cat, fontsize=10)
        ax.set_xlabel("happiness − 5")
        ax.tick_params(axis="y", labelsize=9)
    fig.suptitle("labMT 1.0 anchor exhibit, five words per category")
    plt.tight_layout()
    plt.savefig(FIG / "anchor_exhibit.png", dpi=200)
    plt.close()


# ------------------------------------------------------------------
# Panel B, era-distinctive words
# ------------------------------------------------------------------

def era_token_freqs(sotu_meta: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Return {era: {word: normalised freq per 1000 tokens}}."""
    freqs: dict[str, Counter] = {e: Counter() for e in ERA_ORDER}
    totals: dict[str, int] = {e: 0 for e in ERA_ORDER}
    for _, row in sotu_meta.iterrows():
        era = row["era"]
        if era not in freqs:
            continue
        p = SOTU_DIR / row["filename"]
        if not p.exists():
            continue
        body = strip_preamble(p.read_text(encoding="utf-8", errors="replace"))
        tokens = tokenize(body)
        totals[era] += len(tokens)
        freqs[era].update(tokens)
    # normalise to per-1000 tokens
    out = {}
    for e in ERA_ORDER:
        tot = totals[e] or 1
        out[e] = {w: 1000.0 * c / tot for w, c in freqs[e].items()}
    return out


def era_distinctive(sotu_meta: pd.DataFrame, labmt: pd.DataFrame) -> pd.DataFrame:
    freqs = era_token_freqs(sotu_meta)
    mask = (labmt["happiness_average"] - 5.0).abs() > 1.0
    filt = labmt.loc[mask, ["word", "happiness_average"]].copy()
    filt_set = set(filt["word"].astype(str))
    h_map = dict(zip(filt["word"].astype(str),
                     filt["happiness_average"].astype(float)))

    # build wide table of freqs, restricted to labMT-filtered words
    words = sorted(filt_set)
    data = {
        "word": words,
        "happiness": [h_map[w] for w in words],
    }
    for e in ERA_ORDER:
        data[f"freq_{e}"] = [freqs[e].get(w, 0.0) for w in words]
    wide = pd.DataFrame(data)

    for e in ERA_ORDER:
        others = [f"freq_{o}" for o in ERA_ORDER if o != e]
        wide[f"distinct_{e}"] = wide[f"freq_{e}"] - wide[others].max(axis=1)

    rows = []
    for e in ERA_ORDER:
        col = f"distinct_{e}"
        # only words that actually appear at least once per 10k tokens
        active = wide[wide[f"freq_{e}"] >= 0.1]
        happy = active[active["happiness"] > 5].sort_values(
            col, ascending=False).head(TOP_K)
        sad = active[active["happiness"] < 5].sort_values(
            col, ascending=False).head(TOP_K)
        for _, r in happy.iterrows():
            rows.append({
                "era": e, "side": "happy_distinctive",
                "word": r["word"],
                "happiness": round(float(r["happiness"]), 3),
                "freq_per_1000": round(float(r[f"freq_{e}"]), 3),
                "distinct_score": round(float(r[col]), 3),
            })
        for _, r in sad.iterrows():
            rows.append({
                "era": e, "side": "sad_distinctive",
                "word": r["word"],
                "happiness": round(float(r["happiness"]), 3),
                "freq_per_1000": round(float(r[f"freq_{e}"]), 3),
                "distinct_score": round(float(r[col]), 3),
            })
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "era_distinctive_words.csv", index=False)
    return out


def plot_era_distinctive(dist: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), sharex=False)
    sides = [("happy_distinctive", "#55A868"), ("sad_distinctive", "#C44E52")]
    for col, era in enumerate(ERA_ORDER):
        for row_i, (side, color) in enumerate(sides):
            ax = axes[row_i, col]
            sub = dist[(dist["era"] == era) & (dist["side"] == side)]
            sub = sub.sort_values("distinct_score", ascending=True)
            ax.barh(sub["word"], sub["distinct_score"], color=color)
            ax.set_title(f"{era}: {side.replace('_', ' ')}", fontsize=10)
            ax.set_xlabel("distinct score (Δ freq per 1000)")
            ax.tick_params(axis="y", labelsize=8)
    fig.suptitle("Era-distinctive words, filtered by labMT (Δh=1)")
    plt.tight_layout()
    plt.savefig(FIG / "era_distinctive_grid.png", dpi=200)
    plt.close()


def main() -> None:
    labmt = pd.read_csv(LABMT_CSV)
    sotu = pd.read_csv(SOTU_CSV)

    anchor = anchor_exhibit(labmt)
    print("\n[exhibit] anchor exhibit:")
    print(anchor.to_string(index=False))
    plot_anchor(anchor)

    dist = era_distinctive(sotu, labmt)
    print("\n[exhibit] era-distinctive words (top rows):")
    print(dist.head(20).to_string(index=False))
    plot_era_distinctive(dist)

    print(f"\n[save] {TAB / 'anchor_exhibit.csv'}")
    print(f"[save] {TAB / 'era_distinctive_words.csv'}")
    print(f"[save] {FIG / 'anchor_exhibit.png'}")
    print(f"[save] {FIG / 'era_distinctive_grid.png'}")


if __name__ == "__main__":
    main()
