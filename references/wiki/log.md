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
