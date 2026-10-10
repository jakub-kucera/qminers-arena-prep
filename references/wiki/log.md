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
