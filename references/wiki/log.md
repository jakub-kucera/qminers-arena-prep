# Log

Append-only. One entry per ingest, query, lint, search or restructure. Format: `## [YYYY-MM-DD] kind | title`, then a few lines. `grep "^## \[" references/wiki/log.md | tail -5` shows the latest.

## [2026-10-10] search | first search for sources
Found and cloned the Prosperity 2–4 write-ups, UChicago, AlgoTrade, the Qminers 2025 repo and hftbacktest; read the Arena site's JavaScript bundle. Details and dead ends in `references/SEARCH_LOG.md`.

## [2026-10-10] search | books, articles and papers
Added eight free papers to `literature_raw/`, read Rigtorp and Databento on queue position, bought no books. See `references/SEARCH_LOG.md`.

## [2026-10-10] ingest | all 16 clones into a single `MAP.md`
First field guide, written from the strategy code of each repo. Checked by running Frankfurt's file through our engine (it never trades baskets or options), by grep (DU's `round4.py` reads no counterparty names; DTU's drawdown halt is unused), and by data (P4 empty-side share, days per round, names only in round 4). Found and fixed several of my own unchecked claims (licence of DTU, names in Prosperity 2 data, a made-up note about imports).

## [2026-10-10] restructure | `MAP.md` becomes this wiki
Rebuilt in the LLM-wiki pattern: schema, index, log, 16 source pages, 17 concept pages, a contradictions page, an overview, and `lint.py`. Citations now use `path:line` so they can be checked mechanically. `MAP.md` was removed; its content lives in the source and concept pages.

## [2026-10-10] lint | first run and a manual review of every citation
`lint.py`: 35 pages, 557 citations, 0 errors and 0 warnings after fixes (it also failed correctly on a deliberately bad page and a bad log entry). The lint only proves that a cited line exists and is not blank, so every citation was also read next to the claim it supports. That found about 20 wrong line numbers (for example in `docs/journey.md`, Alpha Animals' README, Qminers' `validate.py`, the log converter, Linear Utility's README) and one wrong statement (names in trade files: Prosperity 2's data has name-bearing `*_wn.csv` files for rounds 1, 3 and 4). All fixed. Not checked: whether each *paraphrase* is faithful beyond that one-line comparison.

## [2026-10-11] ingest | Negative Eevee, the Prosperity wikis, and four repos read online
Cloned `alexbolfa/algotrade-negative-eevee` (found through the HTML of a LinkedIn short link) and `HumzahM/UTC2025-Case2-Writeup`. Downloaded the Prosperity 2, 3 and 4 wikis from Notion with the new `references/fetch_notion.py` (72 pages; fixed three crawler bugs on the way: page-name collisions, synced blocks, anchor links). Saved README snapshots of Leo-Hawking, heyman7913, CMU Physics and two Kayzerjali files under `references/online-snapshots/`. Nine new source pages, a new concept page (`probing-the-environment`), new evidence on eleven concept pages, two new rows in `contradictions.md`. Facts that replaced inferences: IMC's official library list, the 900 ms limit, 1,000 versus 10,000 iterations.

## [2026-10-11] ingest | Diehm's essay and Cartea, Donnelly & Jaimungal (2018)
The user downloaded both PDFs into `literature_raw/`; converted with `literature_md/convert.sh` (`order-book-signals/`, `how-to-almost-win/`; decorative images removed from the latter). The imbalance definition `ρ` was checked against the PDF; the rest of the paper's formulas were not. Quant.SE is blocked for the fetch tool; Hummingbot and Optiver were read as page-fetch summaries (`sources/online-articles.md`).

## [2026-10-12] restructure | the literature joins this wiki
`literature_md/` gets its pages here rather than in a second wiki: the fit analysis is at the top of the new Literature section of `index.md`. `SCHEMA.md` adds literature source pages (Main results, Assumptions against the Arena, In our notation), rule 9 (a citation into `literature_md/` carries its one-based PDF page, and a formula says `checked` or `unchecked`) and an ingest workflow for documents. New `literature_md/pdfpage.py` finds the PDF page of a markdown line: only 9 of 19 documents have Marker's page anchors, so it also bounds the page by figure names and the headings' pages in `meta.json`, then matches words against `pdftotext` (tried on six documents, including Theorem 3.1 of `pseudo-math` on p. 11, confirmed by `pdftotext`). `lint.py` now warns on a literature citation without `(p. N)` and fails when N disagrees with the markers (it catches the zero-based slip: p. 4 cited for a line on p. 5). The 12 existing literature citations got their pages; only `ρ` (Cartea et al. 2018, p. 5) is marked checked.

## [2026-10-12] ingest | literature phase 1: thirteen papers
Source pages for the papers that feed open `TODO.md` items:
- fair value and quoting: Stoikov, Gould & Bonart, Cartea et al. 2018, Cont et al., Avellaneda–Stoikov, GLFT, Guéant 2017;
- validation: the three Bailey et al. papers;
- queue position: Moallemi & Yuan, Huang et al., Guo et al.

New concept pages `book-imbalance-and-micro-price` and `optimal-quoting-models`. Theory added to `validation-and-overfitting` (with the decision that a CSCV PBO for `arena.grid` is worth building), `queue-position-and-fills`, `market-making-and-inventory-skew`, `many-products-architecture` and `fair-value-and-wall-mid`. Rows 1 and 11 of `contradictions.md` got the theory's explanation.

Every kept formula was read on the PDF page image, except those marked `unchecked` (9). Worked numbers were recomputed where the papers give them: the DSR example, `E[max_N]` for N = 10, the A–S spread of 1.29.

OCR traps found, all recorded on the source pages:
- minus signs dropped from Cartea et al.'s Sharpe tables, which turns a uniformly losing table into a partly winning one;
- the square root misplaced in every GLFT and Guéant closed form, and Guéant's exponent `k/(ξΔ+1)` for `k/(ξΔ)+1`;
- `P^A` for `P^B` in Cont et al.'s `e_n`;
- decimal points dropped from Gould & Bonart's tables;
- nearly all inline math lost in the DSR paper;
- typos in the papers themselves: Stoikov's spread with `+`, pseudo-math eq. (6.3), PBO's 12,780 for C(16, 8) = 12,870, Moallemi & Yuan's jump sign.

Our A–S copy is the 2006 preprint, without the `γσ²(T−t)` spread term Hummingbot uses. `lint.py` and `pdfpage.py` now split lines on `\n` only: `splitlines()` also splits on form feeds, which Guo et al.'s markdown contains, and shifted its line numbers against grep's.

## [2026-10-12] restructure | the literature workflow and findings written down
`SCHEMA.md` replaces the short literature-ingest steps with "Add a document to the literature": get it in, triage (a paper is read whole; a book gets a chapter map and only the chapters a question needs), read and check (page images, tables from the PDF, recomputed examples, OCR checklist), write, close. It is the procedure Phase 1 followed, for future books. `literature_md/README.md` lists the OCR failure modes seen so far. `overview.md` has a new section, "What the literature adds", with the eight findings that change what we do. `MANUAL_TODO.md` (books) and the `TODO.md` plan point to the workflow.

## [2026-10-12] ingest | literature phase 2: the two books
Source pages with full chapter maps (PDF pages and markdown lines) for Cartea, Jaimungal & Penalva and for Harris.
- **Read:** Cartea et al. ch. 2 (Grossman–Miller, Kyle, Glosten–Milgrom), 10 (market making), 11 (pairs trading), 12 (order imbalance); Harris ch. 10–14 and 17. The rest is `mapped`.
- **Checked against page images:** Glosten–Milgrom, (10.8)–(10.11), (10.19)–(10.27), (11.1)–(11.2) with `F±`, (12.1), Tables 12.1 and the ch. 11 trigger table. The trigger table was **recomputed** from (11.2) with a standard-library integral (1.746, 1.4367).
- **Found:** Kyle's λ printed inverted in Cartea et al. (`2σ_u/σ`; the book's own derivation gives `σ/(2σ_u)`). OCR garbled the `F±` integrals and put `z` inside the exponent of (10.29).

Filed into `informed-counterparties` (Glosten–Milgrom, Harris's inventory–price test), `shared-market-and-adversaries` (quote matching and its trap, the timing option, bluff-proof pricing, Grossman–Miller competition), `baskets-and-fixed-sums` (pure against speculative arbitrage, optimal bands), `market-making-and-inventory-skew`, `optimal-quoting-models` and `book-imbalance-and-micro-price`. Three new findings in `overview.md`. A new `TODO.md` item: adversarial `--vs` rivals (trapper, sniper).

## [2026-10-12] ingest | literature phase 3: Kelly, the LOB survey, Bouchaud et al., price impact
Source pages for the last three documents:
- **Thorp on Kelly.** The PDF is a scan with no text layer, so `pdfpage.py` now reports that and interpolates a page between Marker's markers; every page cited was confirmed on the page image, and about a third of the interpolations were one page off. All kept formulas are checked: `f* = p − q`, `(bp − q)/b`, `m/(ab)`, (3.2), (7.3)–(7.6), `c(2 − c)`, (7.13), (8.2). OCR slip: `f*_e` rendered as `f_*^*` in the fractional-Kelly lesson.
- **Gould et al., "Limit order books".** Read whole; no formulas used. The OCR (and the PDF's own text layer) print Φ as `+` and Ω as `0`; the paper itself drops a `∝` in the Gabaix result.
- **Bouchaud et al.** Our copy is a 47-page excerpt (preface, ch. 1, ch. 2 to 2.1.4); the impact and market-making chapters are not in it. Checked: (1.9), `s/2 − R∞`, (1.10)–(1.11), (2.9), (2.10), (2.12), (2.13). OCR slip: `e^{−τ/η_t}` for `e^{−τ/τ_η}` in (2.12).

New concept page `price-impact`. A sizing section in `risk-and-protecting-a-lead` (Kelly's edge-over-variance scaling and fractional use carry over; its log-growth objective doesn't). The signature plot in `fair-value-and-wall-mid`; priority rules and tick size in `queue-position-and-fills`.

Measured on Prosperity data with throwaway scripts (not in the repo), recorded on the pages:
- market trades at tick `t` print at book `t`'s prices (96–97%), so book `t` is their arrival book;
- against the wall mid, the signed move after market trades is near zero in P2 round 1 and P3 rounds 1–2 except the baskets; against the mid it looks like a lasting 0.3–1.4 tick impact, which is selection;
- Kelp's mid varies 28 times more per tick at lag 1 than at lag 200, its wall mid 3 times;
- lag-1 autocorrelation of mid changes −0.48 (Kelp), −0.50 (Resin), −0.17 (Squid Ink).

New items: `TODO_DONE.md` "Markouts and fill edge against the wall mid"; `ON_THE_DAY.md` "Do our own trades move the market?" with probe 17. Overview findings 12–14.

## [2026-10-12] lint | literature phase 4: formula statuses, exact pages, theory against practice
- **Formula statuses.** A scan for formulas next to literature citations without `checked` or `unchecked` found 44 lines: 17 were `Traps` lines quoting OCR slips, about 11 were bare symbols or numbers, and 16 were real formulas. 15 of those were read on the page image and marked `checked`: Grossman–Miller, the static depth `1/κ`, Kyle's `x*` and `S`, (10.13) and (10.17) in Cartea et al.; DSR eq. (1); Avellaneda–Stoikov's intensities (2.8); Huang et al.'s Model I; Bouchaud's (2.1); Kelly's `g(f)` and uncorrelated case; Gould et al.'s `|ω|^α`; Guéant's `Σ_j Γ^{ij} q^j`. Cartea et al.'s (11.16) is marked `unchecked`. `lint.py` now warns on such a line (Traps exempt) and errors on an `unchecked` formula under "What it means for our code".
- **Exact pages.** `lint.py --pages` matches each literature citation's first and last line against the PDF text (about 5 s). It found 10 wrong pages, all fixed: mostly ranges whose last line runs onto the next page, plus Cont et al.'s R² line (p. 3, not 2), Gould et al.'s eq. (11) (p. 10, not 9) and the DSR `N̂` formula (p. 14, not 15). Two warnings were the matcher's mistakes, confirmed in the PDF text and listed in `MATCH_MISSES`: a table header shared by Gould & Bonart's Tables 4 and 5, and a short caption in Gould et al. whose context widened into a footnote on the previous page. Scoring on word pairs instead of single words was tried and dropped: it changed 3 of 457 lines and fixed none of these.
- **Claims against lines.** A seeded random sample of 40 of the 411 literature citations, each read against its cited lines: all 40 support their claims.
- **Theory against practice.** Rows 12–16 in `contradictions.md`: quoting at the touch (Cartea et al. 2018 against Prosperity's market makers), whether trades carry information (`R∞` against the wall-mid measurement), how much of the limit to use (Kelly against full-room quoting), reused hold-out days (Bailey et al. against the teams' held-out-day rules), and quote matching (Harris against the template). Theory notes on rows 2 (the signature plot as a criterion) and 10 (Poisson queues overestimate fills). Each row is linked from its concept pages.
- `SCHEMA.md`'s lint workflow now runs `--pages` and the citation sample.

## [2026-10-12] ingest | Prosperity 4 data loadable as `--data p4`
All P4 position limits now cite IMC's round pages (Emeralds and Tomatoes 80, previously unknown). Found while loading: P4's price files give an empty book `mid_price` 0.0 (203 rows), which marked a held position at zero for a tick and showed a 1.6 million drawdown; the loader now treats it as no price. Recorded on `submission-and-scoring-mechanics` and the P4 backtester page. First template results on P4 rounds 1–2 are in `IDEAS.md`, the new register of tested and untested ideas, whose results count as priors for the Arena.

## [2026-10-12] restructure | wall-mid measurements built into `arena.analysis`
The impact and markout measurements behind the price-impact page are now tooling, not throwaway scripts: the timeline CSV carries the book's wall mid, a `_trades.csv` carries the data's market trades, and `arena.analysis` gains a `reference` option (mark or wall mid), `pnl_split` and `trade_impact`. `trade_impact` reproduces the page's P3 round 1 rows exactly. The split's first result, Resin's takes losing 6,048 against the mark but earning 6,272 against the wall mid on one day, is on the price-impact page and in `IDEAS.md`. The lag-1 autocorrelation and signature-plot numbers are still from scripts outside the repo.

## [2026-10-13] lint | P4 traders cross-checked in our engine and in `prosperity4btest`
Baguette Fromage's `Phase1.py`, DTU's round 1 and round 2 traders and DU's `round2.py`, on P4 rounds 1–2: identical PnL per product per day in both engines, 24 trader-days, including DTU's round 2 trader whose Osmium orders are cancelled for possible limit breaches on 124–347 ticks a day (both engines cancel before matching; the P4 runner's fill clamp only acts on top). Against the teams' claims: DTU's round 1 trader is within 4% of its live +67,585, its round 2 trader 12–16% above its live +84,889; Baguette Fromage's Osmium total is consistent with its 18.6k-a-day estimate; DU gives ranks only. Recorded on the three team pages and the backtester page, which now also says the CLI needs the `cli` subcommand and that its drawdown includes the empty-book zero mids. The Pepper Root result (the drift pays a held long about 80k a day) is in `IDEAS.md`.

## [2026-10-13] restructure | which literature copies are incomplete
Checked every PDF in `literature_raw/` for completeness (page counts against the published versions, front and back matter, and the exhibits of the DSR paper, which are all at its end). Only Bouchaud et al. is incomplete: a 47-page excerpt of a book of about 460 pages. Four documents are complete but not the final version: Harris (2003 draft), Avellaneda–Stoikov (2006 preprint), Cont et al. (2011 working paper), Cartea et al. 2018 (accepted manuscript); the full book and the final versions are now in `MANUAL_TODO.md`. `SCHEMA.md` gains "Replace a document with a fuller copy": the wiki is rebuilt from the new copy, with every citation re-pointed and `lint.py --pages` clean.

## [2026-10-13] query | the template against the published P4 traders, and a target position
Ran the teams' later traders (DTU rounds 3–5, Baguette Fromage's `Phase2_Options.py` and `Phase2_Final.py`, DU's `round4.py` and `round5.py`) and a plain wall-mid market maker on P4 rounds 3–5 in our engine; the comparison by product is in `IDEAS.md`, "Benchmark". The gaps, largest first: options, fading round-number jumps (the Robots), the round 3–4 spot products. On most round 5 families plain market making is level with the teams. DTU's backtests on its development days are far from its live results (round 3: 135,842 over 3 days against +3,686 live), recorded on its page. Found on the way: P4 rounds 3 and 4 share days 1 and 2 (`submission-and-scoring-mechanics`). The template gained a `target` position; holding Pepper Root long (target 80, skew 20) brings it from −25k–58k to 76–78k a day, which partly settles contradictions row 7 and is on the drift page.

## [2026-10-13] restructure | Bouchaud et al.: the full book replaces the excerpt
The full *Trades, Quotes and Prices* (463 PDF pages) was converted with Marker (12 minutes, 8,698 lines after removing 16 decorative images) and the source page rebuilt from it, following "Replace a document with a fuller copy": a chapter map with PDF pages and lines for all 22 chapters and the appendix; chapters 1, 7, 11, 15, 16, 17 and 21 read closely, the rest through their take-home messages and key sections; 25 formulas checked on the page images, 9 marked unchecked. Every earlier citation was re-pointed (ch. 1–2 lines moved down by 9, pages up by 1); `lint.py --pages` is clean. OCR slips recorded: (1.11), (2.12), (11.11), (16.22), (17.4), (21.18). The book's Kyle derivation confirms that Cartea et al. print λ inverted.

Measured with it (P3 round 1): the book's break-even margins for market making are 0.3–0.5 of the spread, and trade signs barely persist (`C(1)` about 0.1 against 0.37–0.93 on NASDAQ), so Prosperity is the book's zero-intelligence case where market making is easy. Filed into `market-making-and-inventory-skew` (break-even, mean reversion, size skew), `price-impact` (response function, square-root domain, phantom orders, Kyle), `queue-position-and-fills` (value of priority), `book-imbalance-and-micro-price` (the race between queues), `fair-value-and-wall-mid` (flat signature plots), contradictions rows 12–13, overview finding 15 and `IDEAS.md`. Template line citations across the wiki were re-pointed after the `target` change moved them.

## [2026-10-13] lint | the measured market-making margins, recomputed with `arena.diagnose`
`arena.diagnose` now computes the Bouchaud et al. break-even margins from a data download. Writing it showed that the wall-mid rows of the table on [Bouchaud et al.](sources/trades-quotes-prices.md) mixed two references: the book's `s/2` (the taker's cost against the mid) with the wall mid's `R`. Measured in one reference, the taker's cost against the wall mid is 0.93 for Kelp, not 1.16, and the slow margin is 0.94 against both references (it was 1.17 against the wall mid). The table now uses the measured cost `−edge`, which equals `s/2` against the mid when trades are at the touch. The range moves from 0.3–0.5 to 0.2–0.4 of the spread: updated in the overview (finding 15), `market-making-and-inventory-skew` and `IDEAS.md`. The conclusion stands: market making pays easily on Prosperity data. `arena.diagnose` also reproduces the lag-1 autocorrelations on [Gould et al.](sources/limit-order-books.md).

## [2026-10-13] query | reading the data on day one
New concept page [reading-the-data-on-day-one](concepts/reading-the-data-on-day-one.md), replacing gap 7 of the index.
- **The page:** a decision table from each of `arena.diagnose`'s notes to a strategy choice. Every row cites the evidence (literature or team) and an example, from the tool's output on P2 round 1, P3 round 1 and P4 rounds 1–5.
- **A new column:** writing the table showed that the tool missed slow reversion to a level. Velvetfruit and Hydrogel have signatures of 1.1 at lag 50, yet their variance per tick halves by lag 1,000. A `slow rev` column (the wall mid at lag 50 against 1,000) now catches them, along with Osmium.
- **Its threshold:** 1.8 is calibrated on a simulated random walk (median 1.11, 2% above 1.8) and on P4 round 5's 50 products (0.76–1.64).
- **Other changes:**
  - `ON_THE_DAY.md` gains the first-hour item "What kind of market is each product?";
  - `probing-the-environment` links to the page;
  - index gaps 2, 4 and 5 were stale (P4 cross-check done, Bouchaud et al. now the full copy) and are updated.

## [2026-10-13] query | the template against the teams' P4 bots in one market
Ran the template in one market with DU's `round2.py`, Baguette Fromage's `Phase1.py` and DTU's round 2 trader, one at a time and all together, on P4 rounds 1–2. In `--resting` the teams' bots were wrapped to cancel their orders every tick, since they freeze otherwise.
- **With orders that live one tick:** Osmium's spread is a fixed pie the bots split, and the template keeps the smallest share.
- **With resting orders:** the template loses up to 445k on Osmium in a round. Rivals' large orders far from fair become the "largest level" and drag its `wall_mid`. Checked on the book the template saw: its fair was 5+ off on 36% of ticks against Baguette Fromage.
- **Filed into:**
  - `shared-market-and-adversaries` (sources, code, how to test);
  - `IDEAS.md` (a new row with the numbers);
  - `ON_THE_DAY.md` ("Is `wall_mid` still the market maker's price?").

  It also raises the stakes for the wall-mid comparison in `TODO.md`.

## [2026-10-13] query | size skew (Bouchaud et al. eq. 17.4) tested
The template gains `size_skew`: inventory control through quote size, as in eq. 17.4.
- **Result:** gridded against `skew` on P3 round 1 (Kelp, Resin, also under `--resting`) and P4 rounds 1–2 (Osmium, Pepper Root), it never beat 0. Price `skew` cost more. Both fit the diagnosis that Prosperity's flow is uninformed. Recorded in `IDEAS.md` and `market-making-and-inventory-skew`.
- **Citations moved:** the new `DEFAULTS` line and `make` docstring shifted `python/bots/template.py`. Its citations in 19 wiki pages were re-mapped with a diff of the old and new file (`make` is now `python/bots/template.py:217-249`).

## [2026-10-13] query | the wall-mid definitions compared
Settled contradictions row 2 for Prosperity data and closed the `TODO.md` item.
- **Method:** four definitions, each run in a copy of the template: the largest level (ours), the outermost (Frankfurt), DTU's rule, and the first level from the top with at least 15 (Baguette Fromage round 5, Linear Utility). Compared on Starfruit, Kelp, Osmium and Pepper Root, in all three engine modes, by signature-plot noise, and against the teams' P4 bots under `--resting`.
- **On its own:** the outermost level ties or wins on every worst day, by 0–1.3%.
- **With rivals' resting orders:** only `sized_mid` survives (+39k on Osmium where the others lose 377–654k), because a rival's far order becomes the largest and the outermost level.
- **The template** gains `outer_mid` and `sized_mid` (with `wall_size`). The Prosperity products keep `wall_mid`.
- **Filed into:**
  - the wiki: `fair-value-and-wall-mid` (a per-day table), `shared-market-and-adversaries`, `reading-the-data-on-day-one`, contradictions row 2;
  - the repo: `IDEAS.md`, `ON_THE_DAY.md`, `README.md`, `CLAUDE.md`.
- **Citations moved:** template line citations re-mapped again (`make` is now `python/bots/template.py:217-249`).

## [2026-10-13] query | P4 levels and vouchers measured
Measured what the teams' P4 round 3–4 money is made of, with two committed scripts (`python/experiments/p4_levels.py`, `python/experiments/p4_vouchers.py`) on the four distinct days.
- **Levels:** Hydrogel's and Velvetfruit's daily means agree within 13 and 16 across days. Replacing Baguette Fromage's and DU's hard-coded levels with the other days' mean keeps 90% of their PnL; the day's running mean keeps 55–57%.
- **Vouchers:** implied vol is flat within each day, each voucher sits within about half a spread of Black–Scholes at one vol, and the teams' voucher PnL is delta × Velvetfruit's move. Contradictions row 6 settled for P4; the options page's link to it said row 5 and is fixed.
- **Filed into:** `drift-and-regime-change`, `options-and-vouchers`, `reading-the-data-on-day-one`, contradictions row 6; the repo's `IDEAS.md` (two tested rows; the untested spot-level row removed, the options row narrowed to smile trading on P3).

## [2026-10-13] query | a level mode in the template
`python/bots/template.py` gains `level_target` and `estimate_level`: for a product that returns to a level, the target is the full limit against a move of `level_band`, held until the other band. The level is a number from earlier days, the day's running mean (`"day"`), or a blend (`level_weight`).
- **Result** (`python/experiments/p4_level_template.py`, nested leave-one-day-out on P4 rounds 3–4): 215k over four days on Hydrogel and Velvetfruit, against 286k in-sample and 147k with the day's own mean. Blending did not help.
- **Filed into:** `drift-and-regime-change` ("What it means for our code"), `reading-the-data-on-day-one` (the reverts-to-a-level row); the repo's `IDEAS.md`, `README.md`, `CLAUDE.md`, `ON_THE_DAY.md`, `TODO.md`.

## [2026-10-13] query | options follow their underlying in the template
`python/bots/template.py` gains a cross-product hook and a mode for options. `Trader.run` trades followed products first and passes their plans. A product with `follow` and `strike` holds the underlying's target as a share of its own limit (`follow_target`). Black–Scholes is in total variance, so delta comes from the option's own price without an expiry date.
- **Result** (`python/experiments/p4_vouchers_template.py`, nested leave-one-day-out on P4 rounds 3–4): Velvetfruit with VEV_4000–5500 following makes 768k over four days, the vouchers 661k of it; in-sample 1,001k. The cost-per-delta gate never helped.
- **Filed into:** `options-and-vouchers` ("What it means for our code"); the repo's `IDEAS.md` (the voucher row and a note under the benchmark), `README.md`, `CLAUDE.md`, `ON_THE_DAY.md` ("Products"), `TODO.md`.
- **Citations moved:** template line citations re-mapped with a diff of the old and new file.

## [2026-10-13] query | held-out days in the grid
`arena.grid` now holds out each day in turn: the best combination by PnL on the other days is scored on the day left out, from the runs it already did. It also flags days whose data repeats; P4's round 4 trades add counterparty names to two days of round 3.
- **Result:** no selection bias for Kelp on P3 round 1; −14% for Velvetfruit with its vouchers on P4 rounds 3–4.
- **Filed into:** `validation-and-overfitting` ("What it means for our code"); the repo's `README.md`, `CLAUDE.md` and `TODO.md` (the grid item, CSCV still to build).

## [2026-10-13] query | baskets in the template
`python/bots/template.py` gains a `basket` mode: a basket's spread against its legs, traded with the level settings, with optional hedging legs. The cross-product hook becomes `Market`, which holds every book and this tick's plans.
- **Result** (`python/experiments/baskets.py`, nested leave-one-day-out): 83k on P3 round 2 and 281k on P2 round 3 over three days, against 20k for plain market making. Hedging lost. Baskets only take, because their resting quotes were picked off under `--resting`. Market making on the legs (Roses, Chocolate) lost up to 1.5M under `--resting`, so the legs are left out.
- **Filed into:** `baskets-and-fixed-sums` ("What it means for our code", "How to test it here"); the repo's `IDEAS.md` (two tested rows; the band row narrowed), `README.md`, `CLAUDE.md`, `ON_THE_DAY.md` ("Products"), `TODO.md` (multi-product item done).

## [2026-10-13] query | a jump measure in arena.diagnose
`arena.diagnose` gains a `jumps` column: the share of ticks on which the wall mid moves more than half the spread, and at least a tick. From 5% it adds a note: if orders rest, take only.
- **Calibration:** P2/P3 products at 10–63% lost 140k–1.5M under `--resting` with the template's market making; Kelp, at 0%, did not. All 50 P4 round 5 products are flagged (51–76%), and six that were tested lost 0.7–2.4M each under `--resting`, against 2–27k each in the default mode.
- **Filed into:** `reading-the-data-on-day-one` (a new row); the repo's `README.md`, `IDEAS.md` and `ON_THE_DAY.md` ("Do unfilled orders rest between ticks?").

## [2026-10-13] query | dress rehearsal on P3 round 3
P3 round 3 treated as a first download, following `ON_THE_DAY.md`: diagnose, the decision table, the options check, grids with held-out days, then validate. The template went from 243k to 594k over the three days, but most old products' days are reused from round 2. Two kinds of fix came out of it.
- **Tooling, fixed:** strict `--set` values, flags for the options check, repeated days compared per product.
- **Gaps, recorded:** trading the smile (P3's vouchers stray from Black–Scholes by more than the spread), levels that drift across days, and how to choose when the grid's measures disagree.
- **Filed into:** `reading-the-data-on-day-one` (a P3 round 3 reading), `options-and-vouchers`, contradictions row 6; the repo's `TODO.md` (a rehearsal item), `IDEAS.md`, `ON_THE_DAY.md`.

## [2026-10-13] lint | fixes from the code review
Five fixes from the code review (`TODO_DONE.md`, "From the code review"): the template's error handler, `level_exit` past the level, baskets pricing legs from untouched books, `make` keeping the bid below the ask, and `--resting` no longer filling from the same orders twice.
- **Numbers moved:** `baskets-and-fixed-sums` (held out 71k / 294k, was 83k / 281k) and `drift-and-regime-change` (210k held out, 152k with the day's mean, was 215k / 147k), both from re-running the experiments after the `level_exit` fix.
- **Citations moved:** the template's line citations in 20 pages were re-mapped with a diff of the old and new file (`make` is now `python/bots/template.py:421-459`). Contradictions rows 12 and 16 cited `python/bots/template.py:476-508` (`execute` and the ADAPTER) for the quoting rule; they now cite `make`.

## [2026-10-13] lint | citation ranges into our own code
`lint.py` now warns when a cited range into `python/bots/`, `python/arena/` or `python/experiments/` doesn't start a definition (a `def`, `class`, decorator, assignment, annotated field or dict entry): such a range has usually been left behind by an edit, and the old check only asked whether the line exists.
- **Caught on its first run, and fixed:** `book-imbalance-and-micro-price` cited `python/arena/analysis.py:189-215` for the markouts (now `206-233`); `informed-counterparties` cited `python/arena/model.py:27-35`, inside `Book.wall_mid`, for `MarketTrade` (now `39-48`); `reading-the-data-on-day-one` cited `python/arena/diagnose.py:50-68`, starting at an import, for the thresholds (now `52-73`, twice).
- **Also:** `book-imbalance-and-micro-price` listed three `fair` methods; it now lists all five.

## [2026-10-13] query | do the round-number jumps generalise?
`python/experiments/p4_jumps.py` and the template's new `jump` mode. The Robots' 309–509k in the benchmark is one product-day (ROBOT_DISHES, P4 round 5 day 4); both teams' rules reproduce in the template; with a reversal gate measured on the day, the mode runs on all 50 round 5 products with no losing day (+501k in-sample), and no other P2–P4 round shows the effect. Updated [jumps](concepts/jumps-and-snap-back.md) and the DU and Baguette Fromage source pages; results in `IDEAS.md`.
- **Citations moved:** the new `DEFAULTS` lines, the `jump` branch of `trade_product` and `jump_target` shifted `python/bots/template.py`; its citations in 19 wiki pages were re-mapped with a diff of the old and new file.

## [2026-10-13] ingest | Qminers Quant Hackathon 2024
`qminers-hackathon-2024/` (AdamBobocky/qminers-24, the 1st-place team's repo, pinned in `clone.sh`), found by the user as `last_year_challenge/` on a branch of their private 2025 repo. New source page [qminers-hackathon-2024](sources/qminers-hackathon-2024.md). Updated [submission-and-scoring-mechanics](concepts/submission-and-scoring-mechanics.md) (Qminers' format over two years, the evaluator reused), [risk-and-protecting-a-lead](concepts/risk-and-protecting-a-lead.md) (risk chosen for the chance of winning; halving risk while ahead) and [probing-the-environment](concepts/probing-the-environment.md) (scrambled finals data, the leaderboard as information). The rest of the user's 2025 branches are the organisers' 2025 files, already covered, and the team's own betting models: not ingested.

## [2026-10-13] query | is any named trader worth following?
`python/experiments/counterparties.py` and the template's new `copy` mode. On P3 round 5 Olivia is right on all 19 trades and copying her pays on Croissants and Squid Ink out of sample (+54k); no P4 Mark is worth following, which settles [contradictions](contradictions.md) row 3 for P4. Choosing names by mean move loses out of sample; choosing by hit rate finds only Olivia. Updated [informed counterparties](concepts/informed-counterparties.md); results in `IDEAS.md`.
- **Citations moved:** the new `DEFAULTS` lines, `Market.trades`, `copy_target` and `read_trades` shifted `python/bots/template.py`; its citations were re-mapped with a diff of the old and new file.

## [2026-10-13] restructure | Avellaneda–Stoikov: the published version replaces the preprint
The user saved the published paper (Quantitative Finance 8(3), 2008); the 2006 preprint moved to `literature_raw/superseded/`. Rebuilt [hft-in-a-limit-order-book](sources/hft-in-a-limit-order-book.md) from it, every formula checked on the page images. **Settled:** the spread is `γσ²(T − t) + (2/γ)·ln(1 + γ/k)` (eq. 30), as GLFT's footnote and Hummingbot have it. **Found:** the preprint's infinite-horizon `r̄^a` and `r̄^b` were swapped (checked on both PDFs), and its simulation tables differ (the wiki had quoted them). Re-pointed the citation in [optimal-quoting-models](concepts/optimal-quoting-models.md) and settled its "which spread" question; [dealing-with-inventory-risk](sources/dealing-with-inventory-risk.md)'s open point closed. OCR traps: eqs. 6–7, 13, 14, 19 and the solution of 28 (listed on the source page).

## [2026-10-13] ingest | Rigtorp, Databento, Quant.SE (queue position) and Hummingbot (A–S)
The user printed Rigtorp, Databento and the Quant.SE thread; converted to `literature_md/`. Databento's tutorial (needs JavaScript) was rendered with headless Chrome into `online-snapshots/databento-queue-position-tutorial.md`; Hummingbot's two posts were saved from their static HTML into `online-snapshots/` (Marker dropped most of their dark-mode printouts). New source pages [rigtorp-queue-position](sources/rigtorp-queue-position.md), [quant-se-order-position](sources/quant-se-order-position.md), [databento-queue-position](sources/databento-queue-position.md), [hummingbot-avellaneda-stoikov](sources/hummingbot-avellaneda-stoikov.md); [online-articles](sources/online-articles.md) now holds only Optiver. **Corrected:** `log(1 + x)` is not a back-of-queue bias at every position, so the `TODO.md` queue item's advice to prefer it was wrong; the evidence fits `P(ahead) = xⁿ` (hftbacktest's `PowerProbQueueFunc3`), and Databento's one order sat between `n = 20` and our rule. **Found:** Databento's printed formula is the inverse of what its code computes. Updated [queue-position-and-fills](concepts/queue-position-and-fills.md), [optimal-quoting-models](concepts/optimal-quoting-models.md), [market-making-and-inventory-skew](concepts/market-making-and-inventory-skew.md), [queue-position-valuation](sources/queue-position-valuation.md).

## [2026-10-13] ingest | five market-making papers from the triage
`mean-reverting-reference-price` (Ahuja et al. 2017), `limit-and-market-orders` (Guilbaud & Pham 2012), `online-learning-market-making` (Fernandez-Tapia 2016) read; `competing-dealers` (Yang et al. 2017) partly read and `pro-rata-microstructure` (Guilbaud & Pham 2013) mapped, both conditional on the Arena's rules. Source pages for all five; updated [optimal-quoting-models](concepts/optimal-quoting-models.md), [market-making-and-inventory-skew](concepts/market-making-and-inventory-skew.md), [drift-and-regime-change](concepts/drift-and-regime-change.md), [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md), [queue-position-and-fills](concepts/queue-position-and-fills.md). **Settled** [contradictions](contradictions.md) row 1 for P4 Osmium with a grid: no skew is best on every measure, and the mean-reverting model's constant quotes lose 13% to `wall_mid` (`IDEAS.md`). **Found:** Fernandez-Tapia's numerical example (ψ* = 2.52) contradicts his Theorem 1 (checked by simulation), and his eqs. 23–24 have the wrong sign. OCR traps on each source page.

## [2026-10-13] ingest | arXiv q-fin.TR sweep: four papers
Seventeen arXiv API queries, one per open question, 164 unique results, triaged in `references/SEARCH_LOG.md`. Added and given source pages: [market-makers-dilemma](sources/market-makers-dilemma.md) (a live experiment; partly read), [negative-drift-of-a-fill](sources/negative-drift-of-a-fill.md) (partly read; eq. 3 checked on the page image), [stochastic-liquidity-demand](sources/stochastic-liquidity-demand.md) (introduction only), [algorithmic-cooperation-mm](sources/algorithmic-cooperation-mm.md). Updated [queue-position-and-fills](concepts/queue-position-and-fills.md), [market-making-and-inventory-skew](concepts/market-making-and-inventory-skew.md), [book-imbalance-and-micro-price](concepts/book-imbalance-and-micro-price.md), [backtesting-and-tooling](concepts/backtesting-and-tooling.md), [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md), [risk-and-protecting-a-lead](concepts/risk-and-protecting-a-lead.md), [optimal-quoting-models](concepts/optimal-quoting-models.md); a new probe 18 in `ON_THE_DAY.md`. **Measured:** buy and sell market trades in the same tick, 0.01–0.02% of ticks on P4 round 1 and 0.6–1.1% on P3 round 1, so Capponi et al.'s simultaneous-arrival effect does not apply per tick. OCR trap: DeLise's eq. 3 loses its conditional bar.

## [2026-10-13] ingest | three ICAIF 2025 papers
`marl-competition-no-collusion` (read), `etf-trade-flow-decomposition` (partly read), `cross-asset-order-flow` (read), saved by the user from the ACM Digital Library. Source pages for all three; updated [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md), [baskets-and-fixed-sums](concepts/baskets-and-fixed-sums.md), [book-imbalance-and-micro-price](concepts/book-imbalance-and-micro-price.md). **Measured:** on P3 round 2 the legs do not lead the picnic baskets, nor the baskets the legs (correlations +0.01 to +0.04 at 1–20 ticks, both ways; `IDEAS.md`). OCR trap: two numbers in Lee et al.'s Table 2.


## [2026-10-14] query | how could the organisers make the rounds harder?
Asked by the user, who expects the rounds to be designed against teams that hand the task to an agent. New concept page [harder-rounds](concepts/harder-rounds.md): 25 mechanisms in five groups, each with a likelihood, what it breaks, the tell on the day and the prep, plus a ranked list of prep proposals. **Found:**
- Qminers' 2024 qualification leaderboard has `_LLM_BENCHMARK_` 2nd, ahead of every team but the winner (checked on the screenshot).
- The template takes 0.15 ms a tick on P3 round 3's 15 traded products, so a Prosperity-style time limit is far off; speed as priority conflicts with reproducible reruns.

Web sources (fetch summaries) added to [online-articles](sources/online-articles.md): Optiver's LLM-trading article, the Ready Trader Go rules, ABIDES's RMSC04 config.

## [2026-10-14] ingest | five papers behind the harder-round prep
Downloaded by the agent (each checked with `pdfinfo` and its first page), converted, given source pages: [abides-simulator](sources/abides-simulator.md), [lob-simulation-realism](sources/lob-simulation-realism.md), [spoofing-abm](sources/spoofing-abm.md), [learning-market-maker](sources/learning-market-maker.md), [online-changepoint-detection](sources/online-changepoint-detection.md). Each backs a prep entry in [harder-rounds](concepts/harder-rounds.md) (A1, B1, B3/B4, D3, E2); also linked from [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md), [informed-counterparties](concepts/informed-counterparties.md), [drift-and-regime-change](concepts/drift-and-regime-change.md). `SEARCH_LOG.md`'s "skip ABIDES" verdict reversed for the paper. **Found:**
- OCR: Marker drops the `δ` in Wang & Wellman's variance step (`(1−κ)^{2δ}`), and Das's no-order formula gains an `α`.
- In the papers themselves: Das's no-order probabilities exceed 1 in the middle case (the correct term is `Φ((P_a−V)/σ_W) − Φ((P_b−V)/σ_W)`); Adams & MacKay's Algorithm 1 indexes the hazard differently from their eq. 4; Get Real's impact fit averages an unsigned participation against a signed move.
- Das's market maker loses when jumps are not announced; Wang & Wellman's spoof raises prices but adds 1.2–11.5 to an exploiter's profit of about 200.
- ABIDES's computation delay is configured per agent, not measured, which supports E2's "speed is not a race".

Still pending: Gu et al. 2024 (split from the local ICAIF 2024 proceedings) and Wang, Hoang & Wellman 2020 (`MANUAL_TODO.md` E).

## [2026-10-14] ingest | the two spoofing sequels
[trading-under-manipulation](sources/trading-under-manipulation.md) (Wang, Hoang & Wellman 2020, saved by the user) and [spoofability-and-liquidity](sources/spoofability-and-liquidity.md) (Gu et al. 2024, split by the agent from PDF pages 260–268 of the ICAIF 2024 proceedings; `pdfseparate` produced a 1.7 GB file, so the split uses pypdf). Both converted, read whole, and cited from D3 in [harder-rounds](concepts/harder-rounds.md) and from [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md). **Found:**
- The spoof pays only right behind the best bid, adds 22–26 to an exploiter earning 199–468 without it, and traders that ignore that level lose almost nothing (646–652 against 651).
- Spoofing pays in thin markets and fades in liquid ones; a market maker quoting near fair is itself the defence. Gu et al.'s simulator (PyMarketSim) is public Python: the candidate base for the A1 generator.
- OCR: Marker scrambles the 2020 paper's Table 2 (shifted columns, 494 read as 594) and garbles Gu et al.'s Table 1; correct values on the source pages, from the PDF's text layer. In Gu et al. itself, a truncation condition lacks a `ξ`.

## [2026-10-14] ingest | seven ICAIF 2021–2024 papers
From the ICAIF 2020–2024 triage, saved by the user: [market-making-perceived-collusion](sources/market-making-perceived-collusion.md), [order-stacking-mm](sources/order-stacking-mm.md), [decomposed-ofi](sources/decomposed-ofi.md) (the 21-page extended version), [scaled-beta-policies](sources/scaled-beta-policies.md), [mm-adverse-selection-rl](sources/mm-adverse-selection-rl.md), [classify-trading-agents](sources/classify-trading-agents.md), [collective-liquidity-taking](sources/collective-liquidity-taking.md). Three more the user saved were already ingested by another session (`lob-simulation-realism`, `spoofability-and-liquidity`, `trading-under-manipulation`); this session's edits cite those pages, and its accidental overwrites of two of them were reverted. Updated [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md) (and fixed its doubled Sources line), [queue-position-and-fills](concepts/queue-position-and-fills.md), [book-imbalance-and-micro-price](concepts/book-imbalance-and-micro-price.md), [price-impact](concepts/price-impact.md), [market-making-and-inventory-skew](concepts/market-making-and-inventory-skew.md), [hidden-takers-and-empty-sides](concepts/hidden-takers-and-empty-sides.md), [reading-the-data-on-day-one](concepts/reading-the-data-on-day-one.md), [backtesting-and-tooling](concepts/backtesting-and-tooling.md), [informed-counterparties](concepts/informed-counterparties.md); new [contradictions](contradictions.md) row 17 (learned collusion under price priority). **Found:** applying a cancel's expected share to the queue ahead is optimistic against sampling where it falls (order stacking), now on the queue item in `TODO.md`. The ETF-arbitrage paper did not arrive (its file is a copy of another).

## [2026-10-14] ingest | Shearer et al., ETF arbitrage
[etf-arbitrage-abm](sources/etf-arbitrage-abm.md), the user's second try (the first file was a copy of another paper). Updated [baskets-and-fixed-sums](concepts/baskets-and-fixed-sums.md) and [harder-rounds](concepts/harder-rounds.md) (B5's evidence).

## [2026-10-14] ingest | thirteen papers for the harder rounds
From the spoofing and harder-round triage tables, fetched or split out by the agent: [detecting-spoofing-strategies](sources/detecting-spoofing-strategies.md), [spoofing-learning-algorithms](sources/spoofing-learning-algorithms.md), [optimal-spoofing](sources/optimal-spoofing.md), [manipulation-statistical-physics](sources/manipulation-statistical-physics.md), [learning-not-to-spoof](sources/learning-not-to-spoof.md), [adversarial-attacks-hft](sources/adversarial-attacks-hft.md), [manipulation-detection-evasion](sources/manipulation-detection-evasion.md), [llm-agents-market-simulation](sources/llm-agents-market-simulation.md), [pymarketsim](sources/pymarketsim.md), [benchmark-manipulation](sources/benchmark-manipulation.md), [market-making-latency](sources/market-making-latency.md), [dtw-lead-lag](sources/dtw-lead-lag.md), [guessing-games](sources/guessing-games.md). Five came from arXiv, two from Oxford's repository (the Cartea et al. spoofing paper only as thesis chapters, since SSRN blocks downloads), one from IJCAI's site, one from a PSE course page, four from the local ICAIF proceedings (split with pypdf: poppler's `pdfseparate` choked on the proceedings' recursive dictionaries). Updated [harder-rounds](concepts/harder-rounds.md) (A1, B5, C3, C5, D2, D3, D4), [book-imbalance-and-micro-price](concepts/book-imbalance-and-micro-price.md), [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md), [ai-assisted-work](concepts/ai-assisted-work.md), [backtesting-and-tooling](concepts/backtesting-and-tooling.md), [market-making-and-inventory-skew](concepts/market-making-and-inventory-skew.md), [risk-and-protecting-a-lead](concepts/risk-and-protecting-a-lead.md), [hidden-takers-and-empty-sides](concepts/hidden-takers-and-empty-sides.md); three tells in `ON_THE_DAY.md`, two untested rows in `IDEAS.md`. Still needed from the user: Byrd 2025 (ACM).

## [2026-10-14] ingest | Lee, Eom & Park and Byrd 2025
Saved by the user: [spoofing-traders-empirical](sources/spoofing-traders-empirical.md) (the 53-page manuscript) and [accidental-pump-and-dump](sources/accidental-pump-and-dump.md). The Korea Exchange criterion is now cited first-hand in [harder-rounds](concepts/harder-rounds.md) (D3), [hidden-takers-and-empty-sides](concepts/hidden-takers-and-empty-sides.md), [optimal-spoofing](sources/optimal-spoofing.md) and [manipulation-detection-evasion](sources/manipulation-detection-evasion.md). New points in D3: the thresholds need each product's own baseline, a persistence check alone misses long-lived spoofs, and keep side totals out of `fair`. Byrd's population and its "more followers, more exploitable" result went into D2.

## [2026-10-14] ingest | two ICAIF 2026 preprints
Downloaded by the agent from arXiv (found by the comment-field query in `references/SEARCH_LOG.md`): [hawkes-structured-mm](sources/hawkes-structured-mm.md) and [lob-irreversibility](sources/lob-irreversibility.md). Before writing the first, `python/experiments/trade_clustering.py` checked whether Prosperity's market trades cluster. They don't (ratios 0.90–1.04 on P3 and P4 round 1), so the idea is `dropped here` in `IDEAS.md`. Updated [optimal-quoting-models](concepts/optimal-quoting-models.md) (and removed a stale duplicate of its Sources line) and [harder-rounds](concepts/harder-rounds.md) (A1's realism check).

## [2026-10-15] restructure | the day generator is built
`python/arena/sim.py` implements A1 of [harder-rounds](concepts/harder-rounds.md) from the spec on [pymarketsim](sources/pymarketsim.md), [spoofing-abm](sources/spoofing-abm.md) and [abides-simulator](sources/abides-simulator.md) (seeding), calibrated with [lob-simulation-realism](sources/lob-simulation-realism.md)'s idea of an acceptance test through `arena.diagnose`. First result in `IDEAS.md`: replay `--match-trades all` overstates the template in a reactive market, and `worse` is close.

## [2026-10-15] restructure | the LLM zoo
`python/bots/zoo/` implements D2 of [harder-rounds](concepts/harder-rounds.md), with archetype prompts after [llm-agents-market-simulation](sources/llm-agents-market-simulation.md). Six Claude bots; results in `IDEAS.md`. Other providers' bots are a manual item.

## [2026-10-15] restructure | the stress harness and the template's protection
`python/arena/stress.py` implements B1's harness in [harder-rounds](concepts/harder-rounds.md); the template gains a loss stop and guards. The volatility guard is a stand-in for [online-changepoint-detection](sources/online-changepoint-detection.md)'s detector, not that algorithm.
- **Citations moved:** the template's line citations in 32 pages were re-mapped with a diff of the old and new file (`make` is now `python/bots/template.py:566-604`).

## [2026-10-15] restructure | Kelp's make_edge 0.5 in the template
The template's Kelp moves to `make_edge` 0.5 (tuned on Prosperity 3 data for `worse` fills, not on the Arena; `IDEAS.md`, "Why the zoo beat the template head to head"). Five comment lines went in above it.
- **Citations moved:** 40 of the template's line citations re-mapped with a diff of the old and new file, range ends included (`make` is now `python/bots/template.py:571-635`).

## [2026-10-15] restructure | queue models in the engine
[queue-position-and-fills](concepts/queue-position-and-fills.md): `--queue back|prob|front` now exists; "What it means for our code" records the `arena.sim` check (`front` within 5% for a quote that joins the walls, `prob` blind to re-posting at the same size).

## [2026-10-15] restructure | adversarial rivals measured
[shared-market-and-adversaries](concepts/shared-market-and-adversaries.md): the trapper, spoofer and sniper now exist (`python/bots/rivals/`), with their cost to the template on P3 round 1; "How to test it here" points to `python/experiments/adversaries.py`. The template's `fixed_guard` now reads the sized mid; 35 of its line citations re-mapped (range ends included).

## [2026-10-15] query | book imbalance and the micro-price on Prosperity data
[book-imbalance-and-micro-price](concepts/book-imbalance-and-micro-price.md): new section "Tested here" (`python/experiments/imbalance.py`, the template's `weighted_mid` and `imbalance`): `ρ` predicts the plain mid's noise, not the wall mid; dropped here. [contradictions](contradictions.md) row 11 notes the result. Template citations re-mapped after the edit.

## [2026-10-17] query | regime changes in a market that reacts, and a changepoint detector
`arena.sim` gains `--regime`, a mid-day shift or trend sized in each product's spread, and a Hydrogel-like preset. The template gains `changepoint_level` (Adams & MacKay, on block means of a level product), off by default.
- **Results** (`python/experiments/sim_regimes.py`; `arena.stress` on P4 rounds 3–4):
  - `fixed_guard` holds Resin in the reacting market.
  - Hydrogel's level bet loses most on a trend, and its loss stop rarely fires.
  - The detector finds shifts and trends, but neither re-estimating the level nor dropping the bet wins on balance: dropping costs 17% of P4's plain days.
- **Filed into:** `harder-rounds` (B1), `online-changepoint-detection` ("In our notation"); the repo's `IDEAS.md` (two rows), `TODO.md`, `ON_THE_DAY.md`, `CLAUDE.md`.

## [2026-10-17] lint | pages that said the flatten and the probe bot were still to do
`risk-and-protecting-a-lead`, `harder-rounds` (C5), `optimal-quoting-models` and `probing-the-environment` still described `flatten_from` and `python/bots/probe.py` as deferred items in `TODO.md`. Updated: both are built, with their results.

## [2026-10-18] lint | template citations after Kelp moved to `sized_mid`
Two comment lines added to Kelp's entry in `python/bots/template.py` PARAMS shifted every line from 113 down by two. Re-mapped the citations in 28 pages (each cited line checked against the old file). `shared-market-and-adversaries` describes Kelp on `wall_mid` under the far spoofer; that is the result that moved it.

## [2026-10-18] query | two more `arena.sim` presets: jumps that snap back, one-sided takers
- `ROBOT_DISHES` copies P4 round 5's jumping day; `KELP_FLOW` copies P3 round 1 Kelp's taker flow, which turned out to be 35% buys by count, not persistent signs (`C(1)` 0.04 net of the imbalance).
- **Filed into:** `jumps-and-snap-back` ("What it means for our code"), `market-making-and-inventory-skew` (the `C(1)` measurement); the repo's `IDEAS.md` (two rows), `TODO.md` (the presets item, Kelp's long drift, the mock round's data), `CLAUDE.md`, `README.md`.

## [2026-10-18] query | when is a quote worth posting; GLFT's skew measured
- `python/experiments/quote_markouts.py`: the template's passive fills, valued against the wall mid by the state when quoted. No state has a negative total on Prosperity data; the adverse moves are 0.5 a unit at most, against edges of 0.6–7.4.
- `python/experiments/glft_skew.py`: `σ`, `A`, `k` per product and GLFT's skew. The exponential fill model fits poorly, and every `γ` costs PnL.
- Checked jmerle's claim that P3's Resin is P2's Amethysts: the same books on all three days (`submission-and-scoring-mechanics`).
- **Filed into:** the repo's `IDEAS.md` (three rows moved from "Not yet tested"), `README.md` (reused days), `ON_THE_DAY.md` (probe 18).

## [2026-10-18] query | a rival that undercuts the template
- `python/experiments/undercut.py`: the template against a copy at `make_edge` 0, per tick and with `--resting`. Per tick it costs what any copy costs; with resting orders it wins Resin's whole passive flow from `make_edge` 2, and 1 is the best reply. Two copies of Pepper Root's drift bet fight over it.
- **Filed into:** `shared-market-and-adversaries` (the Wang et al. bullet); the repo's `IDEAS.md` (the row moved from "Not yet tested"), `TODO.md` (a decision on Resin's edge), `ON_THE_DAY.md` (orders that rest).

## [2026-10-18] query | quote size against rivals; template citations re-mapped
- `python/experiments/quote_size.py`: capping the template's quote never binds alone, but saves Pepper Root's drift bet from a rival with the same view (213k → 430k against a copy). Pepper Root now quotes 10 at most.
- `python/bots/template.py` gained three comment and parameter lines at 136–141: every citation at line 139 or later moved by 3 (28 pages).
- **Filed into:** `shared-market-and-adversaries`; the repo's `IDEAS.md`, `ON_THE_DAY.md` ("Before the first submission").

## [2026-10-18] query | PBO and the deflated Sharpe ratio built into arena.grid
- `python/arena/grid.py` now prints the trials, CSCV's PBO and the DSR of the best cell's gain over the bot as is; the detector checks and five real grids are on `validation-and-overfitting`.
- **Filed into:** `validation-and-overfitting` ("What it means for our code", "How to test it here"); the repo's `README.md` ("Grid search"), `TODO.md` (item ticked), `ON_THE_DAY.md` ("Evaluation data"), `IDEAS.md` ("A slow fair on Osmium").

## [2026-10-18] query | trading P3's volcanic vouchers off a smile
- `python/experiments/p3_smile.py`: the smile from held-out days, the residual's fast part, and the template's new `smile` fair. Take-only on two strikes made 529k over five days, every day positive; a flat vol does as well; the delta hedge halves it; quotes lose when orders rest.
- `python/bots/template.py` gained the `smile` parameters and `smile_fair` (37 lines); every citation re-mapped by a line diff (28 pages).
- **Filed into:** `options-and-vouchers` ("What it means for our code", "How to test it here"), `contradictions` row 6; the repo's `IDEAS.md` (row moved from "Not yet tested"), `TODO.md`, `ON_THE_DAY.md` ("Products").

## [2026-10-19] ingest | overfitting, second pass: SPA, StepM, haircuts, the reusable holdout, optimal trading rules
- **Documents:** `superior-predictive-ability` (Hansen 2005), `stepwise-multiple-testing` (Romano & Wolf 2003), `backtesting-haircut` (Harvey & Liu 2015), `reusable-holdout` (Dwork et al. 2015), `optimal-trading-rules` (Carr & López de Prado 2014). White 2000, López de Prado's book chapters, Arian et al. 2024, Masters and Politis–Romano are in `MANUAL_TODO.md` (G).
- **Measured:** `python/experiments/snooping_tests.py`. The DSR fails Kelp's best `make_edge` × `take_edge` cell (0.76) where SPA (p 0.00) and StepM (three cells) pass it. Held out, the gain is real under `all` but reverses under `worse`. Five null grids gave no false positive.
- **Filed into:** `validation-and-overfitting` (theory, "What it means for our code"), `contradictions` row 18; the repo's `IDEAS.md` ("Bootstrap tests of the best cell"), `TODO.md` (research item, "SPA and StepM in `arena.grid`", the rewrite decision), `MANUAL_TODO.md` (G).
- **Traps found:** Hansen's stationary-bootstrap recursion prints `u_{b,1}` for `u_{b,t}` (typo in the paper itself); Marker dropped decimal points in Hansen's tables, moved Holm's `j ≤ i` from the max to the min, and lost all inline math in Carr & López de Prado's Section 4.

## [2026-10-19] query | SPA and StepM built into arena.grid; selection rules on unseen days
- `python/arena/grid.py` prints SPA, StepM, each StepM cell under the other modes, and a pick. `python/experiments/selection_rules.py` scores ten selection rules on unseen days; SPA + `worse` was the only one never to lose. `python/experiments/snooping_tests.py` gained PBO and BHY columns and ten null grids: null PBO averages 46.5%, so neighbouring blocks don't leak.
- **Filed into:** `validation-and-overfitting` ("What it means for our code"), the source pages' code maps (`superior-predictive-ability`, `stepwise-multiple-testing`); the repo's `IDEAS.md`, `TODO.md`, `ON_THE_DAY.md` ("Evaluation data"), `README.md` ("Grid search"), `CLAUDE.md`.

## [2026-10-19] query | a permutation test of the whole search
- `arena.grid --permute N` and `arena.stress.permute`: the grid rerun on copies of the days made of their own ticks shuffled. Hydrogel's level grid is the positive control (lift p 0.05); Kelp's edge gain needs no price order (lift p 0.80). Masters' book is unread; the method is our adaptation.
- **Filed into:** `validation-and-overfitting` ("What it means for our code"); the repo's `IDEAS.md`, `TODO.md`, `MANUAL_TODO.md` (G), `README.md`, `CLAUDE.md`.

## [2026-10-19] query | the selection rules on simulated days
- `python/experiments/selection_rules_sim.py`: each preset's grid tuned on 3 fresh `arena.sim` days, ten times, and scored on 20 other days. The grid's pick lost in 2 of 120 runs, against 10–22 for the rules that gained as much; it is not "never loses", and the docs now say so.
- **Filed into:** `validation-and-overfitting`; the repo's `IDEAS.md`, `README.md`, `ON_THE_DAY.md`, `python/arena/grid.py`'s docstring.

## [2026-10-20] query | screening a big grid
- `arena.grid --screen SHARE`: every cell on the first day under the first mode, then the best share on every day and mode; SPA, StepM and the pick are repeated on the days the screen didn't see.
- **Filed into:** `validation-and-overfitting`; the repo's `README.md`, `TODO.md`, `python/arena/grid.py`'s docstring.

## [2026-10-21] lint | arena.grid's lines moved
- `arena.grid --engine rust` added code above the bootstrap tests: the citations of `omega2`, `spa`, `stepm`, `format_snooping` and `FINE_TICKS` re-mapped (`stepwise-multiple-testing`, `superior-predictive-ability`, `validation-and-overfitting`).

## [2026-10-21] lint | arena.sim's lines moved
- `arena.sim --engine rust` added a line to the module docstring: the citations of the KELP_FLOW and ROBOT_DISHES presets re-mapped (`market-making-and-inventory-skew`, `jumps-and-snap-back`).

## [2026-10-21] lint | the grid's statistics moved to python/arena/stats.py
- `cscv`, the DSR's helpers, `omega2`, `bootstrap_means`, `spa` and `stepm` moved from `python/arena/grid.py` to `python/arena/stats.py` (twinned in `rust/src/stats.rs`; `arena.grid` still exports the names): the citations of `omega2`, `spa` and `stepm` now point there, and `format_snooping`'s moved up (`stepwise-multiple-testing`, `superior-predictive-ability`, `validation-and-overfitting`).

## [2026-10-21] lint | arena.grid's lines moved
- `arena.grid --engine rust` hands Prosperity days to Rust as references to their CSVs: the citation of `format_snooping` re-mapped (`validation-and-overfitting`).

## [2026-10-23] lint | per-tick market trades go best price first
- `python/arena/engine.py` (`_match_trades`) and its Rust twin: with two or more bots, per tick, leftover orders meet the market trades in price-time priority, where they met them in arrival order. `shared-market-and-adversaries` gets the re-run undercut figures (repo `IDEAS.md`, "Against a rival that undercuts us"); the resting results it cites are unchanged.

## [2026-10-23] lint | arena.grid's lines moved
- `arena.grid` flags an axis that never changes the PnL (`dead_axes`): the citations of `FINE_TICKS` and `format_snooping` re-mapped (`superior-predictive-ability`, `validation-and-overfitting`).

## [2026-10-23] restructure | TODO's finished items moved to TODO_DONE.md
- The repo's `TODO.md` keeps its open items; the 55 finished ones moved, word for word, to `TODO_DONE.md`. The pages that cite a finished item now cite `TODO_DONE.md` (22 places in 17 pages); `backtesting-and-tooling`'s status lines brought up to date (`--data p4` and the PnL split exist).

## [2026-10-23] restructure | the repo's architecture moved from CLAUDE.md to ARCHITECTURE.md
- CLAUDE.md's Architecture, Bot files and Known gaps sections moved word for word to `ARCHITECTURE.md`; CLAUDE.md keeps the commands, the rules that keep the code consistent and the conventions. The pages citing those sections now cite `ARCHITECTURE.md` (12 places in 11 pages).

## [2026-10-23] lint | arena.grid and arena.stats lines moved (halving, sampling, the O(cells × blocks) correlation)
- `arena.grid` gains `--halving` and `--sample`, and `arena.stats.mean_correlation` becomes the identity (‖Σz‖² − Σ‖z‖²) / (S·M(M−1)) with exact sums: the citations of `FINE_TICKS`, `format_snooping`, `omega2`, `spa` and `stepm` re-mapped (`superior-predictive-ability`, `stepwise-multiple-testing`, `validation-and-overfitting`).

## [2026-10-23] lint | fill-model scenarios in arena.grid and arena.compare
- `arena.grid --scenario` (repo `python/arena/scenario.py`) and the selection rules across ten scenarios: `validation-and-overfitting` gets the result (the worst-case PnL loses most often; the pick least). The citations of `FINE_TICKS` and `format_snooping` re-mapped (`superior-predictive-ability`, `validation-and-overfitting`).

## [2026-10-23] lint | a rival field: the taker archetype and the payoff matrix
- `python/bots/rivals/taker.py` (with a Rust twin) and `python/experiments/rival_field.py`: `shared-market-and-adversaries` gets the field result (the best reply depends on the field; Resin's edge 2 collapses against makers nearer fair when orders rest).

## [2026-10-25] lint | the Arena site changed: the portal's metrics and leaderboard
- `references/check_arena_site.py` found new portal text (submission metrics including a mark-out price, a position-limit penalty and a PnL standard error; one evaluation at a time; a submission final only once it completes; a leaderboard of each team's final submission on the private backtest). Recorded in `ON_THE_DAY.md` ("Known so far" and the items it answers); `arena-site-snapshot.txt` re-saved. Every line added sits after line 260, so the citations into it (`concepts/harder-rounds.md`, lines 151–188) are unchanged.

## [2026-10-25] lint | the Arena site's code read in full: the weights are unconfirmed
- The bundle's code, not just its strings: the 10/20/30/40% round weights are in translation strings no page uses, and the shown leaderboard is per round by PnL. `concepts/harder-rounds`, `concepts/risk-and-protecting-a-lead` and `sources/kelly-criterion` now call the weights unconfirmed; the rest is in `ON_THE_DAY.md`, "Known so far".

## [2026-10-25] lint | reading the leaderboard's curves for a shared market
- `python/experiments/leaderboard_curves.py`: `concepts/shared-market-and-adversaries` gets the result (co-movement of one sign: alone on the same data; of both signs: one market; none: data of each team's own; 88 of 90 simulated cases right).

## [2026-10-25] lint | make_inside: quoting nearer fair against rivals
- The template's `make_inside` and `python/experiments/quote_inside.py`: `concepts/shared-market-and-adversaries` gets the result, `concepts/optimal-quoting-models` names the setting. The template's lines moved (one setting, a longer `make` docstring): 57 citations to `python/bots/template.py` re-mapped.

## [2026-10-25] lint | --mark and --limit-penalty in the engine
- `python/arena/report.py` gained the penalty's line, so `sources/probability-of-backtest-overfitting`'s citation of it moved (134 → 144). No page cites the engine's lines.
