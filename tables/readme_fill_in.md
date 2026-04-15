# README fill-in values

Values produced by bootstrap_inference.py. Copy these into
the [[...]] placeholders in README.md §6.

## Comparison 1 — pairwise corpus differences (filtered)
- twitter − google: diff = -0.0654, CI = [-0.1668, +0.0325], mean_a = 5.8095, mean_b = 5.8750, prob>0 = 0.097
- twitter − nyt: diff = -0.0158, CI = [-0.1207, +0.0852], mean_a = 5.8095, mean_b = 5.8253, prob>0 = 0.378
- twitter − lyrics: diff = +0.3371, CI = [+0.2294, +0.4457], mean_a = 5.8095, mean_b = 5.4724, prob>0 = 1.000
- google − nyt: diff = +0.0497, CI = [-0.0501, +0.1500], mean_a = 5.8750, mean_b = 5.8253, prob>0 = 0.837
- google − lyrics: diff = +0.4025, CI = [+0.2970, +0.5042], mean_a = 5.8750, mean_b = 5.4724, prob>0 = 1.000
- nyt − lyrics: diff = +0.3529, CI = [+0.2458, +0.4621], mean_a = 5.8253, mean_b = 5.4724, prob>0 = 1.000

## Comparison 2 — top-1000 minus bottom-1000 per corpus (filtered)
- twitter: diff = +0.5819, CI = [+0.3553, +0.8101], n_top = 467, n_bot = 341
- google: diff = +0.4255, CI = [+0.2088, +0.6408], n_top = 317, n_bot = 386
- nyt: diff = +0.4584, CI = [+0.2407, +0.6840], n_top = 334, n_bot = 371
- lyrics: diff = +0.3783, CI = [+0.1389, +0.6245], n_top = 442, n_bot = 366

## Comparison 3 — mean happiness by n_corpora (filtered)
- n_corpora = 1: mean = 5.4179, CI = [5.3327, 5.5021], n_words = 1462
- n_corpora = 2: mean = 5.5381, CI = [5.4179, 5.6563], n_words = 831
- n_corpora = 3: mean = 5.8222, CI = [5.6715, 5.9696], n_words = 482
- n_corpora = 4: mean = 5.9601, CI = [5.8500, 6.0680], n_words = 807
