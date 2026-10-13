# Index of the references wiki

Read this first, then the pages it points to. Conventions, workflows and the lint are in [`SCHEMA.md`](SCHEMA.md); the history of changes is in [`log.md`](log.md). Pattern: Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (raw sources → wiki → schema). The raw sources are the clones in `references/<repo>/` and the papers and books in `literature_md/`; this wiki never edits them.

**If you only have a minute:** [`overview.md`](overview.md). **If you have a question:** find the concept below, read it, follow its citations. **If something looks wrong:** check the cited line, fix the page, add a `lint` entry to the log.

## Overview and open questions
- [overview.md](overview.md): what the Prosperity record teaches and what probably carries to the Arena.
- [contradictions.md](contradictions.md): disagreements between sources, README-versus-code mismatches, theory against the teams' practice (rows 12–16), open questions, each with what would settle it.

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
- [book-imbalance-and-micro-price](concepts/book-imbalance-and-micro-price.md): `ρ`, the weighted mid, Stoikov's micro-price and order-flow imbalance; strong only at 1-tick spreads, so test per product first.
- [optimal-quoting-models](concepts/optimal-quoting-models.md): Avellaneda–Stoikov, GLFT and Guéant; the closed form is our linear `skew` with coefficients from `σ`, `A`, `k`; cross-product skew.
- [probing-the-environment](concepts/probing-the-environment.md): experiments on the simulator before strategies: the PnL mark, bot tolerances, no-queue, sample data that is really live data.
- [reading-the-data-on-day-one](concepts/reading-the-data-on-day-one.md): `arena.diagnose`'s notes (tick regime, noise, slow reversion, drift, one-sided or informed flow, the market-making margin) mapped to strategy choices, with Prosperity examples.
- [price-impact](concepts/price-impact.md): instantaneous and permanent impact, the maker's `s/2 − R∞`, the shapes in the literature; on Prosperity data the bots' trades don't move the wall mid.
- [harder-rounds](concepts/harder-rounds.md): how the organisers could make rounds harder than Prosperity (reactive simulator, regime shifts, punishing bots, an agent-written field, fees and caps, speed), with tells and ranked prep.

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
- [qminers-hackathon-2024](sources/qminers-hackathon-2024.md): the 2024 winner's post-mortem; same evaluator, qualification then a reset 3-round final, risk chosen for the chance of winning.
Documents and articles:
- [timo-diehm-medium-article](sources/timo-diehm-medium-article.md): Frankfurt Hedgehogs' essay on questioning assumptions and understanding the environment; no tactics.
- [prosperity-wikis](sources/prosperity-wikis.md): IMC's own documentation (Notion) for Prosperity 2, 3 and 4: the bot interface, libraries, limits and time limit.
- [online-articles](sources/online-articles.md): Optiver's explainers (read as a summary; no local copy).
- [hummingbot-avellaneda-stoikov](sources/hummingbot-avellaneda-stoikov.md): Hummingbot's A–S guide and deep dive (snapshots); γ and κ backed out of a user's spread band.
Tools:
- [prosperity3-backtester-jmerle](sources/prosperity3-backtester-jmerle.md): the rules our engine matches; log-to-data converter.
- [prosperity2-backtester-jmerle](sources/prosperity2-backtester-jmerle.md): P2 data and limits.
- [prosperity4-backtester](sources/prosperity4-backtester.md): **the P4 data**; fork differences; default limit 50.
- [prosperity3-visualizer-jmerle](sources/prosperity3-visualizer-jmerle.md): the log format.
- [hftbacktest](sources/hftbacktest.md): queue models and fill docs.

## Literature (papers and books in `literature_md/`)
**Why the literature is in this wiki, and what for** (analysed 2026-10-11). The converted literature is about 680k words. Two books make up 68% of it (Harris 325k, Cartea, Jaimungal & Penalva 136k); the 15 papers average 12k words, so any one of them can be read whole. For the papers, *finding* the passage was never the problem, and a summary would add little to `grep`. What is expensive, and was being redone on every question, is:
- checking a formula against the PDF (Marker's LaTeX is OCR);
- translating a continuous-time model into our setting: discrete ticks, a hard position limit, bots instead of a Poisson crowd, and our parameter names;
- seeing where the theory and the teams' results disagree.

So a literature page stores those three things, and the theory sits on the same concept pages as the teams' evidence instead of in a second wiki. For the two books finding the passage *is* the problem: their source pages are chapter maps with PDF pages, and only the chapters our questions need are read.

**What it found:** [`overview.md`](overview.md), "What the literature adds". **How to add a document:** `SCHEMA.md`, "Add a document to the literature".

**How to use it:** start from the concept page; its literature citations carry the PDF page and say whether a formula was `checked` against the PDF (`SCHEMA.md`, rule 9). To see a page: `python3 literature_md/pdfpage.py <slug> <line>`. Only `checked` formulas should reach the code.

Documents with a source page (each says which formulas were checked against the PDF):
- [micro-price](sources/micro-price.md): Stoikov 2018; the micro-price as a Markov-chain table on (imbalance, spread); no information at a 4-tick spread.
- [queue-imbalance-predictor](sources/queue-imbalance-predictor.md): Gould & Bonart 2015; logistic test of `ρ` on the next mid move; strong at 1-tick spreads, 2–6% better than a coin flip otherwise.
- [order-book-signals](sources/order-book-signals.md): Cartea, Donnelly & Jaimungal 2018; quoting at the touch loses; post a side only if the half-spread beats the expected adverse move. OCR dropped the minus signs in its tables.
- [price-impact-of-book-events](sources/price-impact-of-book-events.md): Cont, Kukanov & Stoikov 2011; order-flow imbalance explains the same interval's move (R² 65%), not the next.
- [hft-in-a-limit-order-book](sources/hft-in-a-limit-order-book.md): Avellaneda & Stoikov 2008 (published version since 2026-10-13); reservation price and the spread `γσ²(T−t) + (2/γ)ln(1+γ/k)`; how it differs from the preprint.
- [dealing-with-inventory-risk](sources/dealing-with-inventory-risk.md): Guéant, Lehalle & Fernandez-Tapia 2013; hard inventory bound, stationary closed-form quotes (GLFT). OCR misplaces the square root in every closed form.
- [optimal-market-making](sources/optimal-market-making.md): Guéant 2017; any intensity, PnL-with-penalty objective, multi-asset skew through `Γ`.
- [pseudo-math](sources/pseudo-math.md): Bailey et al. 2014; the best of N null trials, MinBTL, and why memory makes the in-sample winner lose.
- [probability-of-backtest-overfitting](sources/probability-of-backtest-overfitting.md): Bailey et al. 2017; PBO and CSCV, the recipe for `arena.grid`.
- [deflated-sharpe-ratio](sources/deflated-sharpe-ratio.md): Bailey & López de Prado 2014; DSR, independent trials from correlated ones, the 37% stopping rule. OCR lost the inline math; read the PDF.
- [queue-position-valuation](sources/queue-position-valuation.md): Moallemi & Yuan 2017; order value = fill probability × (premium − adverse selection); front against back of the queue on ITCH data.
- [queue-reactive-model](sources/queue-reactive-model.md): Huang, Lehalle & Rosenbaum 2015; queue-size-dependent order flow as a simulator; uniform cancellation overstates fills.
- [rigtorp-queue-position](sources/rigtorp-queue-position.md): Rigtorp 2013; the queue estimate behind `ProbQueueModel`; `log(1 + x)` is not a back bias at every position.
- [quant-se-order-position](sources/quant-se-order-position.md): Quant.SE 2012 (Lehalle's answer); the risk-averse rule (ours) and the neutral one (`ProbQueueModel`).
- [databento-queue-position](sources/databento-queue-position.md): Databento 2025; one ES order against MBO data: cancels come from the back, `P(ahead) = x^{1/(1+k)}` (the page's formula is inverted).
- [mean-reverting-reference-price](sources/mean-reverting-reference-price.md): Ahuja et al. 2017; A–S with an OU price: constant quotes around the mean far from the end, a skew of γ × stationary variance between; on Osmium the skew half holds, the constant-quote half loses.
- [limit-and-market-orders](sources/limit-and-market-orders.md): Guilbaud & Pham 2012; best or one tick inside, or cross: a policy table over (inventory, spread in ticks); fill rates per state from data.
- [online-learning-market-making](sources/online-learning-market-making.md): Fernandez-Tapia 2016; learn the half-spread by stochastic gradient; the Brownian optimum `ψ*`; its numerical example contradicts its theorem.
- [competing-dealers](sources/competing-dealers.md): Yang et al. 2017; N dealers, no price priority; only qualitative for a shared market.
- [pro-rata-microstructure](sources/pro-rata-microstructure.md): Guilbaud & Pham 2013 (mapped); one-tick pro-rata book; only if the Arena matches pro-rata.
- [market-makers-dilemma](sources/market-makers-dilemma.md): Albers et al. 2025; a live experiment on the bitcoin perpetual: fill probability against post-fill return; naive and imbalance quoting lose at a one-tick spread.
- [negative-drift-of-a-fill](sources/negative-drift-of-a-fill.md): DeLise 2024; fills come with adverse moves; which fill rule matches a live simulator (ours has it in `--resting`).
- [stochastic-liquidity-demand](sources/stochastic-liquidity-demand.md): Capponi et al. 2021; discrete-time quoting with a closing cost and forecasts; simultaneous buy and sell fills are rare per tick here.
- [algorithmic-cooperation-mm](sources/algorithmic-cooperation-mm.md): Han 2022; Q-learning makers keep spreads wide without communicating; only if the market is shared.
- [marl-competition-no-collusion](sources/marl-competition-no-collusion.md): Wang, Ventre & Polukarov 2025; a rival trained to hurt you takes the flow by quoting tighter; self-interested makers did not collude.
- [etf-trade-flow-decomposition](sources/etf-trade-flow-decomposition.md): Petit, Cucuringu & Cartea 2025; trades classified by co-occurrence across an ETF and its constituents; a daily signal.
- [cross-asset-order-flow](sources/cross-asset-order-flow.md): Lee et al. 2025; constituents' order flow predicts the index a little; on Prosperity's baskets the legs don't lead.
- [dynamics-of-order-positions](sources/dynamics-of-order-positions.md): Guo, Ruan & Zhu 2015; fluid limit of the volume ahead of you; `Υ`, the general cancellation rule behind `ProbQueueModel`.
- [algorithmic-and-hft](sources/algorithmic-and-hft.md): Cartea, Jaimungal & Penalva (book), chapters 2, 10, 11, 12 read; chapter map with pages. Market making with a running penalty, optimal pairs-trading bands, Kyle λ typo.
- [harris-trading-and-exchanges](sources/harris-trading-and-exchanges.md): Harris (book, 2003 draft), chapters 10–14 and 17 read; chapter map. Dealers, spreads, quote matching, bluffing, arbitrage risks.
- [kelly-criterion](sources/kelly-criterion.md): Thorp 1997; `f* = edge/variance`, fractional Kelly keeps `c(2 − c)` of the growth, estimated edges run high. A scanned PDF with no text layer.
- [limit-order-books](sources/limit-order-books.md): Gould et al. 2013, survey; LOB vocabulary, priority rules, impact and stylized facts, mostly from pre-2010 data.
- [abides-simulator](sources/abides-simulator.md): Byrd et al. 2019; the open agent-based exchange simulator; per-agent seeded randomness, a configured (not measured) computation delay, persistent impact.
- [lob-simulation-realism](sources/lob-simulation-realism.md): Vyetrenko et al. 2019; the stylised facts a simulated book should show; the acceptance test for a day generator.
- [spoofing-abm](sources/spoofing-abm.md): Wang & Wellman 2017; mean-reverting fundamental, noisy observers with a Kalman update, ZI and book-reading HBL traders; a spoofer moves prices but adds little profit. OCR drops a δ in the variance step.
- [learning-market-maker](sources/learning-market-maker.md): Das 2005; Bayesian market maker over a hidden jumping value; loses when jumps aren't announced; the paper's no-order probabilities are wrong.
- [online-changepoint-detection](sources/online-changepoint-detection.md): Adams & MacKay 2007; exact online run-length posterior; the detector for a regime guard.
- [trades-quotes-prices](sources/trades-quotes-prices.md): Bouchaud et al. 2018 (book, full copy since 2026-10-13), chapters 1, 7, 11, 15–17 and 21 read; chapter map. When market making pays (`s/2` against long-run impact, slow and fast), the response function, the square-root law, Kyle, Glosten–Milgrom, MRR, queue value; measured: Prosperity is the zero-intelligence case where making is easy.

Not yet ingested: none; every document in `literature_md/README.md` has a source page. (`how-to-almost-win` is ingested as [timo-diehm-medium-article](sources/timo-diehm-medium-article.md).) The two books are partly read; their chapter maps say what is left.

## Gaps
Things the wiki does not cover yet, in rough order of value:
1. **Manual-round puzzles.** No page. Unread: Baguette Fromage `README.md:1105-1485`, Alpha Search `README.md:181-638`, Ryan Challman `README.md:147-255`, Frankfurt `README.md:786-876`. The Arena may have none.
2. **Cross-check against our engine.** Done for the P4 teams on 2026-10-13 ([log](log.md)): identical to `prosperity4btest` on 24 trader-days, and DTU's live results within 4% and 12–16%. Left: the P3 teams other than Frankfurt.
3. **Unread source parts** (listed per source page): Frankfurt `README.md:325-876`; most of DU `round5.py`; DTU round 1–3 bodies; AlgoTrade's API reference; the Prosperity wikis' FAQ, round pages and glossary; most of the Leo-Hawking, heyman7913 and CMU Physics READMEs; Negative Eevee's `runner.rs`, `state.rs`, `config.rs`.
4. **Sources not obtainable by the agent:** books (an options text) and any organiser material. (The Quant.SE thread, the queue articles and the published A–S arrived on 2026-10-13.) All tracked in [`MANUAL_TODO.md`](../../MANUAL_TODO.md); see also `references/SEARCH_LOG.md`.
5. **The three books are only partly read** (Harris, Cartea et al., and Bouchaud et al., now the full copy). The chapter maps on their source pages say where to look next.
6. **Ready Trader Go winning bots** and the Jane Street trading-challenge bots: none public that we found.
7. **Do the day-one notes predict what works?** [reading-the-data-on-day-one](concepts/reading-the-data-on-day-one.md) maps measurements to strategies from the sources. Not yet tested: whether an imbalance-adjusted fair helps on the `large-tick` products, and whether fading the level pays on the products that revert to one.

## Outside the wiki
- [`../README.md`](../README.md): the human-facing table of repos, reading order and cloning.
- [`../SEARCH_LOG.md`](../SEARCH_LOG.md): how sources were found, rejected, and dead ends.
- `../check_arena_site.py` and `../arena-site-snapshot.txt`: the Arena site's text and a diff tool.
