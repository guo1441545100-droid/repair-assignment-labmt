"""
tokenize_and_score.py

Step 3: turn the SOTU corpus into one row per document, with a labMT
happiness score and the metadata I need for the comparisons in §5 of
the README.

This is the Measurement step of the assignment. The rubric asks for
tokenisation, labMT matching, coverage / OOV handling, and document
scoring, so each of those decisions is made explicit here rather than
buried in a helper.

Pipeline per document:

 1. Read the .txt file. Strip the leading three-line preamble
    ("{president}\\n{date}\\n\\n") that the upstream repo prepends to
    every file, so that the preamble words do not contaminate the score.
 2. Lowercase, collapse any non-letter run to a single space, split
    on whitespace. This is a deliberately simple tokeniser: no stemming,
    no lemmatisation, no stop-word removal. Reasons:
      - labMT entries are surface forms already (e.g. "laughter",
        "laughed", "laughing" are separate rows), so stemming would
        destroy the match.
      - stop words are not in labMT anyway, they drop out naturally
        in the lookup step.
      - simplicity makes the coverage number interpretable.
 3. Look every token up in labMT. A token counts as "matched" iff it
    appears in the labMT word column AND its happiness_average is
    outside the neutral band |h - 5| <= DELTA_H_PRIMARY. The filter
    matches the neutral-word convention from Dodds et al. 2011 and is
    applied at the word level, which is the granularity at which
    neutrality is actually defined.
 4. Score per document:
        happiness_weighted = sum(h_i * freq_i) / sum(freq_i)
    over matched tokens. This is the Dodds hedonometer formula. I also
    store an unweighted version (mean over matched types) so the
    robustness script can compare the two.
 5. Coverage = n_matched_tokens / n_tokens_total. This is the diagnostic
    that tells you how much of a document labMT "sees". A document with
    coverage < 10% is flagged; the robustness script drops those.

Metadata parsing:
    Filename pattern is {president_slug}-{month}_{day}-{year}.txt. I
    pull year out of the last hyphen-separated chunk, slug out of the
    first. From the year I derive three metadata variables:
      - era: one of {"Founding", "Industrial", "Broadcast"} with
        boundaries 1860 / 1945. Rationale is in README §4.
      - modality: "written" if year <= 1912 else "spoken", because
        Wilson revived the oral delivery in 1913.
      - half_century: a coarser facet for descriptive plots.

Output:
    data/processed/sotu_scored.csv
        one row per speech, columns:
        filename, president, year, era, modality, half_century,
        n_tokens, n_types, n_matched_tokens, n_matched_types,
        coverage, happiness_weighted, happiness_unweighted
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOTU_DIR = RAW / "sotu"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

LABMT_CSV = PROC / "labmt_clean.csv"
OUT = PROC / "sotu_scored.csv"

DELTA_H_PRIMARY = 1.0

TOKEN_SPLIT_RE = re.compile(r"[^a-z']+")
YEAR_RE = re.compile(r"(\d{4})")

ERA_BOUNDS = [
    ("Founding",   1790, 1860),
    ("Industrial", 1861, 1945),
    ("Broadcast",  1946, 2025),
]


def era_of(year: int) -> str:
    for name, lo, hi in ERA_BOUNDS:
        if lo <= year <= hi:
            return name
    return "Unknown"


def modality_of(year: int) -> str:
    # Jefferson switched to written in 1801. Wilson broke that tradition
    # in 1913 by delivering the address in person. I use 1913 as the
    # cut. This is coarse, some post-1913 addresses were written, but
    # the spoken-oral genre is the dominant mode after Wilson.
    return "written" if year <= 1912 else "spoken"


def half_century_of(year: int) -> str:
    base = (year // 50) * 50
    return f"{base}-{base + 49}"


def parse_filename(name: str) -> tuple[str, int] | None:
    # Drop extension, split on '-', keep the last 4-digit chunk as year,
    # join the rest as president slug (without trailing hyphen).
    stem = name[:-4] if name.endswith(".txt") else name
    parts = stem.split("-")
    if len(parts) < 2:
        return None
    last = parts[-1]
    m = YEAR_RE.search(last)
    if not m:
        return None
    year = int(m.group(1))
    president = parts[0].strip("_").replace("_", " ").title()
    return president, year


def strip_preamble(text: str) -> str:
    # The upstream files begin with three lines: name, date, blank.
    # Everything after the first blank line is the body.
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            return "\n".join(lines[i + 1:])
    return text


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = TOKEN_SPLIT_RE.split(text)
    return [t for t in tokens if t and any(c.isalpha() for c in t)]


def load_labmt_scores() -> tuple[dict[str, float], dict[str, float]]:
    df = pd.read_csv(LABMT_CSV)
    scores = dict(zip(df["word"].astype(str), df["happiness_average"].astype(float)))
    # also return the filtered map for the primary analysis
    mask = (df["happiness_average"] - 5.0).abs() > DELTA_H_PRIMARY
    dff = df.loc[mask]
    filtered = dict(zip(dff["word"].astype(str), dff["happiness_average"].astype(float)))
    return scores, filtered


def score_document(tokens: list[str], filt: dict[str, float]) -> dict:
    counts = Counter(tokens)
    n_tokens = sum(counts.values())
    n_types = len(counts)
    matched_tokens = 0
    matched_types = 0
    num_w = 0.0
    den_w = 0
    unweighted_accum = 0.0
    for w, c in counts.items():
        h = filt.get(w)
        if h is None:
            continue
        matched_types += 1
        matched_tokens += c
        num_w += h * c
        den_w += c
        unweighted_accum += h
    return {
        "n_tokens": n_tokens,
        "n_types": n_types,
        "n_matched_tokens": matched_tokens,
        "n_matched_types": matched_types,
        "coverage": matched_tokens / n_tokens if n_tokens else float("nan"),
        "happiness_weighted": num_w / den_w if den_w else float("nan"),
        "happiness_unweighted": (unweighted_accum / matched_types
                                 if matched_types else float("nan")),
    }


def main() -> None:
    if not LABMT_CSV.exists():
        raise FileNotFoundError(
            f"missing {LABMT_CSV}, run load_labmt.py first")
    _, filt = load_labmt_scores()
    print(f"[score] labMT filtered vocabulary (|h-5|>{DELTA_H_PRIMARY}): "
          f"{len(filt)} words")

    files = sorted(SOTU_DIR.glob("*.txt"))
    if not files:
        raise FileNotFoundError(
            f"no .txt files under {SOTU_DIR}, run fetch_data.py first")
    print(f"[score] scoring {len(files)} SOTU documents")

    rows = []
    for p in files:
        meta = parse_filename(p.name)
        if meta is None:
            print(f"[score] WARN: cannot parse filename, skipping: {p.name}")
            continue
        president, year = meta
        raw = p.read_text(encoding="utf-8", errors="replace")
        body = strip_preamble(raw)
        tokens = tokenize(body)
        scored = score_document(tokens, filt)
        rows.append({
            "filename": p.name,
            "president": president,
            "year": year,
            "era": era_of(year),
            "modality": modality_of(year),
            "half_century": half_century_of(year),
            **scored,
        })

    df = pd.DataFrame(rows).sort_values(["year", "president"]).reset_index(drop=True)
    df.to_csv(OUT, index=False)
    print(f"[score] wrote {OUT} with {len(df)} rows")

    print("\n[score] per-era summary:")
    g = df.groupby("era", sort=False).agg(
        n_docs=("filename", "count"),
        mean_year=("year", "mean"),
        mean_cov=("coverage", "mean"),
        mean_h=("happiness_weighted", "mean"),
        sd_h=("happiness_weighted", "std"),
    ).reindex([e[0] for e in ERA_BOUNDS])
    print(g.to_string())

    flagged = (df["coverage"] < 0.10).sum()
    print(f"\n[score] documents with coverage < 10%: {flagged}")
    print(f"[score] overall mean coverage: {df['coverage'].mean():.3f}")


if __name__ == "__main__":
    main()
