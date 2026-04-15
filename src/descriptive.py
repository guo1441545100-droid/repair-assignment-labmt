"""
descriptive.py

Step 4: descriptive statistics and distribution plots for the SOTU
corpus, now scored at the document level.

Inputs:
    data/processed/labmt_clean.csv   (for the labMT-side sanity panel)
    data/processed/sotu_scored.csv   (one row per SOTU address)

Outputs:
    tables/desc_labmt_overall.csv
    tables/desc_sotu_by_era.csv
    tables/desc_sotu_by_modality.csv
    tables/desc_sotu_coverage.csv
    tables/desc_sotu_docs_per_president.csv
    figures/labmt_hist_happiness.png
    figures/sotu_hist_happiness_by_era.png
    figures/sotu_scatter_year_vs_happiness.png
    figures/sotu_coverage_hist.png
    figures/sotu_tokens_per_doc.png

The descriptive stage has two jobs in this repair. First, verify the
instrument: labMT's own happiness distribution is shown so the reader
can see the scoring scale before any inference happens. Second, show
the corpus: how many documents per era, how long they are, how much of
each document labMT actually sees, and where the per-document scores
sit on the scale.
"""

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

LABMT_CSV = PROC / "labmt_clean.csv"
SOTU_CSV = PROC / "sotu_scored.csv"

ERA_ORDER = ["Founding", "Industrial", "Broadcast"]
ERA_COLOR = {
    "Founding":   "#4C72B0",
    "Industrial": "#DD8452",
    "Broadcast":  "#55A868",
}


def summary(series: pd.Series) -> pd.Series:
    s = series.dropna()
    return pd.Series({
        "n": int(s.shape[0]),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=1)) if s.shape[0] > 1 else float("nan"),
        "median": float(s.median()),
        "q25": float(s.quantile(0.25)),
        "q75": float(s.quantile(0.75)),
        "min": float(s.min()),
        "max": float(s.max()),
    })


def main() -> None:
    labmt = pd.read_csv(LABMT_CSV)
    sotu = pd.read_csv(SOTU_CSV)

    # ---- labMT side: one-line sanity panel ----
    labmt_overall = summary(labmt["happiness_average"]).to_frame("value").reset_index()
    labmt_overall.columns = ["metric", "value"]
    labmt_overall.to_csv(TAB / "desc_labmt_overall.csv", index=False)

    plt.figure(figsize=(7, 4))
    plt.hist(labmt["happiness_average"], bins=40, color="#888888")
    plt.axvline(labmt["happiness_average"].mean(), linestyle="--",
                color="black",
                label=f"mean = {labmt['happiness_average'].mean():.3f}")
    plt.axvspan(4.0, 6.0, color="red", alpha=0.08,
                label="neutral band |h-5|<=1")
    plt.title(f"labMT 1.0: happiness distribution (n={len(labmt)} words)")
    plt.xlabel("happiness_average (1 = least happy, 9 = most happy)")
    plt.ylabel("word count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "labmt_hist_happiness.png", dpi=200)
    plt.close()

    # ---- SOTU side ----
    by_era_rows = []
    for era in ERA_ORDER:
        s = sotu.loc[sotu["era"] == era, "happiness_weighted"]
        row = summary(s)
        row["era"] = era
        by_era_rows.append(row)
    by_era = pd.DataFrame(by_era_rows)[
        ["era", "n", "mean", "std", "median", "q25", "q75", "min", "max"]
    ]
    by_era.to_csv(TAB / "desc_sotu_by_era.csv", index=False)

    by_mod_rows = []
    for mod in ["written", "spoken"]:
        s = sotu.loc[sotu["modality"] == mod, "happiness_weighted"]
        row = summary(s)
        row["modality"] = mod
        by_mod_rows.append(row)
    by_mod = pd.DataFrame(by_mod_rows)[
        ["modality", "n", "mean", "std", "median", "q25", "q75", "min", "max"]
    ]
    by_mod.to_csv(TAB / "desc_sotu_by_modality.csv", index=False)

    cov = summary(sotu["coverage"]).to_frame("value").reset_index()
    cov.columns = ["metric", "value"]
    cov.to_csv(TAB / "desc_sotu_coverage.csv", index=False)

    per_pres = (sotu.groupby("president", sort=False)
                .agg(n_docs=("filename", "count"),
                     first_year=("year", "min"),
                     last_year=("year", "max"),
                     mean_h=("happiness_weighted", "mean"))
                .reset_index()
                .sort_values("first_year"))
    per_pres.to_csv(TAB / "desc_sotu_docs_per_president.csv", index=False)

    # --- figures ---
    # overlay histogram of weighted happiness by era
    plt.figure(figsize=(7.5, 4.5))
    for era in ERA_ORDER:
        s = sotu.loc[sotu["era"] == era, "happiness_weighted"].dropna()
        plt.hist(s, bins=25, alpha=0.5, density=True,
                 color=ERA_COLOR[era], label=f"{era} (n={len(s)})")
    plt.xlabel("happiness_weighted (per-document labMT score, filtered Δh=1)")
    plt.ylabel("density")
    plt.title("SOTU happiness distribution by era")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "sotu_hist_happiness_by_era.png", dpi=200)
    plt.close()

    # scatter year vs happiness
    plt.figure(figsize=(9, 4.5))
    for era in ERA_ORDER:
        sub = sotu[sotu["era"] == era]
        plt.scatter(sub["year"], sub["happiness_weighted"],
                    color=ERA_COLOR[era], s=22, alpha=0.85, label=era)
    plt.axhline(sotu["happiness_weighted"].mean(), color="black",
                linestyle="--", linewidth=0.8,
                label=f"grand mean = {sotu['happiness_weighted'].mean():.3f}")
    # era boundaries
    for _, lo, hi in [("", 1860, 1860), ("", 1945, 1945)]:
        plt.axvline(hi + 0.5, color="grey", linestyle=":", linewidth=0.8)
    plt.xlabel("year")
    plt.ylabel("happiness_weighted")
    plt.title("SOTU happiness over time, 1790-2020")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "sotu_scatter_year_vs_happiness.png", dpi=200)
    plt.close()

    # coverage distribution
    plt.figure(figsize=(7, 4))
    plt.hist(sotu["coverage"], bins=30, color="#6A5ACD")
    plt.axvline(sotu["coverage"].mean(), linestyle="--", color="black",
                label=f"mean = {sotu['coverage'].mean():.3f}")
    plt.axvline(0.10, linestyle=":", color="red",
                label="robustness cut = 0.10")
    plt.xlabel("labMT coverage per document  (matched tokens / total tokens)")
    plt.ylabel("document count")
    plt.title("How much of each SOTU does labMT see?")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "sotu_coverage_hist.png", dpi=200)
    plt.close()

    # tokens per doc
    plt.figure(figsize=(7, 4))
    plt.hist(sotu["n_tokens"], bins=40, color="#888888")
    plt.xlabel("n_tokens per document (after simple tokenisation)")
    plt.ylabel("document count")
    plt.title("SOTU document length (tokens)")
    plt.tight_layout()
    plt.savefig(FIG / "sotu_tokens_per_doc.png", dpi=200)
    plt.close()

    print("[desc] wrote tables and figures")
    print("\nby era:")
    print(by_era.to_string(index=False))
    print("\nby modality:")
    print(by_mod.to_string(index=False))
    print(f"\ndocs total: {len(sotu)}, "
          f"mean coverage: {sotu['coverage'].mean():.3f}, "
          f"mean tokens/doc: {sotu['n_tokens'].mean():.0f}")


if __name__ == "__main__":
    main()
