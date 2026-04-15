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


def density_plots(df: pd.DataFrame) -> None:
    print("\n== Bootstrap density plots ==")

    # Precompute the per-era mean samples (used twice: panel 1 and panel 6)
    era_samples: dict[str, np.ndarray] = {}
    for era in ERA_ORDER:
        x = df.loc[df["era"] == era, "happiness_weighted"].dropna().to_numpy()
        era_samples[era] = boot_mean_samples(x)

    # --- 1. Per-era means, 3 overlapping KDEs -----------------------------
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for era in ERA_ORDER:
        s = era_samples[era]
        lo, hi = np.percentile(s, [2.5, 97.5])
        _draw_hist_kde(
            ax, s, ERA_HIST_COLOR[era],
            label=f"{era}  mean={s.mean():.3f}  CI=[{lo:.3f}, {hi:.3f}]")
    ax.set_xlabel("bootstrapped mean happiness_weighted")
    ax.set_ylabel("density")
    ax.set_title("Bootstrap distributions of per-era means\n"
                 "(C3: 10,000 resamples per era)")
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout()
    plt.savefig(FIG / "density_era_means.png", dpi=200)
    plt.close()

    # --- 2. Written vs spoken means ---------------------------------------
    xw = df.loc[df["modality"] == "written", "happiness_weighted"].dropna().to_numpy()
    xs = df.loc[df["modality"] == "spoken", "happiness_weighted"].dropna().to_numpy()
    sw = boot_mean_samples(xw)
    ss = boot_mean_samples(xs)

    fig, ax = plt.subplots(figsize=(8, 4.6))
    for s, color, label, raw in [
        (sw, "#4C72B0", "written (≤1912)", xw),
        (ss, "#C44E52", "spoken (≥1913)", xs),
    ]:
        lo, hi = np.percentile(s, [2.5, 97.5])
        _draw_hist_kde(
            ax, s, color,
            label=f"{label}  n={raw.size}  mean={s.mean():.3f}  "
                  f"CI=[{lo:.3f}, {hi:.3f}]")
    ax.set_xlabel("bootstrapped mean happiness_weighted")
    ax.set_ylabel("density")
    ax.set_title("C2: bootstrap distributions of written vs spoken means")
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout()
    plt.savefig(FIG / "density_written_vs_spoken.png", dpi=200)
    plt.close()

    # --- 3, 4, 5. Difference distributions for each era pair ---------------
    diff_panels = [
        ("Industrial", "Broadcast", "density_diff_industrial_broadcast.png",
         "C1a: Industrial − Broadcast\n(the robust claim)"),
        ("Founding", "Broadcast", "density_diff_founding_broadcast.png",
         "C1b: Founding − Broadcast\n(borderline, half coverage artefact)"),
        ("Founding", "Industrial", "density_diff_founding_industrial.png",
         "C1c: Founding − Industrial\n(noise, CI straddles zero)"),
    ]
    diff_samples: dict[str, np.ndarray] = {}
    for a, b, fname, title in diff_panels:
        xa = df.loc[df["era"] == a, "happiness_weighted"].dropna().to_numpy()
        xb = df.loc[df["era"] == b, "happiness_weighted"].dropna().to_numpy()
        boot, obs, lo, hi, pp = boot_diff(xa, xb)
        diff_samples[f"{a}-{b}"] = boot

        fig, ax = plt.subplots(figsize=(8, 4.6))
        _draw_hist_kde(ax, boot, "#6A5ACD",
                       label=f"{a} − {b}\nobserved = {obs:+.4f}\n"
                             f"CI = [{lo:+.4f}, {hi:+.4f}]\n"
                             f"P(diff > 0) = {pp:.3f}")
        ax.axvline(0, color="red", linestyle="--", linewidth=1.2,
                   label="zero (no difference)")
        ax.axvline(obs, color="black", linestyle=":", linewidth=1.0,
                   label=f"observed {obs:+.4f}")
        ax.set_xlabel("bootstrapped difference in mean happiness_weighted")
        ax.set_ylabel("density")
        ax.set_title(title)
        ax.legend(fontsize=8, loc="upper right")
        plt.tight_layout()
        plt.savefig(FIG / fname, dpi=200)
        plt.close()

    # --- 6. All three C1 difference distributions overlaid ----------------
    fig, ax = plt.subplots(figsize=(9, 4.6))
    palette = [("Industrial-Broadcast", "#55A868"),
               ("Founding-Broadcast",   "#4C72B0"),
               ("Founding-Industrial",  "#DD8452")]
    for key, color in palette:
        s = diff_samples[key]
        lo, hi = np.percentile(s, [2.5, 97.5])
        pp = float((s > 0).mean())
        _draw_hist_kde(
            ax, s, color,
            label=f"{key.replace('-', ' − ')}  "
                  f"CI=[{lo:+.3f}, {hi:+.3f}]  P>0={pp:.2f}")
    ax.axvline(0, color="red", linestyle="--", linewidth=1.2)
    ax.set_xlabel("bootstrapped difference in mean happiness_weighted (A − B)")
    ax.set_ylabel("density")
    ax.set_title("C1 overview: all three era-pair difference distributions")
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout()
    plt.savefig(FIG / "density_c1_all_pairs.png", dpi=200)
    plt.close()

    print("[save] 6 density plots under figures/density_*.png")


def main() -> None:
    df = pd.read_csv(IN)
    c1 = comparison_1(df)
    c2 = comparison_2(df)
    c3 = comparison_3(df)
    density_plots(df)
    dump_fill_in(c1, c2, c3)


if __name__ == "__main__":
    main()
