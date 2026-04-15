"""
bootstrap_inference.py

Step 5: inferential comparisons. All three are non-parametric
bootstrap on document-level labMT scores (`happiness_weighted` in
data/processed/sotu_scored.csv).

Unit of analysis: one SOTU address. Score: weighted labMT happiness
with the Δh = 1 neutral-word filter applied at the word level during
scoring. Inference target: the mean of happiness_weighted inside each
stratum, and the difference in means between strata.

Superpopulation framing: I treat each era as a sample from a larger
(counterfactual) distribution of "addresses a president of that era
might have delivered." This is the standard move when you have a full
enumeration of a closed set and still want uncertainty: bootstrap the
observed distribution to stand in for that superpopulation. It is not
the same as sampling presidents, and I will not claim it is.

Three comparisons:

    Comparison 1 - era pairwise
        Three pairs: (Founding, Industrial), (Founding, Broadcast),
        (Industrial, Broadcast). Independent bootstrap of the two
        strata, difference in means, 95% percentile CI, probability
        that the difference is positive.

    Comparison 2 - modality
        written (<=1912) vs spoken (>=1913). Two strata, same
        machinery.

    Comparison 3 - per-era mean happiness with CI
        One bootstrap mean per era, so the reader can see where each
        era's mean sits absolutely, not just as a contrast. Also
        reports the difference between Broadcast and Founding as an
        across-the-corpus span.

Output:
    tables/comparison_1_era_pairwise.csv
    tables/comparison_2_modality.csv
    tables/comparison_3_era_means.csv
    tables/readme_fill_in.md
    figures/bootstrap_comparison_1.png
    figures/bootstrap_comparison_2.png
    figures/bootstrap_comparison_3.png

N_BOOT = 10,000, seed fixed to 20260415 (today's date when I froze
this script).
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

IN = PROC / "sotu_scored.csv"

N_BOOT = 10_000
RNG = np.random.default_rng(20260415)

ERA_ORDER = ["Founding", "Industrial", "Broadcast"]
ERA_COLOR = {
    "Founding":   "#4C72B0",
    "Industrial": "#DD8452",
    "Broadcast":  "#55A868",
}


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


def boot_mean_samples(x: np.ndarray) -> np.ndarray:
    """Return the raw N_BOOT resampled means, for density plotting."""
    if x.size == 0:
        return np.array([])
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        boot[i] = RNG.choice(x, size=x.size, replace=True).mean()
    return boot


def gaussian_kde_1d(samples: np.ndarray, grid: np.ndarray,
                    bw: float | None = None) -> np.ndarray:
    """
    Minimal 1-D Gaussian KDE evaluated on `grid`. Silverman's rule for
    bandwidth if `bw` is not given. No scipy dependency.
    """
    s = np.asarray(samples, dtype=float)
    n = s.size
    if n == 0:
        return np.zeros_like(grid)
    if bw is None:
        sd = float(s.std(ddof=1)) if n > 1 else 1.0
        bw = max(1.06 * sd * n ** (-0.2), 1e-6)
    # evaluate in chunks to keep memory modest
    out = np.zeros_like(grid, dtype=float)
    chunk = 1024
    coef = 1.0 / (np.sqrt(2.0 * np.pi) * bw * n)
    for start in range(0, n, chunk):
        block = s[start:start + chunk]
        diff = (grid[:, None] - block[None, :]) / bw
        out += np.exp(-0.5 * diff * diff).sum(axis=1)
    return out * coef


# -----------------------------------------------------------------------------
# Comparison 1, era pairwise
# -----------------------------------------------------------------------------

def comparison_1(df: pd.DataFrame) -> pd.DataFrame:
    print("\n== Comparison 1: era pairwise differences ==")
    rows = []
    for a, b in combinations(ERA_ORDER, 2):
        xa = df.loc[df["era"] == a, "happiness_weighted"].dropna().to_numpy()
        xb = df.loc[df["era"] == b, "happiness_weighted"].dropna().to_numpy()
        _, obs, lo, hi, pp = boot_diff(xa, xb)
        rows.append({
            "comparison": f"{a} − {b}",
            "n_a": int(xa.size),
            "n_b": int(xb.size),
            "mean_a": float(xa.mean()),
            "mean_b": float(xb.mean()),
            "observed_diff": obs,
            "ci_lower": lo,
            "ci_upper": hi,
            "prob_diff_positive": pp,
        })
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "comparison_1_era_pairwise.csv", index=False)
    print(out.to_string(index=False))

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ypos = np.arange(len(rows))[::-1]
    for y, r in zip(ypos, rows):
        xerr = [[r["observed_diff"] - r["ci_lower"]],
                [r["ci_upper"] - r["observed_diff"]]]
        ax.errorbar(r["observed_diff"], y, xerr=xerr, fmt="o",
                    capsize=4, color="black")
    ax.axvline(0, color="red", linestyle="--", linewidth=1)
    ax.set_yticks(ypos, [r["comparison"] for r in rows])
    ax.set_xlabel("Difference in mean happiness_weighted (A − B)")
    ax.set_title("Comparison 1, era pairwise differences (bootstrap 95% CI)")
    plt.tight_layout()
    plt.savefig(FIG / "bootstrap_comparison_1.png", dpi=200)
    plt.close()
    return out


# -----------------------------------------------------------------------------
# Comparison 2, modality (written vs spoken)
# -----------------------------------------------------------------------------

def comparison_2(df: pd.DataFrame) -> pd.DataFrame:
    print("\n== Comparison 2: written vs spoken ==")
    xa = df.loc[df["modality"] == "written", "happiness_weighted"].dropna().to_numpy()
    xb = df.loc[df["modality"] == "spoken", "happiness_weighted"].dropna().to_numpy()
    _, obs, lo, hi, pp = boot_diff(xa, xb)
    row = {
        "comparison": "written − spoken",
        "n_written": int(xa.size),
        "n_spoken": int(xb.size),
        "mean_written": float(xa.mean()),
        "mean_spoken": float(xb.mean()),
        "observed_diff": obs,
        "ci_lower": lo,
        "ci_upper": hi,
        "prob_diff_positive": pp,
    }
    out = pd.DataFrame([row])
    out.to_csv(TAB / "comparison_2_modality.csv", index=False)
    print(out.to_string(index=False))

    # Two half-violins-ish: just a strip + mean marker with CI
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for i, (lab, x) in enumerate([("written", xa), ("spoken", xb)]):
        jitter = RNG.normal(0, 0.04, size=x.size)
        ax.scatter(np.full_like(x, i) + jitter, x,
                   alpha=0.5, s=18, color="#888888")
        m, clo, chi = boot_mean(x)
        ax.errorbar(i, m, yerr=[[m - clo], [chi - m]], fmt="D",
                    color="black", capsize=5, markersize=7,
                    label=f"{lab} mean={m:.3f}")
    ax.set_xticks([0, 1], ["written (≤1912)", "spoken (≥1913)"])
    ax.set_ylabel("happiness_weighted (per document)")
    ax.set_title(f"Comparison 2, written vs spoken. "
                 f"diff = {obs:+.4f}  "
                 f"CI = [{lo:+.4f}, {hi:+.4f}]")
    plt.tight_layout()
    plt.savefig(FIG / "bootstrap_comparison_2.png", dpi=200)
    plt.close()
    return out


# -----------------------------------------------------------------------------
# Comparison 3, per-era mean with CI
# -----------------------------------------------------------------------------

def comparison_3(df: pd.DataFrame) -> pd.DataFrame:
    print("\n== Comparison 3: per-era mean happiness with CI ==")
    rows = []
    for era in ERA_ORDER:
        x = df.loc[df["era"] == era, "happiness_weighted"].dropna().to_numpy()
        m, lo, hi = boot_mean(x)
        rows.append({
            "era": era,
            "n_docs": int(x.size),
            "mean_happiness": m,
            "ci_lower": lo,
            "ci_upper": hi,
        })
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "comparison_3_era_means.csv", index=False)
    print(out.to_string(index=False))

    fig, ax = plt.subplots(figsize=(6.5, 4))
    xpos = np.arange(len(rows))
    means = [r["mean_happiness"] for r in rows]
    lows = [r["mean_happiness"] - r["ci_lower"] for r in rows]
    highs = [r["ci_upper"] - r["mean_happiness"] for r in rows]
    colors = [ERA_COLOR[r["era"]] for r in rows]
    ax.errorbar(xpos, means, yerr=[lows, highs], fmt="o",
                capsize=6, color="black", ecolor="#444444", zorder=3)
    for x, m, c in zip(xpos, means, colors):
        ax.scatter([x], [m], color=c, s=90, zorder=4, edgecolor="black")
    ax.set_xticks(xpos, [f"{r['era']}\nn={r['n_docs']}" for r in rows])
    ax.set_ylabel("mean happiness_weighted (95% bootstrap CI)")
    ax.set_title("Comparison 3, per-era mean happiness")
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
             "Produced by bootstrap_inference.py. Paste these into the",
             "[[...]] placeholders in README.md §5.",
             ""]
    lines.append("## Comparison 1, era pairwise")
    for _, r in c1.iterrows():
        lines.append(
            f"- {r['comparison']}: diff = {r['observed_diff']:+.4f}, "
            f"CI = [{r['ci_lower']:+.4f}, {r['ci_upper']:+.4f}], "
            f"mean_a = {r['mean_a']:.4f}, mean_b = {r['mean_b']:.4f}, "
            f"prob>0 = {r['prob_diff_positive']:.3f}"
        )
    lines.append("")
    lines.append("## Comparison 2, written vs spoken")
    for _, r in c2.iterrows():
        lines.append(
            f"- {r['comparison']}: diff = {r['observed_diff']:+.4f}, "
            f"CI = [{r['ci_lower']:+.4f}, {r['ci_upper']:+.4f}], "
            f"mean_written = {r['mean_written']:.4f}, "
            f"mean_spoken = {r['mean_spoken']:.4f}, "
            f"n = {int(r['n_written'])}/{int(r['n_spoken'])}"
        )
    lines.append("")
    lines.append("## Comparison 3, per-era mean happiness")
    for _, r in c3.iterrows():
        lines.append(
            f"- {r['era']}: mean = {r['mean_happiness']:.4f}, "
            f"CI = [{r['ci_lower']:.4f}, {r['ci_upper']:.4f}], "
            f"n_docs = {int(r['n_docs'])}"
        )
    lines.append("")
    (TAB / "readme_fill_in.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[save] {TAB / 'readme_fill_in.md'}")


# -----------------------------------------------------------------------------
# Bootstrap density plots. This is the "analytical" panel set: one histogram
# plus KDE curve per stratum / contrast, so the reader can see the full
# bootstrap distribution and not just a CI bar. Six panels total:
#
#   1. Per-era means (3 overlapping KDEs)         -> C3
#   2. Written vs spoken means (2 overlapping)    -> C2
#   3. Difference Industrial - Broadcast          -> C1, the robust claim
#   4. Difference Founding - Broadcast            -> C1, the borderline
#   5. Difference Founding - Industrial           -> C1, the noise case
#   6. Per-era difference sampling, all 3 pairs overlaid
# -----------------------------------------------------------------------------

ERA_HIST_COLOR = {
    "Founding":   "#4C72B0",
    "Industrial": "#DD8452",
    "Broadcast":  "#55A868",
}


def _draw_hist_kde(ax, samples: np.ndarray, color: str, label: str,
                   bins: int = 50) -> None:
    if samples.size == 0:
        return
    counts, edges = np.histogram(samples, bins=bins, density=True)
    ax.hist(samples, bins=edges, density=True, color=color,
            alpha=0.35, edgecolor=color, linewidth=0.4)
    pad = (edges[-1] - edges[0]) * 0.1
    grid = np.linspace(edges[0] - pad, edges[-1] + pad, 400)
    dens = gaussian_kde_1d(samples, grid)
    ax.plot(grid, dens, color=color, linewidth=2.0, label=label)


def _fill_ci(ax, samples: np.ndarray, color: str) -> tuple[float, float, float]:
    """Fill a 2.5–97.5 percentile band on the KDE curve."""
    lo, hi = np.percentile(samples, [2.5, 97.5])
    if samples.size == 0:
        return float("nan"), lo, hi
    sd = float(samples.std(ddof=1)) if samples.size > 1 else 1.0
    bw = max(1.06 * sd * samples.size ** (-0.2), 1e-6)
    pad = (samples.max() - samples.min()) * 0.15 + 3 * bw
    grid = np.linspace(samples.min() - pad, samples.max() + pad, 500)
    dens = gaussian_kde_1d(samples, grid, bw=bw)
    band = (grid >= lo) & (grid <= hi)
    ax.fill_between(grid[band], 0, dens[band], color=color, alpha=0.25)
    ax.plot(grid, dens, color=color, linewidth=2.2)
    return float(samples.mean()), lo, hi


def density_plots(df: pd.DataFrame) -> None:
    print("\n== Bootstrap density plots ==")

    era_samples: dict[str, np.ndarray] = {}
    for era in ERA_ORDER:
        x = df.loc[df["era"] == era, "happiness_weighted"].dropna().to_numpy()
        era_samples[era] = boot_mean_samples(x)

    # =================================================================
    # Figure A. C3 "per-era means" rich panel
    #    row 1, col 1: overlapping KDEs of the bootstrap means
    #    row 1, col 2: horizontal CI forest of the same three means
    #    row 2:        ridgeline-style per-era stacked density panels
    # =================================================================
    fig = plt.figure(figsize=(13, 7.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.4, 1.0],
                          hspace=0.45, wspace=0.28)

    ax_overlay = fig.add_subplot(gs[0, 0])
    summary_rows = []
    for era in ERA_ORDER:
        s = era_samples[era]
        m, lo, hi = _fill_ci(ax_overlay, s, ERA_HIST_COLOR[era])
        ax_overlay.axvline(m, color=ERA_HIST_COLOR[era],
                           linestyle="--", linewidth=1.2, alpha=0.85)
        summary_rows.append((era, m, lo, hi))
        ax_overlay.hist(s, bins=55, density=True, color=ERA_HIST_COLOR[era],
                        alpha=0.25, edgecolor=ERA_HIST_COLOR[era],
                        linewidth=0.3)
    handles = [plt.Line2D([0], [0], color=ERA_HIST_COLOR[e], linewidth=3)
               for e in ERA_ORDER]
    labels = [f"{e}  μ*={m:.3f}  CI=[{lo:.3f}, {hi:.3f}]"
              for e, m, lo, hi in summary_rows]
    ax_overlay.legend(handles, labels, fontsize=8, loc="upper left")
    ax_overlay.set_xlabel("bootstrapped mean happiness_weighted")
    ax_overlay.set_ylabel("density")
    ax_overlay.set_title("(a) Overlapping bootstrap distributions")

    ax_forest = fig.add_subplot(gs[0, 1])
    ypos = np.arange(len(summary_rows))[::-1]
    for y, (era, m, lo, hi) in zip(ypos, summary_rows):
        ax_forest.errorbar(m, y, xerr=[[m - lo], [hi - m]], fmt="o",
                           color=ERA_HIST_COLOR[era], markersize=10,
                           capsize=6, capthick=1.4, elinewidth=1.8,
                           markeredgecolor="black")
        ax_forest.text(hi + 0.004, y, f" {m:.3f}", va="center", fontsize=9)
    ax_forest.set_yticks(ypos, [r[0] for r in summary_rows])
    ax_forest.axvline(df["happiness_weighted"].mean(),
                      color="black", linestyle="--", linewidth=0.8,
                      label=f"grand mean = {df['happiness_weighted'].mean():.3f}")
    ax_forest.set_xlabel("mean happiness_weighted (95% CI)")
    ax_forest.set_title("(b) Per-era mean, forest view")
    ax_forest.legend(fontsize=8)

    ax_ridge = fig.add_subplot(gs[1, :])
    offsets = {era: i for i, era in enumerate(reversed(ERA_ORDER))}
    for era in ERA_ORDER:
        s = era_samples[era]
        sd = float(s.std(ddof=1)) if s.size > 1 else 1.0
        bw = max(1.06 * sd * s.size ** (-0.2), 1e-6)
        grid = np.linspace(s.min() - 5 * bw, s.max() + 5 * bw, 400)
        dens = gaussian_kde_1d(s, grid, bw=bw)
        dens = dens / dens.max() * 0.85
        y0 = offsets[era]
        ax_ridge.fill_between(grid, y0, y0 + dens,
                              color=ERA_HIST_COLOR[era], alpha=0.75)
        ax_ridge.plot(grid, y0 + dens, color="black", linewidth=0.6)
        _, m, lo, hi = summary_rows[ERA_ORDER.index(era)]
        ax_ridge.plot([m, m], [y0, y0 + 0.85], color="black", linewidth=1.0)
        ax_ridge.plot([lo, hi], [y0, y0], color="black", linewidth=2.0)
    ax_ridge.set_yticks(list(offsets.values()), list(offsets.keys()))
    ax_ridge.set_xlabel("bootstrapped mean happiness_weighted")
    ax_ridge.set_title("(c) Ridgeline view: the Broadcast bell has almost no "
                       "central overlap with Industrial")
    ax_ridge.set_ylim(-0.2, len(ERA_ORDER) + 0.1)

    fig.suptitle("Figure A — C3: per-era mean happiness, 10,000-sample bootstrap",
                 fontsize=13, y=1.0)
    plt.savefig(FIG / "density_era_means.png", dpi=200, bbox_inches="tight")
    plt.close()

    # =================================================================
    # Figure B. C2 written vs spoken rich panel
    #    two KDEs + CI band + vertical means + inline annotation
    # =================================================================
    xw = df.loc[df["modality"] == "written",
                "happiness_weighted"].dropna().to_numpy()
    xs = df.loc[df["modality"] == "spoken",
                "happiness_weighted"].dropna().to_numpy()
    sw = boot_mean_samples(xw)
    ss = boot_mean_samples(xs)

    fig = plt.figure(figsize=(13, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1.0], wspace=0.3)
    ax_dens = fig.add_subplot(gs[0, 0])
    ax_dot = fig.add_subplot(gs[0, 1])

    for s, color, label, raw in [
        (sw, "#4C72B0", "written (≤1912)", xw),
        (ss, "#C44E52", "spoken (≥1913)", xs),
    ]:
        m, lo, hi = _fill_ci(ax_dens, s, color)
        ax_dens.axvline(m, color=color, linestyle="--", linewidth=1.4)
        ax_dens.hist(s, bins=55, density=True, color=color, alpha=0.22,
                     edgecolor=color, linewidth=0.3,
                     label=f"{label}  n={raw.size}  μ*={m:.3f}  "
                           f"CI=[{lo:.3f}, {hi:.3f}]")
    ax_dens.set_xlabel("bootstrapped mean happiness_weighted")
    ax_dens.set_ylabel("density")
    ax_dens.set_title("(a) Bootstrap distributions overlap almost entirely")
    ax_dens.legend(fontsize=8, loc="upper left")

    # Right panel: raw per-document strip with means + CI
    rng = np.random.default_rng(12345)
    for i, (lab, raw, color) in enumerate([
        ("written", xw, "#4C72B0"),
        ("spoken", xs, "#C44E52"),
    ]):
        jitter = rng.normal(0, 0.05, size=raw.size)
        ax_dot.scatter(np.full_like(raw, i) + jitter, raw,
                       color=color, alpha=0.45, s=22, edgecolor="white",
                       linewidth=0.3)
        m = raw.mean()
        s_boot = boot_mean_samples(raw)
        lo_c, hi_c = np.percentile(s_boot, [2.5, 97.5])
        ax_dot.errorbar(i, m, yerr=[[m - lo_c], [hi_c - m]], fmt="D",
                        color="black", capsize=6, markersize=9, elinewidth=1.6)
        ax_dot.text(i + 0.15, m, f" μ={m:.3f}\n CI=[{lo_c:.3f},{hi_c:.3f}]",
                    fontsize=8, va="center")
    ax_dot.set_xticks([0, 1], ["written\n(n=124)", "spoken\n(n=109)"])
    ax_dot.set_ylabel("happiness_weighted per document")
    ax_dot.set_title("(b) Per-document strip plot with bootstrap CI")

    fig.suptitle("Figure B — C2: written vs spoken addresses (the "
                 "Wilson-1913 alternative hypothesis)", fontsize=13, y=1.02)
    plt.savefig(FIG / "density_written_vs_spoken.png", dpi=200,
                bbox_inches="tight")
    plt.close()

    # =================================================================
    # Figure C. C1 era-pair differences rich panel
    #    3x1 grid, one per pair, each with full bootstrap distribution,
    #    shaded CI band, observed line, zero line, inline annotation.
    # =================================================================
    diff_pairs = [
        ("Industrial", "Broadcast", "#55A868",
         "(a) Industrial − Broadcast — robust across all four conditions"),
        ("Founding", "Broadcast", "#4C72B0",
         "(b) Founding − Broadcast — borderline, dissolves under coverage cut"),
        ("Founding", "Industrial", "#DD8452",
         "(c) Founding − Industrial — noise, CI straddles zero"),
    ]
    diff_samples: dict[str, tuple[np.ndarray, float, float, float, float]] = {}
    for a, b, _, _ in diff_pairs:
        xa = df.loc[df["era"] == a, "happiness_weighted"].dropna().to_numpy()
        xb = df.loc[df["era"] == b, "happiness_weighted"].dropna().to_numpy()
        boot, obs, lo, hi, pp = boot_diff(xa, xb)
        diff_samples[f"{a}-{b}"] = (boot, obs, lo, hi, pp)

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for ax, (a, b, color, title) in zip(axes, diff_pairs):
        boot, obs, lo, hi, pp = diff_samples[f"{a}-{b}"]
        m, lo2, hi2 = _fill_ci(ax, boot, color)
        ax.hist(boot, bins=70, density=True, color=color, alpha=0.22,
                edgecolor=color, linewidth=0.3)
        ax.axvline(0, color="red", linestyle="--", linewidth=1.4,
                   label="zero (no difference)")
        ax.axvline(obs, color="black", linestyle=":", linewidth=1.2,
                   label=f"observed = {obs:+.4f}")
        ax.text(
            0.98, 0.88,
            f"CI = [{lo:+.4f}, {hi:+.4f}]\nP(diff > 0) = {pp:.4f}\n"
            f"n_a = {int((df['era'] == a).sum())}, "
            f"n_b = {int((df['era'] == b).sum())}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=color, linewidth=1.0),
        )
        ax.set_title(title, fontsize=11)
        ax.set_ylabel("density")
        ax.legend(fontsize=8, loc="upper left")
    axes[-1].set_xlabel("bootstrapped difference in mean happiness_weighted "
                        "(A − B)")
    fig.suptitle("Figure C — C1: all three era-pair bootstrap difference "
                 "distributions", fontsize=13, y=1.0)
    plt.tight_layout(rect=(0, 0, 1, 0.98))
    plt.savefig(FIG / "density_c1_all_pairs.png", dpi=200,
                bbox_inches="tight")
    plt.close()

    # also dump the three individual figures that I referenced earlier,
    # now with the same rich panel look, one-per-file for the README.
    for a, b, color, title in diff_pairs:
        boot, obs, lo, hi, pp = diff_samples[f"{a}-{b}"]
        fig, ax = plt.subplots(figsize=(9, 4.8))
        _fill_ci(ax, boot, color)
        ax.hist(boot, bins=70, density=True, color=color, alpha=0.22,
                edgecolor=color, linewidth=0.3)
        ax.axvline(0, color="red", linestyle="--", linewidth=1.4,
                   label="zero (no difference)")
        ax.axvline(obs, color="black", linestyle=":", linewidth=1.2,
                   label=f"observed = {obs:+.4f}")
        ax.text(
            0.98, 0.88,
            f"CI = [{lo:+.4f}, {hi:+.4f}]\n"
            f"P(diff > 0) = {pp:.4f}\n"
            f"n_{a} = {int((df['era'] == a).sum())}, "
            f"n_{b} = {int((df['era'] == b).sum())}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=color, linewidth=1.0),
        )
        ax.set_xlabel("bootstrapped difference in mean happiness_weighted")
        ax.set_ylabel("density")
        ax.set_title(title)
        ax.legend(fontsize=8, loc="upper left")
        plt.tight_layout()
        fname = f"density_diff_{a.lower()}_{b.lower()}.png"
        plt.savefig(FIG / fname, dpi=200)
        plt.close()

    print("[save] density_era_means.png density_written_vs_spoken.png "
          "density_c1_all_pairs.png + 3 per-pair diffs")


def main() -> None:
    df = pd.read_csv(IN)
    c1 = comparison_1(df)
    c2 = comparison_2(df)
    c3 = comparison_3(df)
    density_plots(df)
    dump_fill_in(c1, c2, c3)


if __name__ == "__main__":
    main()
