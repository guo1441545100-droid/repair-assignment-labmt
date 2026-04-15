"""
load_labmt.py

Step 2: load the raw Data_Set_S1.txt and write a cleaned, enriched
version to data/processed/labmt_clean.csv.

"Cleaned" means:
 - the three metadata lines at the top of the file are skipped;
 - the '--' placeholder in the rank columns is converted to NaN;
 - numeric columns are coerced to float;
 - the `word` column is lowered and whitespace-stripped;
 - any accidentally duplicated word rows are dropped.

"Enriched" means I add four derived columns that the rest of the
pipeline relies on:

    in_twitter, in_google, in_nyt, in_lyrics
        boolean flags derived from the four rank columns. A word is
        "in corpus C" iff its rank column for C is not NaN, which (in
        labMT 1.0 terms) means the word appeared in the top-5000 most
        frequent words of corpus C.

    n_corpora
        how many of the four corpora the word appears in, integer 1–4.
        Every labMT word appears in at least one corpus by construction,
        because the lexicon is the union of the four top-5000 lists.

    valence_band
        categorical bin on happiness_average. I use {"negative",
        "neutral", "positive"} with edges 4 and 6 to match the Δh=1
        neutral filter used elsewhere in the pipeline.

The enrichment lives here, and not in the downstream scripts, because
every downstream script uses the same definitions. Factoring them out
once makes it easier to change the thresholds later.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Data_Set_S1.txt"
PROC_DIR = ROOT / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)
OUT = PROC_DIR / "labmt_clean.csv"


NUMERIC_COLS = [
    "happiness_rank",
    "happiness_average",
    "happiness_standard_deviation",
    "twitter_rank",
    "google_rank",
    "nyt_rank",
    "lyrics_rank",
]

RANK_COLS = ["twitter_rank", "google_rank", "nyt_rank", "lyrics_rank"]
CORPORA = ["twitter", "google", "nyt", "lyrics"]


def load_raw() -> pd.DataFrame:
    if not RAW.exists():
        raise FileNotFoundError(
            f"Expected labMT at {RAW}. Run fetch_data.py first.")
    df = pd.read_csv(
        RAW,
        sep="\t",
        skiprows=3,
        na_values=["--"],
        encoding="utf-8",
    )
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["word"] = df["word"].astype("string").str.strip().str.lower()

    before = len(df)
    df = df.drop_duplicates(subset=["word"]).reset_index(drop=True)
    after = len(df)
    if before != after:
        print(f"[clean] dropped {before - after} duplicated word rows")
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["in_twitter"] = out["twitter_rank"].notna()
    out["in_google"] = out["google_rank"].notna()
    out["in_nyt"] = out["nyt_rank"].notna()
    out["in_lyrics"] = out["lyrics_rank"].notna()
    out["n_corpora"] = (
        out["in_twitter"].astype(int)
        + out["in_google"].astype(int)
        + out["in_nyt"].astype(int)
        + out["in_lyrics"].astype(int)
    )

    def band(h: float) -> str:
        if pd.isna(h):
            return "unknown"
        if h < 4.0:
            return "negative"
        if h > 6.0:
            return "positive"
        return "neutral"

    out["valence_band"] = out["happiness_average"].map(band)
    return out


def summarize(df: pd.DataFrame) -> None:
    print(f"[labmt] rows: {len(df)}")
    print(f"[labmt] happiness_average: mean={df['happiness_average'].mean():.4f}, "
          f"median={df['happiness_average'].median():.4f}, "
          f"min={df['happiness_average'].min():.2f}, "
          f"max={df['happiness_average'].max():.2f}")
    print(f"[labmt] happiness_std: mean={df['happiness_standard_deviation'].mean():.4f}")
    for c in CORPORA:
        flag = f"in_{c}"
        print(f"[labmt] {flag}: {int(df[flag].sum())} words "
              f"({df[flag].mean():.1%})")
    print("[labmt] words appearing in N corpora:")
    print(df["n_corpora"].value_counts().sort_index().to_string())
    print("[labmt] valence band counts:")
    print(df["valence_band"].value_counts().to_string())


def main() -> None:
    df = load_raw()
    df = enrich(df)
    summarize(df)
    df.to_csv(OUT, index=False)
    print(f"[save] {OUT}")


if __name__ == "__main__":
    main()
