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
    # Figure 1: the "corpus at a glance" four-panel grid. This is the
    # front-page descriptive figure for the README. Each panel uses the
    # same ERA_COLOR palette so the reader can track the three eras
    # visually across panels.
    fig = plt.figure(figsize=(13, 9))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25)

    # (a) year vs happiness scatter with era boundary shading, grand mean,
    #     and a per-era rolling median line
    ax1 = fig.add_subplot(gs[0, 0])
    sotu_sorted = sotu.sort_values("year")
    for era in ERA_ORDER:
        sub = sotu_sorted[sotu_sorted["era"] == era]
        ax1.scatter(sub["year"], sub["happiness_weighted"],
                    color=ERA_COLOR[era], s=26, alpha=0.75,
                    edgecolor="white", linewidth=0.4, label=era, zorder=3)
    # era background bands
    for era, (lo_y, hi_y) in [
        ("Founding",   (1790, 1860)),
        ("Industrial", (1861, 1945)),
        ("Broadcast",  (1946, 2020)),
    ]:
        ax1.axvspan(lo_y, hi_y, color=ERA_COLOR[era], alpha=0.08, zorder=1)
    # per-era mean line
    for era in ERA_ORDER:
        sub = sotu[sotu["era"] == era]
        m = sub["happiness_weighted"].mean()
        yrs = sub["year"]
        ax1.hlines(m, yrs.min(), yrs.max(),
                   colors=ERA_COLOR[era], linewidth=2.4, zorder=4)
        ax1.text(yrs.max() + 1, m, f"  μ={m:.3f}", fontsize=8,
                 color=ERA_COLOR[era], va="center")
    grand = sotu["happiness_weighted"].mean()
    ax1.axhline(grand, color="black", linestyle="--", linewidth=0.8,
                label=f"grand mean = {grand:.3f}")
    ax1.set_xlabel("year")
    ax1.set_ylabel("happiness_weighted")
    ax1.set_title("(a) Per-document score over time, with era means")
    ax1.legend(fontsize=8, loc="lower left")

    # (b) density of happiness_weighted by era (hist + KDE-like smooth)
    ax2 = fig.add_subplot(gs[0, 1])
    for era in ERA_ORDER:
        s = sotu.loc[sotu["era"] == era, "happiness_weighted"].dropna().to_numpy()
        ax2.hist(s, bins=22, alpha=0.45, density=True,
                 color=ERA_COLOR[era], edgecolor=ERA_COLOR[era],
                 linewidth=0.4,
                 label=f"{era} (n={len(s)})")
        # smooth overlay via np.histogram + simple moving average
        counts, edges = np.histogram(s, bins=60, density=True)
        centres = 0.5 * (edges[:-1] + edges[1:])
        kernel = np.array([1, 2, 4, 6, 4, 2, 1], dtype=float)
        kernel /= kernel.sum()
        smooth = np.convolve(counts, kernel, mode="same")
        ax2.plot(centres, smooth, color=ERA_COLOR[era], linewidth=2.0)
    ax2.set_xlabel("happiness_weighted (Δh=1 filter)")
    ax2.set_ylabel("density")
    ax2.set_title("(b) Per-document score distribution, by era")
    ax2.legend(fontsize=8)

    # (c) coverage over time with per-era mean lines
    ax3 = fig.add_subplot(gs[1, 0])
    for era in ERA_ORDER:
        sub = sotu[sotu["era"] == era]
        ax3.scatter(sub["year"], sub["coverage"],
                    color=ERA_COLOR[era], s=22, alpha=0.75,
                    edgecolor="white", linewidth=0.4, label=era)
        mc = sub["coverage"].mean()
        ax3.hlines(mc, sub["year"].min(), sub["year"].max(),
                   colors=ERA_COLOR[era], linewidth=2.2)
    ax3.axhline(0.18, color="red", linestyle=":", linewidth=1.0,
                label="robustness cut = 0.18")
    ax3.set_xlabel("year")
    ax3.set_ylabel("labMT coverage per document")
    ax3.set_title("(c) Coverage over time — the confound flagged in §6")
    ax3.legend(fontsize=8, loc="upper left")

    # (d) document length (tokens) over time, log-y to see the 19C long
    #     reports vs 20C short speeches contrast
    ax4 = fig.add_subplot(gs[1, 1])
    for era in ERA_ORDER:
        sub = sotu[sotu["era"] == era]
        ax4.scatter(sub["year"], sub["n_tokens"],
                    color=ERA_COLOR[era], s=22, alpha=0.75,
                    edgecolor="white", linewidth=0.4, label=era)
    ax4.set_yscale("log")
    ax4.set_xlabel("year")
    ax4.set_ylabel("n_tokens per document (log scale)")
    ax4.set_title("(d) Document length over time, log axis")
    ax4.legend(fontsize=8, loc="upper left")

    fig.suptitle("Corpus at a glance: 233 SOTU addresses, 1790-2019",
                 fontsize=13, y=0.995)
    plt.savefig(FIG / "corpus_at_a_glance.png", dpi=200,
                bbox_inches="tight")
    plt.close()

    # Figure 2: dedicated per-era density overlay (single panel, bigger
    # type, used as the "analytical" hist in README §3)
    fig, ax = plt.subplots(figsize=(9, 5))
    for era in ERA_ORDER:
        s = sotu.loc[sotu["era"] == era, "happiness_weighted"].dropna().to_numpy()
        ax.hist(s, bins=22, alpha=0.40, density=True,
                color=ERA_COLOR[era],
                label=f"{era}  n={len(s)}  μ={s.mean():.3f}  σ={s.std(ddof=1):.3f}")
        counts, edges = np.histogram(s, bins=60, density=True)
        centres = 0.5 * (edges[:-1] + edges[1:])
        kernel = np.array([1, 2, 4, 6, 4, 2, 1], dtype=float)
        kernel /= kernel.sum()
        smooth = np.convolve(counts, kernel, mode="same")
        ax.plot(centres, smooth, color=ERA_COLOR[era], linewidth=2.4)
        ax.axvline(s.mean(), color=ERA_COLOR[era], linestyle="--",
                   linewidth=1.4, alpha=0.9)
    ax.set_xlabel("happiness_weighted (Δh=1 filter)")
    ax.set_ylabel("density")
    ax.set_title("SOTU happiness distribution by era, 233 documents")
    ax.legend(fontsize=9, loc="upper left", framealpha=0.92)
    plt.tight_layout()
    plt.savefig(FIG / "sotu_hist_happiness_by_era.png", dpi=200)
    plt.close()

    # Figure 3: coverage-vs-happiness scatter, to make the §6 confound
    # visible BEFORE we ever mention the robustness condition.
    fig, ax = plt.subplots(figsize=(9, 5))
    for era in ERA_ORDER:
        sub = sotu[sotu["era"] == era]
        ax.scatter(sub["coverage"], sub["happiness_weighted"],
                   color=ERA_COLOR[era], s=34, alpha=0.8,
                   edgecolor="white", linewidth=0.5,
                   label=f"{era}  (cov̄={sub['coverage'].mean():.3f})")
    ax.axvline(0.18, color="red", linestyle=":", linewidth=1.2,
               label="robustness cut = 0.18")
    ax.set_xlabel("labMT coverage per document")
    ax.set_ylabel("happiness_weighted")
    ax.set_title("Coverage confound: the Broadcast bump sits inside a higher-coverage zone")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(FIG / "coverage_vs_happiness.png", dpi=200)
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
