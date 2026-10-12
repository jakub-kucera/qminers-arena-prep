---
title: The official Prosperity wikis (Notion), editions 2, 3 and 4
type: source
repo: prosperity-wikis
status: partly-read
updated: 2026-10-11
---

# The official Prosperity wikis (IMC, public Notion pages)

## What it is
The organisers' own documentation, downloaded on 2026-10-11 by `references/fetch_notion.py` into `references/prosperity-wikis/`: Prosperity 2 (17 pages), Prosperity 3 (36) and Prosperity 4 (19), each folder with an `INDEX.md`. Third-party text, not ours, gitignored. Images are links only; five "Round N" pages in the Prosperity 3 folder are empty at the source (a "[Staging]" copy). This is the only primary source in the clones for what IMC states about its environment; everything else is what teams inferred.

## Layout and code map
Prosperity 4 (`prosperity4/`): `writing-an-algorithm-in-python-192659.md` is the key page; `prosperity4/game-mechanics-overview-0d3547.md`, `prosperity4/rules-9e998c.md`, `faq-abbcbe.md`, `round-schedule-1a054f.md`, `trading-glossary-d14f71.md`, `programming-resources-72a5e3.md`, one page per round (`round-1-…` to `round-5-…`), `prosperity4/announcements-339c3b.md` (the organisers' updates) and the tutorial round.

What the key page (`prosperity4/writing-an-algorithm-in-python-192659.md`) states:
- Format: a predefined `Trader` class with a `run()` method; **round 2 also needs a `bid()` method**, harmless in other rounds (`prosperity4/writing-an-algorithm-in-python-192659.md:11`).
- Simulation length: **1,000 iterations while testing, 10,000 for the scored run** (`prosperity4/writing-an-algorithm-in-python-192659.md:13`).
- **Position limit rule**: if the aggregated quantity of all buy (sell) orders in an iteration would, if fully matched, take the position beyond the limit, **all** the orders for that product are rejected (`prosperity4/writing-an-algorithm-in-python-192659.md:21`, `prosperity4/writing-an-algorithm-in-python-192659.md:233`).
- Execution is instantaneous; no bot can act faster than the player's order (`prosperity4/writing-an-algorithm-in-python-192659.md:227`).
- **Time limit: 900 ms per `run` call** (average expected ≤ 100 ms) (`prosperity4/writing-an-algorithm-in-python-192659.md:432`).
- **Libraries (Appendix C): everything in the Python 3.12 standard library, plus pandas, NumPy, `statistics`, `math`, `typing` and `jsonpickle`; "importing other, external libraries is not supported"** (`prosperity4/writing-an-algorithm-in-python-192659.md:609-620`).
- Uploading runs the algorithm for 1,000 iterations on a sample day different from the scored one and returns a log with the algorithm's prints (`prosperity4/writing-an-algorithm-in-python-192659.md:434-442`).
- `prosperity4/game-mechanics-overview-0d3547.md`: five rounds over 16 days, rounds 1–2 last 72 hours and rounds 3–5 48 hours; the last successfully processed submission is locked in when the round ends.

## What carries over
It answers, for IMC, several items in `ON_THE_DAY.md` that remain open for the Arena (entry point, per-tick call, libraries, time limit, limit rule). It is also the best model for how an organiser documents a bot interface. See [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md).

## Traps
- It describes **Prosperity**, not the Arena. Our stdlib-only rule is stricter than IMC's, which is deliberate while the Arena's library list is unknown.
- The page's runtime limits mean the logger boilerplate and heavy analysis in a `run` call matter (see [prosperity3-cmu-physics](prosperity3-cmu-physics.md) for a memory incident).
- Screenshots and tables that were images are not in the markdown.

## Read depth
- **Read:** `prosperity4/writing-an-algorithm-in-python-192659.md` lines 7–24, 202–240, 427–442, 609–640; the first ~40 lines of `prosperity4/game-mechanics-overview-0d3547.md`, `prosperity4/rules-9e998c.md`, `prosperity4/what-is-prosperity-68789f.md` and `prosperity4/announcements-339c3b.md`.
- **Mapped:** the other Prosperity 4 pages by title.
- **Unread:** the FAQ, the round pages (products, position limits and hints per round), the glossary, and the whole Prosperity 2 and 3 folders beyond their first page.

## Cited by
[submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [many-products-architecture](../concepts/many-products-architecture.md).
