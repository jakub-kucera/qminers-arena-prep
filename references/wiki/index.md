# Index of the references wiki

Read this first, then the pages it points to. Conventions, workflows and the lint are in [`SCHEMA.md`](SCHEMA.md); the history of changes is in [`log.md`](log.md). Pattern: Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (raw sources → wiki → schema). The raw sources are the clones in `references/<repo>/`; this wiki never edits them.

**If you only have a minute:** [`overview.md`](overview.md). **If you have a question:** find the concept below, read it, follow its citations. **If something looks wrong:** check the cited line, fix the page, add a `lint` entry to the log.

## Overview and open questions
- [overview.md](overview.md): what the Prosperity record teaches and what probably carries to the Arena.
- [contradictions.md](contradictions.md): disagreements between sources, README-versus-code mismatches, open questions, each with what would settle it.

## Concepts (synthesised across sources)
- [fair-value-and-wall-mid](concepts/fair-value-and-wall-mid.md): the mark is the market maker's mid; five definitions of "wall mid".
- [market-making-and-inventory-skew](concepts/market-making-and-inventory-skew.md): take / clear / make, and the unsettled question of skew.
- [hidden-takers-and-empty-sides](concepts/hidden-takers-and-empty-sides.md): quoting ~100 away when a side is empty; recurring takers; the 20% removed orders.
- [drift-and-regime-change](concepts/drift-and-regime-change.md): drifting, pegged and mean-reverting products; fixed anchors that broke.
- [baskets-and-fixed-sums](concepts/baskets-and-fixed-sums.md): known baskets, the 50,000 pebbles sum, and why searching for unknown ones fails.
- [options-and-vouchers](concepts/options-and-vouchers.md): why smile trading rarely paid; deep-OTM 0/1; stdlib Black–Scholes.
- [informed-counterparties](concepts/informed-counterparties.md): Olivia, the Marks, and the rollbacks.
- [jumps-and-snap-back](concepts/jumps-and-snap-back.md): round-number jumps that reverse; DU's three-tick rule.
- [many-products-architecture](concepts/many-products-architecture.md): intents, cluster strategies, ownership, safety nets.
- [validation-and-overfitting](concepts/validation-and-overfitting.md): worst-day, leave-one-day-out, multiple testing, not opening the unseen day.
- [queue-position-and-fills](concepts/queue-position-and-fills.md): our resting model versus hftbacktest's, and the evidence on cancels.
- [risk-and-protecting-a-lead](concepts/risk-and-protecting-a-lead.md): scoring formats, cutting variance, stopping when safe.
- [shared-market-and-adversaries](concepts/shared-market-and-adversaries.md): book-sniping, crowded edges, what to do if the Arena is shared.
- [submission-and-scoring-mechanics](concepts/submission-and-scoring-mechanics.md): the Arena's described format against four comparison events; limits by edition; data shape.
- [backtesting-and-tooling](concepts/backtesting-and-tooling.md): matching rules, the P4 fork, log conversion, what backtesters cannot do.
- [ai-assisted-work](concepts/ai-assisted-work.md): how the winners used agents and what they warn about.
- [cross-market-and-conversions](concepts/cross-market-and-conversions.md): orchids, macarons, cross-venue; unsupported by the backtesters.
- [probing-the-environment](concepts/probing-the-environment.md): experiments on the simulator before strategies: the PnL mark, bot tolerances, no-queue, sample data that is really live data.

## Sources (one page per clone; each ends with a "Read depth" section)
Team write-ups and code:
- [prosperity3-frankfurt-hedgehogs](sources/prosperity3-frankfurt-hedgehogs.md): P3 2nd; origin of the wall mid; the published file is broken.
- [prosperity4-baguette-fromage](sources/prosperity4-baguette-fromage.md): P4 4th; most detailed; intents architecture.
- [prosperity4-dtu-quant-lab](sources/prosperity4-dtu-quant-lab.md): P4 28th; stdlib option helpers, regime detector, literature review.
- [prosperity4-du-trading](sources/prosperity4-du-trading.md): P4 10th; wide fills, snap-back rule; README ≠ code.
- [prosperity4-ryan-challman](sources/prosperity4-ryan-challman.md): P4 57th; validation discipline and rollbacks.
- [prosperity4-alpha-search](sources/prosperity4-alpha-search.md): P4; README only; multiple testing, PnL decomposition.
- [prosperity2-linear-utility](sources/prosperity2-linear-utility.md): P2 2nd; ancestor of `bots/template.py`.
- [prosperity3-alpha-animals](sources/prosperity3-alpha-animals.md): P3 9th; conversions, copy-trading; state on `self`.
More team write-ups and code (added 2026-10-11; the first four are read from saved README snapshots in `references/online-snapshots/`):
- [prosperity4-leo-hawking-review](sources/prosperity4-leo-hawking-review.md): human-plus-AI workflow, round 0 probe (no queue), the limits of agent consensus.
- [prosperity4-heyman7913](sources/prosperity4-heyman7913.md): P4 19th; capacity reservation, signal fair, opening-price regimes, Mark 67 event study.
- [prosperity3-cmu-physics](sources/prosperity3-cmu-physics.md): P3 7th; a Lambda restart wiped trading state; sample data was live data; a fitted IV smile broke.
- [prosperity4-kayzerjali](sources/prosperity4-kayzerjali.md): an agent loop using the live result as the oracle; one measured backtest-versus-live gap.
- [algotrade2026-negative-eevee](sources/algotrade2026-negative-eevee.md): the AlgoTrade 2026 winners; a shared market; cross-exchange IOC arbitrage.
- [uchicago-2025-case2-humzah](sources/uchicago-2025-case2-humzah.md): a #1 file-upload entry that found the generator's 10-tick structure.
Other competitions and organisers' files:
- [algotrade2026-pitfa19](sources/algotrade2026-pitfa19.md): live WebSocket event; market-maker reverse engineering.
- [uchicago-trading-2026](sources/uchicago-trading-2026.md): shared live exchange; Case 2 is a file upload with a restricted library set.
- [qminers-hackathon-2025](sources/qminers-hackathon-2025.md): Qminers' earlier competition; stub, upload, hidden seasons.
Documents and articles:
- [timo-diehm-medium-article](sources/timo-diehm-medium-article.md): Frankfurt Hedgehogs' essay on questioning assumptions and understanding the environment; no tactics.
- [prosperity-wikis](sources/prosperity-wikis.md): IMC's own documentation (Notion) for Prosperity 2, 3 and 4: the bot interface, libraries, limits and time limit.
- [online-articles](sources/online-articles.md): Rigtorp, Databento, Hummingbot's Avellaneda–Stoikov guides, Optiver's explainers (read as summaries; no local copy).
Tools:
- [prosperity3-backtester-jmerle](sources/prosperity3-backtester-jmerle.md): the rules our engine matches; log-to-data converter.
- [prosperity2-backtester-jmerle](sources/prosperity2-backtester-jmerle.md): P2 data and limits.
- [prosperity4-backtester](sources/prosperity4-backtester.md): **the P4 data**; fork differences; default limit 50.
- [prosperity3-visualizer-jmerle](sources/prosperity3-visualizer-jmerle.md): the log format.
- [hftbacktest](sources/hftbacktest.md): queue models and fill docs.

## Gaps
Things the wiki does not cover yet, in rough order of value:
1. **Manual-round puzzles.** No page. Unread: Baguette Fromage `README.md:1105-1485`, Alpha Search `README.md:181-638`, Ryan Challman `README.md:147-255`, Frankfurt `README.md:786-876`. The Arena may have none.
2. **Cross-check against our engine.** No team's PnL claim is reproduced except Frankfurt's Resin and Kelp. Needs `--data p4` (`TODO.md`).
3. **Unread source parts** (listed per source page): Frankfurt `README.md:325-876`; most of DU `round5.py`; DTU round 1–3 bodies; AlgoTrade's API reference; the Prosperity wikis' FAQ, round pages and glossary; most of the Leo-Hawking, heyman7913 and CMU Physics READMEs; Negative Eevee's `runner.rs`, `state.rs`, `config.rs`.
4. **Sources not obtainable by the agent:** the Quant.SE queue-position thread (the fetch tool is blocked on that domain), exact copies of the queue and Avellaneda–Stoikov articles, books (Bouchaud et al. full text, an options text), and any organiser material. All tracked in [`MANUAL_TODO.md`](../../MANUAL_TODO.md); see also `references/SEARCH_LOG.md`.
5. **`literature_md/` is not in this wiki.** `TODO.md` has an item to turn it into one; reuse this schema. The Cartea et al. 2018 paper is cited from here, but only its imbalance definition (`ρ`) has been checked against the PDF.
6. **Ready Trader Go winning bots** and the Jane Street trading-challenge bots: none public that we found.
7. **A concept page on "reading the public data on day one"**: a checklist of the facts above to test on the Arena's first download (partly covered by [probing-the-environment](concepts/probing-the-environment.md)).

## Outside the wiki
- [`../README.md`](../README.md): the human-facing table of repos, reading order and cloning.
- [`../SEARCH_LOG.md`](../SEARCH_LOG.md): how sources were found, rejected, and dead ends.
- `../check_arena_site.py` and `../arena-site-snapshot.txt`: the Arena site's text and a diff tool.
