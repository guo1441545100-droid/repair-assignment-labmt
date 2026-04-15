# `data/raw/`

Two raw inputs live here.

## 1. `Data_Set_S1.txt` (labMT 1.0 lexicon, instrument)

About 400 KB, tab-separated. This is the supporting-information file for:

> Dodds, P. S., Harris, K. D., Kloumann, I. M., Bliss, C. A., &
> Danforth, C. M. (2011). Temporal Patterns of Happiness and
> Information in a Global Social Network: Hedonometrics and Twitter.
> *PLoS ONE*, 6(12), e26752.
> <https://doi.org/10.1371/journal.pone.0026752>

Not redistributed in this repo because it is a PLoS supporting-information file and the cleanest thing to do is point at the original. To obtain it:

1. Open <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0026752>
2. Scroll to the **Supporting Information** section at the bottom.
3. Download **Data Set S1** (a `.txt` file, about 360 KB).
4. Put it at `data/raw/Data_Set_S1.txt` (rename if your browser adds a suffix).

### File layout (as I read it)

Three metadata lines at the top (skipped in `load_labmt.py` via `skiprows=3`) and then a tab-separated table with these columns:

    word
    happiness_rank
    happiness_average
    happiness_standard_deviation
    twitter_rank
    google_rank
    nyt_rank
    lyrics_rank

Missing rank entries are the literal string `--`, which `load_labmt.py` treats as NaN via `na_values=["--"]`.

## 2. `sotu/*.txt` (State of the Union corpus, 1790-2019)

233 plain-text files, one per address, downloaded automatically by `src/fetch_data.py` from the public GitHub repository `martin-martin/sotu-speeches`, which mirrors the canonical texts. The files are US federal government speech, public domain.

File naming convention, as-is from upstream:

    {president_slug}-{month}_{day}-{year}.txt

For example:

    abraham_lincoln-december_1-1862.txt
    donald_j._trump-february_5-2019.txt

Each file begins with three lines that the upstream project prepends (president name, date, blank line). `src/tokenize_and_score.py` strips that preamble in `strip_preamble()` so the preamble words do not contaminate the labMT score.

### If you are offline

If `src/fetch_data.py` cannot reach GitHub, download the `speeches/` directory from <https://github.com/martin-martin/sotu-speeches> manually and drop every `.txt` into `data/raw/sotu/`. The scorer only cares that the files are in that directory with the expected filename pattern.

## Run order

After both raw inputs are in place:

```bash
python src/fetch_data.py          # verifies labMT + SOTU
python src/run_all.py             # runs the whole pipeline end to end
```

## Citations

Cite Dodds et al. (2011) if you use the lexicon for anything beyond reproducing this repair. The SOTU texts are public domain but credit upstream by linking to the `martin-martin/sotu-speeches` repository if you redistribute them.
