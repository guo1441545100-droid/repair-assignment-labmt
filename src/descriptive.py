"""
descriptive.py

Step 3: descriptive statistics and distribution plots.

Outputs:
    tables/descriptive_overall.csv
    tables/descriptive_by_corpus.csv
    tables/corpus_overlap_counts.csv
    tables/pairwise_overlap.csv
    tables/descriptive_by_n_corpora.csv

    figures/hist_happiness_overall.png
    figures/hist_happiness_by_corpus.png
    figures/scatter_happiness_vs_std.png
    figures/corpus_overlap_bar.png
    figures/happiness_vs_rank_per_corpus.png

The four labMT source corpora each contain at most 5,000 words by
design (this is how Dodds et al. 2011 built the union lexicon), so
"coverage" in the group-project sense is uninteresting here — every
corpus always has 5,000 entries. What IS interesting descriptively is:

    - the overall shape of happiness_average;
    - how each corpus's word set compares in mean / median / spread;
    - the pattern of overlap between corpora (how many words are
      shared, which pairs overlap most);
    - the scatter of rank against happiness inside each corpus — does
      a more frequent word tend to be more or less neutral?
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
FIG.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)

IN = PROC / "labmt_clean.csv"
CORPORA = ["twitter", "google", "nyt", "lyrics"]


def summary(series: pd.Series) -> pd.Series:
    s = series.dropna()
    return pd.Series({
        "n": int(s.shape[0]),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=1)),
        "median": float(s.median()),
        "q25": float(s.quantile(0.25)),
        "q75": float(s.quantile(0.75)),
        "min": float(s.min()),
        "max": float(s.max()),
    })


def main() -> None:
    df = pd.read_csv(IN)

    # ---- tables ----
    overall = summary(df["happiness_average"]).to_frame("value").reset_index()
    overall.columns = ["metric", "value"]
    overall.to_csv(TAB / "descriptive_overall.csv", index=False)

    by_corpus_rows = []
    for c in CORPORA:
        s = df.loc[df[f"in_{c}"], "happiness_average"]
        row = summary(s)
        row["corpus"] = c
        by_corpus_rows.append(row)
    by_corpus = pd.DataFrame(by_corpus_rows)[
        ["corpus", "n", "mean", "std", "median", "q25", "q75", "min", "max"]
    ]
    by_corpus.to_csv(TAB / "descriptive_by_corpus.csv", index=False)

    # words-in-N-corpora table
    by_n_rows = []
    for n in sorted(df["n_corpora"].unique()):
        s = df.loc[df["n_corpora"] == n, "happiness_average"]
        row = summary(s)
        row["n_corpora"] = int(n)
        by_n_rows.append(row)
    by_n = pd.DataFrame(by_n_rows)[
        ["n_corpora", "n", "mean", "std", "median", "q25", "q75", "min", "max"]
    ]
    by_n.to_csv(TAB / "descriptive_by_n_corpora.csv", index=False)

    # overlap counts
    overlap = df["n_corpora"].value_counts().sort_index().reset_index()
    overlap.columns = ["n_corpora", "n_words"]
    overlap.to_csv(TAB / "corpus_overlap_counts.csv", index=False)

    # pairwise overlaps
    pairs = []
    for a, b in combinations(CORPORA, 2):
        mask = df[f"in_{a}"] & df[f"in_{b}"]
        pairs.append({
            "pair": f"{a}+{b}",
            "n_shared": int(mask.sum()),
            "mean_happiness_shared": float(df.loc[mask, "happiness_average"].mean()),
        })
    pd.DataFrame(pairs).to_csv(TAB / "pairwise_overlap.csv", index=False)

    # ---- figures ----
    # 1) overall histogram
    plt.figure(figsize=(7, 4))
    plt.hist(df["happiness_average"], bins=40)
    plt.axvline(df["happiness_average"].mean(), linestyle="--", color="black",
                label=f"mean = {df['happiness_average'].mean():.3f}")
    plt.axvline(5.0, linestyle=":", color="red", label="scale midpoint (5)")
    plt.title("labMT 1.0: distribution of happiness_average\n"
              f"n = {len(df)} words")
    plt.xlabel("happiness_average (1 = least happy, 9 = most happy)")
    plt.ylabel("word count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "hist_happiness_overall.png", dpi=200)
    plt.close()

    # 2) by-corpus overlay (density so the 5000-vs-5000 comparison is fair)
    plt.figure(figsize=(7, 4))
    for c in CORPORA:
        s = df.loc[df[f"in_{c}"], "happiness_average"]
        plt.hist(s, bins=40, alpha=0.4, density=True,
                 label=f"{c} (n={len(s)})")
    plt.title("labMT 1.0 by source corpus: happiness density")
    plt.xlabel("happiness_average")
    plt.ylabel("density")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "hist_happiness_by_corpus.png", dpi=200)
    plt.close()

    # 3) scatter: happiness vs std, coloured by n_corpora
    plt.figure(figsize=(7, 5))
    sc = plt.scatter(
        df["happiness_average"],
        df["happiness_standard_deviation"],
        c=df["n_corpora"],
        cmap="viridis",
        s=10, alpha=0.5,
    )
    plt.colorbar(sc, label="# corpora containing the word")
    plt.title("Rater disagreement vs happiness score\n"
              "(each point = one labMT word)")
    plt.xlabel("happiness_average")
    plt.ylabel("happiness_standard_deviation")
    plt.tight_layout()
    plt.savefig(FIG / "scatter_happiness_vs_std.png", dpi=200)
    plt.close()

    # 4) overlap bar
    plt.figure(figsize=(6, 4))
    oc = df["n_corpora"].value_counts().sort_index()
    plt.bar(oc.index.astype(str), oc.values)
    for x, y in zip(oc.index.astype(str), oc.values):
        plt.text(x, y, f"{y}", ha="center", va="bottom", fontsize=9)
    plt.title("How many labMT words appear in N source corpora?")
    plt.xlabel("n_corpora (1 = exclusive, 4 = universal)")
    plt.ylabel("number of words")
    plt.tight_layout()
    plt.savefig(FIG / "corpus_overlap_bar.png", dpi=200)
    plt.close()

    # 5) happiness vs rank, per corpus (small multiples)
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, sharey=True)
    for ax, c in zip(axes.flat, CORPORA):
        sub = df[df[f"in_{c}"]]
        ax.scatter(sub[f"{c}_rank"], sub["happiness_average"], s=6, alpha=0.4)
        ax.axhline(5.0, color="red", linestyle=":", linewidth=0.8)
        ax.set_title(f"{c}  (n={len(sub)})", fontsize=10)
        ax.set_xlabel(f"{c}_rank (1 = most frequent)")
        ax.set_ylabel("happiness_average")
    fig.suptitle("Happiness vs frequency rank, per source corpus")
    plt.tight_layout()
    plt.savefig(FIG / "happiness_vs_rank_per_corpus.png", dpi=200)
    plt.close()

    print("[desc] wrote tables/ and figures/")
    print(by_corpus.to_string(index=False))


if __name__ == "__main__":
    main()
