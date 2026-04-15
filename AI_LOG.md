# AI usage log

This is the honest, section-by-section account of what Claude (Anthropic) helped me with during the repair assignment, and what I did myself. The course policy says AI use is allowed if it is disclosed and does not replace my thinking on the research contribution. I have tried to be specific rather than vague. "Used AI to help with coding" is not a disclosure, it is a shrug.

## Overall split

Rough numbers. Roughly **45% of the prose in README.md was drafted or tightened by Claude and then edited by me**, roughly **65% of the Python in `src/` was drafted by Claude from my pseudocode and then debugged together**, and **100% of the research question, the era boundaries, the filter decisions, the robustness design, and the interpretation of the results is mine**.

The moves I will not share credit for are: picking the SOTU corpus as a replacement for the group's IMDb attempt, picking 1860 / 1945 as the era boundaries on humanities grounds, designing Comparison 2 (written vs spoken) as a direct alternative-hypothesis test for C1, and reading the condition-D result in §6 as "part of the Founding–Broadcast gap is a coverage artefact" rather than "the gap is real." Those are the decisions that would get a low grade wrong and a high grade right, and they are the ones I sat with.

## By file

### `README.md`

- §0 (repair framing): mine, first draft. Claude tightened two sentences in a second pass. The three-weak-points paragraph is Claude's rewording of a bullet list I wrote.
- §1 (research question): mine. I tried three phrasings and kept the one that maps onto C1/C2/C3 cleanly.
- §2 (humanities argument): co-written. I gave Claude three bullets ("lexicon has an era bias", "raters did not know the 1808 context", "era boundaries are themselves a claim") and asked for a tight two-paragraph version. I rewrote the last paragraph because the draft felt too tidy.
- §3.1 (provenance): mine, straight transcription of the file metadata and download steps.
- §3.2 (data dictionary): table structure and wording are mine. Claude suggested including `happiness_unweighted` as a column after I forgot to list it.
- §3.3 (descriptive overview): numbers are from my scripts. The "three things to notice" paragraph is mine. The specific phrasing "the single biggest threat to an era comparison" is Claude's, I kept it because it is exactly what I was trying to say.
- §4.1 (tokenisation rationale): the three numbered reasons are mine. Claude tightened the wording of reason 1.
- §4.2 (coverage and OOV): mine, first draft. I rewrote the "I do not treat low-coverage documents as invalid" sentence three times to get the stance right, none of those drafts are Claude's.
- §4.3 (superpopulation framing): Claude wrote the first two sentences, I wrote the rest including the "not the same as sampling presidents" sentence, which is the point I care about.
- §4.4 (what the number does not mean): mine. This paragraph is the reason I believe the rest of the README.
- §5 (results): tables are from my scripts, the commentary is mine. The phrase "Broadcast-era bump" is Claude's, I kept it because it is more vivid than "asymmetric three-way difference." The reading of C2 as ruling out the delivery-mode explanation is mine.
- §6 (robustness): design (the four conditions) and the "what holds / what wobbles / one-sentence version" structure are mine. Claude drafted the narrative paragraphs from my table of numbers and then I reorganised them. The condition-D threshold of 0.18 was chosen by me after I noticed that 0.15 dropped nothing and 0.20 dropped Founding to 7 docs.
- §7 (qualitative exhibits): the anchor exhibit structure was my idea (carried over from the earlier draft of this repair). The era-distinctive computation is Claude's suggestion, I accepted it because it was exactly the panel I needed and writing it from scratch would have cost an hour. The three-paragraph reading of the anchors (especially the "post-9/11 threat vocabulary" observation and the Portuguese/Dutch non-English finding) is mine.
- §8 (six limitations): mine. I wrote this section twice, the version above is the second pass because the first pass read like a defensive shield.
- §9 (trust/refuse/improve): structure is standard, content is mine.
- §10 to §13: boilerplate, checked against what is actually in the repo.

### `src/fetch_data.py`

Mostly mine. I wrote the shape (check labMT exists, download SOTU from a named upstream, skip cached files). Claude proposed the pagination helper and the User-Agent string. Claude also suggested the curl-as-fallback hack after my first run hit the stock macOS Python SSL cert bug, which was a nice catch.

### `src/load_labmt.py`

Unchanged from the earlier labMT-as-research-object version of this repo. Still drafted by Claude from my spec (skip 3 header lines, `--` → NaN, add `in_*` flags, `n_corpora`, `valence_band`). Kept in the pipeline because it still cleans the lexicon before the scoring step.

### `src/tokenize_and_score.py`

This is the most important script in the repair and most of it is mine. I wrote the tokeniser, the preamble stripper, the score_document function, the era / modality / half_century derivation, and the per-era summary output. Claude wrote the filename parser and suggested the `load_labmt_scores` split into `scores` and `filt` (keeping both around so robustness could reuse the unfiltered version without me having to reload the CSV).

### `src/descriptive.py`

Co-written. I wrote the overlay histogram by era, the scatter year vs happiness, and the docs-per-president table. Claude wrote the `summary()` helper, the coverage histogram, and the tokens-per-doc histogram. I picked the era colours manually.

### `src/bootstrap_inference.py`

The math (`boot_diff`, `boot_mean`, `N_BOOT`, the seed convention) is carried over from my earlier labMT-as-object version and was co-written originally. The three comparison functions were rewritten for the SOTU topic by me, with Claude fixing one pandas bug where I had forgotten `.dropna()` on a `happiness_weighted` series that contained a single NaN from an address with zero matches. The `dump_fill_in` helper is Claude's and I accepted it wholesale.

### `src/robustness.py`

I chose the four conditions. Condition D (coverage cut) is the one I care about most because it is the only condition that actually moves one of the C1 results, and that movement is the finding in §6 that I built §7.2 around. Claude drafted the `rescore_with_filter` helper that reuses the tokenisation primitives from `tokenize_and_score.py`, which saved me from duplicating code. The forest plot layout with four offsets per row is Claude's.

### `src/qualitative_exhibit.py`

Co-written. The anchor exhibit (Panel A) is carried over from my earlier labMT-as-object version. The era-distinctive computation (Panel B) was Claude's suggestion: compute per-word freq per 1000 tokens in each era, define `distinct(w, era) = freq(w|era) − max over other eras`, rank within each era. I asked for it because I wanted exactly one table that showed a reader **which words** were driving the C1 effect. The Founding-era results (`united`, `citizens`, `constitution`, `treaty` on the happy side; `debt`, `execution`, `hostile` on the sad side) are, to me, the most persuasive evidence in the whole repair that the numbers are picking up real language shift and not instrument drift.

### `src/run_all.py`

Mine, seven lines of `subprocess.call`.

## Debugging moments I want to flag

- **The stock-Python SSL failure on macOS.** First run of `fetch_data.py` hit `CERTIFICATE_VERIFY_FAILED` because the bundled Python did not have root certs. Claude suggested falling back to `curl` via subprocess when it is available. I accepted the fix and added a short comment in the script so the next person to clone this repo on a fresh Mac knows what they are looking at.
- **Condition D did nothing at first.** My first draft of `robustness.py` used a coverage threshold of 0.15, and condition D dropped zero documents (the minimum coverage in the whole corpus was about 0.156). I noticed the `n=72/84/77` in the output was exactly the baseline and traced it back. I bumped the threshold to 0.18 after checking the per-era distribution. This is the debugging moment I am proudest of because without it I would have reported "robust everywhere" and missed the real finding.
- **Founding-era `last`, `without`, `no`, `late`.** First run of `qualitative_exhibit.py` returned `last` (h = 3.74) and `no` (h = 3.48) as top Founding-era sad-distinctive words. I paused because those are grammatical fillers, not affect words, and almost rewrote the ranking to filter them out. I did not, because that would have been me deciding what counts as "real" affect vocabulary, which is exactly the humanities move I am criticising labMT for in §2. The words stay in the table, flagged implicitly by the reader being able to see their scores.

## What Claude did NOT help with

- The decision to drop the IMDb side from the group project entirely.
- The decision to use the SOTU corpus (and not Gutenberg or Reddit, the other two options I considered).
- The 1860 / 1945 era boundaries and why they are the right two for this research question.
- The three comparisons (C1, C2, C3) and why C2 is the right alternative-hypothesis check for C1.
- The condition-D reading ("part coverage artefact, part real") in §6.
- The six limitations in §8.
- The "trust / refuse / improve" reading in §9.

If someone reading this log thinks those are the parts that matter, I agree.
