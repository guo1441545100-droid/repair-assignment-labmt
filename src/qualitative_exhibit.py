"""
qualitative_exhibit.py

Step 6: a small qualitative exhibit so the numbers in Comparisons 1–3
do not sit in the README as "pure numbers divorced from meaning."

For each of the four source corpora (Twitter, Google Books, NYT, song
lyrics) I list:
    - the 10 highest-happiness words that are EXCLUSIVE to that corpus
      (n_corpora == 1, appears only in that one source's top-5000)
    - the 10 lowest-happiness words that are exclusive to it
These are the words that a reader would see as "uniquely Twitter" or
"uniquely NYT" in the lexicon, and they are the ones that move a
corpus mean the most when you add or remove the filter.

I also compile a 20-word "anchor exhibit" grouped by four categories
that I use to discuss the Δh=1 filter choice in the README:

    very positive (h ≥ 7.5, low SD)
    very negative (h ≤ 2.5, low SD)
    contested     (std ≥ 2.3, any h)
    near-neutral  (|h − 5| ≤ 0.2)  ← the ones the filter drops

Outputs:
    tables/exclusive_words_per_corpus.csv
    tables/anchor_exhibit.csv
    figures/exclusive_words_grid.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
TAB = ROOT / "tables"

IN = PROC / "labmt_clean.csv"
CORPORA = ["twitter", "google", "nyt", "lyrics"]
TOP_K = 10


def main() -> None:
    df = pd.read_csv(IN)

    # ---------------- exclusive words per corpus ----------------
    rows = []
    exclusive_by_corpus: dict[str, pd.DataFrame] = {}
    for c in CORPORA:
        mask = df[f"in_{c}"] & (df["n_corpora"] == 1)
        sub = df[mask].copy()
        sub_sorted = sub.sort_values("happiness_average", ascending=False)
        top_pos = sub_sorted.head(TOP_K)
        top_neg = sub_sorted.tail(TOP_K).iloc[::-1]
        exclusive_by_corpus[c] = pd.concat([top_pos, top_neg])

        for _, r in top_pos.iterrows():
            rows.append({
                "corpus": c, "side": "top_positive",
                "word": r["word"], "happiness": r["happiness_average"],
                "std": r["happiness_standard_deviation"],
                "rank_in_corpus": int(r[f"{c}_rank"]) if not pd.isna(r[f"{c}_rank"]) else None,
            })
        for _, r in top_neg.iterrows():
            rows.append({
                "corpus": c, "side": "bottom_negative",
                "word": r["word"], "happiness": r["happiness_average"],
                "std": r["happiness_standard_deviation"],
                "rank_in_corpus": int(r[f"{c}_rank"]) if not pd.isna(r[f"{c}_rank"]) else None,
            })

    pd.DataFrame(rows).to_csv(TAB / "exclusive_words_per_corpus.csv", index=False)

    # ---------------- anchor exhibit (20 words) ----------------
    # I want 5 words per category so the README table stays readable.
    anchor_rows = []

    def pick(subset: pd.DataFrame, category: str, n: int = 5) -> None:
        for _, r in subset.head(n).iterrows():
            anchor_rows.append({
                "category": category,
                "word": r["word"],
                "happiness": round(float(r["happiness_average"]), 3),
                "std": round(float(r["happiness_standard_deviation"]), 3),
                "n_corpora": int(r["n_corpora"]),
            })

    very_pos = df[(df["happiness_average"] >= 7.5)
                  & (df["happiness_standard_deviation"] <= 1.3)]\
        .sort_values("happiness_average", ascending=False)
    very_neg = df[(df["happiness_average"] <= 2.5)
                  & (df["happiness_standard_deviation"] <= 1.3)]\
        .sort_values("happiness_average", ascending=True)
    contested = df[df["happiness_standard_deviation"] >= 2.3]\
        .sort_values("happiness_standard_deviation", ascending=False)
    near_neutral = df[(df["happiness_average"] - 5.0).abs() <= 0.2]\
        .sort_values("happiness_standard_deviation", ascending=True)

    pick(very_pos, "very positive (h ≥ 7.5, low SD)")
    pick(very_neg, "very negative (h ≤ 2.5, low SD)")
    pick(contested, "contested (std ≥ 2.3)")
    pick(near_neutral, "near-neutral (|h − 5| ≤ 0.2)")

    anchor = pd.DataFrame(anchor_rows)
    anchor.to_csv(TAB / "anchor_exhibit.csv", index=False)
    print("\n[exhibit] anchor exhibit:")
    print(anchor.to_string(index=False))

    # ---------------- figure: 2x2 grid of horizontal bars ----------------
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, c in zip(axes.flat, CORPORA):
        sub = exclusive_by_corpus[c].copy()
        # Plot highest at top, lowest at bottom.
        sub = sub.sort_values("happiness_average", ascending=True)
        colors = ["tab:green" if h > 5 else "tab:red"
                  for h in sub["happiness_average"]]
        ax.barh(sub["word"], sub["happiness_average"] - 5.0, color=colors)
        ax.axvline(0, color="black", linewidth=0.6)
        ax.set_title(f"{c}  (n exclusive = {int((df[f'in_{c}'] & (df['n_corpora']==1)).sum())})",
                     fontsize=10)
        ax.set_xlabel("happiness − 5 (distance from scale midpoint)")
        ax.tick_params(axis="y", labelsize=8)
    fig.suptitle("Top and bottom corpus-exclusive words\n"
                 "(words appearing only in this corpus's top-5000)")
    plt.tight_layout()
    plt.savefig(FIG / "exclusive_words_grid.png", dpi=200)
    plt.close()

    print(f"[save] {TAB / 'exclusive_words_per_corpus.csv'}")
    print(f"[save] {TAB / 'anchor_exhibit.csv'}")
    print(f"[save] {FIG / 'exclusive_words_grid.png'}")


if __name__ == "__main__":
    main()
