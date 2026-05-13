# AI usage log

This is an honest account of how I used Claude (Anthropic) during the repair
assignment, and what I did myself. The course policy permits AI use as long as
it is disclosed and does not substitute for my own thinking on the research
contribution. I have tried to be specific rather than vague: "used AI to help
with coding" is not a real disclosure.

## Summary

Claude was used as a support tool, not as a co-author of the research. I used
it for:

- debugging Python and pandas issues (e.g. a missing `.dropna()`, the macOS stock-Python SSL cert problem)
- improving code structure and removing small duplications
- checking that the README sections were ordered in a way a marker could follow
- tightening wording on sentences I had already drafted
- explaining error messages and unfamiliar library behaviour

The intellectual decisions in this repair are mine. In particular:

- choosing the SOTU corpus instead of the original group-project IMDb corpus
- formulating the research question and mapping it onto C1, C2 and C3
- choosing 1860 and 1945 as the historical era boundaries on humanities grounds
- designing the three comparisons, including C2 (written vs spoken) as a direct alternative-hypothesis check on C1
- interpreting the coverage / OOV issue and the condition-D result in §6 as "part of the Founding–Broadcast gap is a coverage artefact, part is probably real" rather than collapsing it either way
- deciding the limits of what the numbers can support, including the six limitations in §8

These are the decisions a marker should grade me on, and they are the ones I sat with rather than handed off.

## By file

### README.md

- **§0 (repair framing):** drafted by me. Claude tightened two sentences on a second pass. The three-weak-points paragraph is Claude's rewording of a bullet list I wrote.
- **§1 (research question):** mine. I tried three phrasings before settling on the one that maps cleanly onto C1/C2/C3.
- **§2 (humanities argument):** I gave Claude three bullets ("lexicon has an era bias", "raters did not know the 1808 context", "era boundaries are themselves a claim") and asked for a tight two-paragraph version. I rewrote the last paragraph because the draft felt too neat.
- **§3.1 (provenance):** mine, transcribed from file metadata and download steps.
- **§3.2 (data dictionary):** table structure and wording are mine. Claude noticed I had forgotten to list `happiness_unweighted` as a column.
- **§3.3 (descriptive overview):** numbers come from my scripts; the "three things to notice" paragraph is mine. One phrase ("the single biggest threat to an era comparison") is Claude's wording of a point I had already made.
- **§4.1 (tokenisation rationale):** the three numbered reasons are mine; Claude tightened reason 1.
- **§4.2 (coverage and OOV):** mine. I rewrote the "I do not treat low-coverage documents as invalid" sentence several times to get the stance right.
- **§4.3 (superpopulation framing):** Claude wrote the first two sentences; I wrote the rest, including the "not the same as sampling presidents" sentence, which is the point I care about.
- **§4.4 (what the number does not mean):** mine. This paragraph is the reason I trust the rest of the README.
- **§5 (results):** tables from my scripts; commentary mine. The phrase "Broadcast-era bump" is Claude's and I kept it because it is more vivid than my own version. The reading of C2 as ruling out the delivery-mode explanation is mine.
- **§6 (robustness):** the four conditions and the "what holds / what wobbles / one-sentence version" structure are mine. Claude drafted narrative paragraphs from my table of numbers, which I then reorganised. The condition-D threshold of 0.18 was chosen by me after checking what 0.15 and 0.20 did to the per-era counts.
- **§7 (qualitative exhibits):** the anchor exhibit structure is mine, carried over from an earlier draft. The era-distinctive computation in Panel B was Claude's suggestion; I accepted it because it was the panel I needed. The three-paragraph reading (including the post-9/11 vocabulary observation and the Portuguese/Dutch non-English finding) is mine.
- **§8 (six limitations):** mine. I wrote this section twice; the first pass read too much like a defensive shield.
- **§9 (trust / refuse / improve):** structure is standard; content is mine.
- **§10–§13:** boilerplate, checked against what is actually in the repo.

### src/fetch_data.py

Mostly mine: the overall shape (check labMT exists, download SOTU from a named upstream, skip cached files). Claude proposed the pagination helper and the User-Agent string, and suggested the curl fallback after my first run hit the macOS stock-Python SSL cert bug.

### src/load_labmt.py

Unchanged from the earlier labMT-as-research-object version of the repo. Originally drafted by Claude from my spec (skip three header lines, `--` → NaN, add `in_*` flags, `n_corpora`, `valence_band`). Kept in the pipeline because it still cleans the lexicon before scoring.

### src/tokenize_and_score.py

The most important script in the repair and most of it is mine: the tokeniser, the preamble stripper, the `score_document` function, the era / modality / half-century derivation, and the per-era summary output. Claude wrote the filename parser and suggested splitting `load_labmt_scores` into `scores` and `filt` so robustness could reuse the unfiltered version without reloading the CSV.

### src/descriptive.py

Co-written. I wrote the overlay histogram by era, the year-vs-happiness scatter, and the docs-per-president table, and chose the era colours manually. Claude wrote the `summary()` helper, the coverage histogram, and the tokens-per-doc histogram.

### src/bootstrap_inference.py

The math (`boot_diff`, `boot_mean`, `N_BOOT`, the seed convention) carries over from the earlier labMT-as-object version and was co-written then. The three comparison functions were rewritten for the SOTU topic by me; Claude fixed one pandas bug where I had forgotten `.dropna()` on a `happiness_weighted` series that contained a single NaN. The `dump_fill_in` helper is Claude's, and I accepted it as-is.

### src/robustness.py

I chose the four conditions. Condition D (coverage cut) is the one I care about most because it is the only condition that moves a C1 result, and that movement is the finding §6 and §7.2 are built around. Claude drafted the `rescore_with_filter` helper that reuses the tokenisation primitives from `tokenize_and_score.py`. The four-offsets-per-row forest-plot layout is Claude's.

### src/qualitative_exhibit.py

Co-written. The anchor exhibit (Panel A) carries over from the earlier labMT-as-object version. The era-distinctive computation in Panel B was Claude's suggestion (per-word frequency per 1000 tokens by era, distinct(w, era) = freq(w|era) − max over other eras, ranked within each era). I asked for it because I wanted one table that showed which words were driving the C1 effect. The Founding-era results (united, citizens, constitution, treaty on the happy side; debt, execution, hostile on the sad side) are the most persuasive evidence in the repair that the gap reflects real language change rather than instrument drift, and that reading is mine.

### src/run_all.py

Mine. Seven lines of `subprocess.call`.

## Debugging moments worth flagging

- **macOS stock-Python SSL failure.** First run of `fetch_data.py` hit `CERTIFICATE_VERIFY_FAILED` because the bundled Python lacked root certs. Claude suggested falling back to `curl` via subprocess. I added a short comment in the script so anyone cloning the repo on a fresh Mac knows what they are looking at.
- **Condition D did nothing at first.** My initial threshold of 0.15 dropped zero documents (the minimum coverage in the corpus was about 0.156). I noticed the n=72/84/77 in the output matched the baseline and traced the issue back. After checking the per-era distribution I moved the threshold to 0.18. This is the debugging moment I am proudest of: without it I would have reported "robust everywhere" and missed the real finding.
- **Founding-era `last`, `without`, `no`, `late`.** The first run of `qualitative_exhibit.py` returned `last` (h ≈ 3.74) and `no` (h ≈ 3.48) as top Founding-era sad-distinctive words. I almost filtered them out as grammatical fillers, but didn't, because that would have been me deciding what counts as "real" affect vocabulary — exactly the humanities move I criticise labMT for in §2. The words stay in the table.

## What Claude did NOT help with

- The decision to drop the IMDb side of the original group project.
- The decision to use the SOTU corpus rather than Gutenberg or Reddit.
- The 1860 / 1945 era boundaries and why they are the right ones for this research question.
- The three comparisons (C1, C2, C3) and the role of C2 as an alternative-hypothesis check on C1.
- The condition-D reading ("part coverage artefact, part real") in §6.
- The six limitations in §8.
- The "trust / refuse / improve" reading in §9.

If a reader of this log thinks those are the parts that matter, I agree.

## How I verified the AI-assisted work

I did not take Claude's output on trust. After every round of AI-assisted edits I checked the work in concrete ways:

- I reran the scripts end-to-end with `run_all.py` and confirmed they produced the expected CSVs and figures without error.
- I opened the generated CSVs (per-era summaries, bootstrap outputs, robustness conditions, era-distinctive tables) and spot-checked counts and means against numbers quoted in the README.
- I compared every claim in the README against the actual outputs in `results/` and `figures/`. Where the draft text overstated or misdescribed a result, I rewrote it.
- For AI-suggested code, I read it line by line before committing and removed or rewrote anything I could not explain to a marker.
- A few Claude suggestions were rejected because they did not match the evidence: an early proposed phrasing that called the Broadcast effect "clearly real" was cut, and a suggested filter on grammatical fillers in the qualitative exhibit was rejected for the reason given above.

The pipeline as it stands is one I can run, defend, and explain.

