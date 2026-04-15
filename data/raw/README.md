# `data/raw/`

This directory holds exactly one file:

    Data_Set_S1.txt    (labMT 1.0 lexicon, ~400 KB, tab-separated)

It is the supporting-information file for:

> Dodds, P. S., Harris, K. D., Kloumann, I. M., Bliss, C. A., &
> Danforth, C. M. (2011). Temporal Patterns of Happiness and
> Information in a Global Social Network: Hedonometrics and Twitter.
> *PLoS ONE*, 6(12), e26752.
> <https://doi.org/10.1371/journal.pone.0026752>

I am not redistributing it inside this repo because it is a PLoS
supporting-information file and the cleanest thing to do is point at
the original. To obtain it:

1. Open <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0026752>
2. Scroll to the **Supporting Information** section at the bottom.
3. Download **Data Set S1** (a `.txt` file, about 360 KB).
4. Put it at `data/raw/Data_Set_S1.txt` (rename if your browser adds
   a suffix).

After the file is in place, run `python src/fetch_data.py` to
confirm the check passes, then `python src/run_all.py` to run the
whole pipeline.

## File layout (as I read it)

The file has three metadata lines at the top (skipped in
`load_labmt.py` via `skiprows=3`) and then a tab-separated table with
these columns:

    word
    happiness_rank
    happiness_average
    happiness_standard_deviation
    twitter_rank
    google_rank
    nyt_rank
    lyrics_rank

Missing rank entries are the literal string `--`, which `load_labmt.py`
treats as NaN via `na_values=["--"]`.

## Citation

Please cite Dodds et al. (2011) — see the full reference above — if
you use this file for anything beyond reproducing the repair
assignment.
