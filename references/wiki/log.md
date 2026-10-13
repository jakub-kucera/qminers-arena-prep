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

New items: `TODO.md` "Markouts and fill edge against the wall mid"; `ON_THE_DAY.md` "Do our own trades move the market?" with probe 17. Overview findings 12–14.

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
- **Citations moved:** the new `DEFAULTS` line and `make` docstring shifted `bots/template.py`. Its citations in 19 wiki pages were re-mapped with a diff of the old and new file (`make` is now `bots/template.py:203-235`).

## [2026-10-13] query | the wall-mid definitions compared
Settled contradictions row 2 for Prosperity data and closed the `TODO.md` item.
- **Method:** four definitions, each run in a copy of the template: the largest level (ours), the outermost (Frankfurt), DTU's rule, and the first level from the top with at least 15 (Baguette Fromage round 5, Linear Utility). Compared on Starfruit, Kelp, Osmium and Pepper Root, in all three engine modes, by signature-plot noise, and against the teams' P4 bots under `--resting`.
- **On its own:** the outermost level ties or wins on every worst day, by 0–1.3%.
- **With rivals' resting orders:** only `sized_mid` survives (+39k on Osmium where the others lose 377–654k), because a rival's far order becomes the largest and the outermost level.
- **The template** gains `outer_mid` and `sized_mid` (with `wall_size`). The Prosperity products keep `wall_mid`.
- **Filed into:**
  - the wiki: `fair-value-and-wall-mid` (a per-day table), `shared-market-and-adversaries`, `reading-the-data-on-day-one`, contradictions row 2;
  - the repo: `IDEAS.md`, `ON_THE_DAY.md`, `README.md`, `CLAUDE.md`.
- **Citations moved:** template line citations re-mapped again (`make` is now `bots/template.py:203-235`).

## [2026-10-13] query | P4 levels and vouchers measured
Measured what the teams' P4 round 3–4 money is made of, with two committed scripts (`experiments/p4_levels.py`, `experiments/p4_vouchers.py`) on the four distinct days.
- **Levels:** Hydrogel's and Velvetfruit's daily means agree within 13 and 16 across days. Replacing Baguette Fromage's and DU's hard-coded levels with the other days' mean keeps 90% of their PnL; the day's running mean keeps 55–57%.
- **Vouchers:** implied vol is flat within each day, each voucher sits within about half a spread of Black–Scholes at one vol, and the teams' voucher PnL is delta × Velvetfruit's move. Contradictions row 6 settled for P4; the options page's link to it said row 5 and is fixed.
- **Filed into:** `drift-and-regime-change`, `options-and-vouchers`, `reading-the-data-on-day-one`, contradictions row 6; the repo's `IDEAS.md` (two tested rows; the untested spot-level row removed, the options row narrowed to smile trading on P3).

## [2026-10-13] query | a level mode in the template
`bots/template.py` gains `level_target` and `estimate_level`: for a product that returns to a level, the target is the full limit against a move of `level_band`, held until the other band. The level is a number from earlier days, the day's running mean (`"day"`), or a blend (`level_weight`).
- **Result** (`experiments/p4_level_template.py`, nested leave-one-day-out on P4 rounds 3–4): 215k over four days on Hydrogel and Velvetfruit, against 286k in-sample and 147k with the day's own mean. Blending did not help.
- **Filed into:** `drift-and-regime-change` ("What it means for our code"), `reading-the-data-on-day-one` (the reverts-to-a-level row); the repo's `IDEAS.md`, `README.md`, `CLAUDE.md`, `ON_THE_DAY.md`, `TODO.md`.

## [2026-10-13] query | options follow their underlying in the template
`bots/template.py` gains a cross-product hook and a mode for options. `Trader.run` trades followed products first and passes their plans. A product with `follow` and `strike` holds the underlying's target as a share of its own limit (`follow_target`). Black–Scholes is in total variance, so delta comes from the option's own price without an expiry date.
- **Result** (`experiments/p4_vouchers_template.py`, nested leave-one-day-out on P4 rounds 3–4): Velvetfruit with VEV_4000–5500 following makes 768k over four days, the vouchers 661k of it; in-sample 1,001k. The cost-per-delta gate never helped.
- **Filed into:** `options-and-vouchers` ("What it means for our code"); the repo's `IDEAS.md` (the voucher row and a note under the benchmark), `README.md`, `CLAUDE.md`, `ON_THE_DAY.md` ("Products"), `TODO.md`.
- **Citations moved:** template line citations re-mapped with a diff of the old and new file.
