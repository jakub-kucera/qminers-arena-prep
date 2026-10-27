# Manual to-do: things only a person can obtain

Items the agent cannot get itself: documents only the team has, pages its fetch tool is blocked from,
and books or papers that need a library or a purchase. Everything else is in `TODO.md`.

**How to hand something over:** save it where the item says, then tell the agent. It ingests the file
following `references/wiki/SCHEMA.md` (a source page, updates to the concept pages it touches, a `log.md`
entry, `python3 references/wiki/lint.py`), writes what it found, and ticks the item here.
**Never save one-time login links, passwords or other people's personal data.** Strip them first.
Event: 7–8 Nov 2026. Section A is worth doing as soon as anything arrives; the rest is best done before about 1 Nov.

## Now: rotate the neuralwatt API key

- [ ] **Rotate the neuralwatt key.** `ce2aa7b` committed `.env` with `NEURALWATT_API_KEY` in it; the file is untracked and
  in `.gitignore` since 2026-10-28 (the fourth audit's R1), but the old key stays in the history of every clone.
  - How: make a new key in the neuralwatt dashboard, revoke the old one, put the new one in `.env` (never committed) or
    the shell's environment. Rewriting the history (`git filter-repo`, every clone re-cloned) is not needed once the
    old key is revoked.
  - Done when: the key in the history no longer works.

## A. Arena-specific material (highest value)

- [ ] **Every organiser e-mail, document or link the team has received**: registration confirmation, schedule,
  rules, FAQ, any technical note. Save as PDF or text in `references/arena-docs/` (ignored by git).
  - Why: it is the only primary evidence about the Arena. The site's own text is already tracked by
    `references/check_arena_site.py`; this is everything else.
  - Done when: each file is in the folder and `ON_THE_DAY.md` "Known so far" and the item answers it settles
    cite the file as their source.
  - **Done in part (2026-10-23):** the e-mail of 7 Oct (the schedule, the playground, the on-site and
    sleeping rules) is the first message of `references/algo_trade_arena_conversation.json`, which is
    committed, and its facts are in `ON_THE_DAY.md`, "Known so far". Left: the last e-mail, due about
    a week before the event (around 31 Oct), with travel, parking and the final instructions.
- [ ] **Anything the portal shows before the event, and on each submission**: a playground or practice round,
  an example bot, the "Download public backtest data" button, the result-file format, error messages. Save
  pages as PDF, data and result files unchanged, in `references/arena-docs/portal/`.
  - **The public site was read in full again on 2026-10-26 and is still the 23 Oct build**
    (`index-E19sYWMS.js`, SHA-256 `45dacdbc…a4bc`, Last-Modified 23 Oct 17:41 GMT): no new pages, no playground,
    no example bot, no API documentation and no extra endpoint; the old bundle is gone and there is no Wayback
    copy. The remaining website material is behind our team login, below.
  - **On the first upload (2026-10-26):** save the submission page and its `resultFileZip` unchanged, list
    the ZIP's contents, and compare any fills or orders in it with `arena.backtest --out` on the same data.
    That is the portal's only detailed record of the public run and the best calibration of our engine.
  - **After each deadline:** save the leaderboard's JSON (the page's own response for `rounds/<id>/leaderboard`,
    from the browser's Network tab) and the PRIVATE evaluation's `resultFileZip`; both are our own team's pages.
  - Why: it decides the bot interface, data format and limits (`ON_THE_DAY.md`, "First hour"), and the ZIPs
    are the only per-fill detail the portal gives. Note that the mock round in `TODO.md` ("Run a mock round
    before the event.") is **our own rehearsal**; we do not know that the organisers offer one.
  - Done when: the files are saved and the loader work (`python/arena/formats/qminers.py`, `ON_THE_DAY.md`) has what it needs, or the
    item is ticked as "nothing available before the event".
- [x] **Material from earlier Qminers Quant Hackathons**, if a teammate or friend took part (2022 or 2024 problem
  statement, stub class, evaluation code). Save in `references/qminers-hackathon-older/`.
  - Why: `references/qminers-hackathon-2025/` is the only look at how Qminers builds a task; a second or third
    year shows what they reuse. A weak prior, since the Arena is a different task.
  - Done when: the files are saved, or the item is ticked as "nobody has any".
  - Done 2026-10-13: the user's private 2025 repo (`jakub-kucera/QQH-2025`) had the 2024 winner's repo on a branch; its public original is pinned in `references/clone.sh` as `qminers-hackathon-2024/` (organisers' README, problem statement and evaluation loop, plus the post-mortem) and ingested as `references/wiki/sources/qminers-hackathon-2024.md`. The repo's other branches hold the organisers' 2025 files, which we already had, and the team's own models. No 2022 material.
- [ ] **(Optional) Organiser posts from the Prosperity Discord**, if anyone on the team has access: the announcements
  and the clarifications about data generation, order matching and hints. Copy the text into
  `references/prosperity-discord/`.
  - Why: teams cite these (for example the admins' statement that 20% of the bots' orders were removed at random,
    `references/wiki/sources/prosperity4-du-trading.md`) and the agent cannot see Discord.
  - Done when: the text is saved, or the item is ticked as "no access".

- [ ] **Zoo bots from Gemini and ChatGPT** (`TODO.md`, "(a, part 2)"). The agent can't reach other providers' models.
  - What: Gemini 4 and an older Gemini, and ChatGPT models current and older (GPT-4o, o3, GPT-4.1, ...), each on the `baseline` prompt; the strongest of each on all four prompts.
  - How: `python/bots/zoo/README.md`, "Running a model cleanly". Save each reply unchanged in `python/bots/zoo/gemini/` or `python/bots/zoo/chatgpt/`, add a row to the README's table.
  - Done when: the files are saved; the agent then runs `uv run python -m experiments.zoo` and records the results.

## B. Free web pages the agent cannot read exactly

Open each page in a browser and print it to PDF into `literature_raw/`, with the suggested name. The agent then
registers it in `literature_md/convert.sh` and converts it. All links returned HTTP 200 on 2026-10-11 except Quant.SE.

- [x] **Quant.SE: "How do we estimate position of our order in order book"**:
  <https://quant.stackexchange.com/questions/3782/how-do-we-estimate-position-of-our-order-in-order-book>
  as `quant-se-order-position.pdf`. Blocked for the agent's tool (403).
  - Done when: the PDF is converted and cited in `references/wiki/concepts/queue-position-and-fills.md`.
- [x] **Rigtorp, "Estimating order queue position"**: <https://rigtorp.se/2013/06/08/estimating-order-queue-position.html>
  as `rigtorp-queue-position.pdf`.
- [x] **Databento, "Getting queue position from L2 and order book data"**:
  <https://databento.com/blog/getting-queue-position-from-l2-and-order-book-data> as `databento-queue-position.pdf`.
  - Why for both: the agent has only a summary, and the queue-model TODO (`--queue back|prob|front`) needs the exact formula.
  - Done when: both are converted and `references/wiki/sources/online-articles.md` cites them by line.
  - Done 2026-10-13, with the Quant.SE thread: all three printed by the user, converted (`literature_md/rigtorp-queue-position/`, `databento-queue-position/`, `quant-se-order-position/`) and given their own source pages, which the queue concept page cites by line. Databento's tutorial was rendered with headless Chrome into `references/online-snapshots/databento-queue-position-tutorial.md`.
- [x] **Hummingbot Avellaneda–Stoikov guide and technical deep dive**:
  <https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/> and
  <https://hummingbot.org/blog/technical-deep-dive-into-the-avellaneda--stoikov-strategy/> as `hummingbot-as-guide.pdf`
  and `hummingbot-as-deep-dive.pdf`.
  - Why: the guide's formulas are images, so the agent's summary of them is unreliable.
  - Done when: the PDFs are converted and the formulas checked against `literature_md/hft-in-a-limit-order-book/`.
  - Done 2026-10-13 by the agent: the pages are static HTML, saved as text snapshots (`references/online-snapshots/hummingbot-as-guide.md`, `hummingbot-as-deep-dive.md`; Marker could not read their dark-mode printouts). The guide's image formulas were read on headless-Chrome printouts. Both formulas match the published A–S; see `references/wiki/sources/hummingbot-avellaneda-stoikov.md`.
- [ ] **(Only if you expect options) Optiver primers**: <https://www.optiver.com/insights/explainers/options-pricing/>,
  <https://www.optiver.com/insights/explainers/option-greeks/>, <https://www.optiver.com/insights/explainers/options-volatility/>,
  and <https://www.optiver.com/insights/explainers/orders-and-the-order-book/> as `optiver-<topic>.pdf`.
  - Why: `literature_md/` has no options material; these are a free, short primer.
  - Done when: converted, or ticked as "no options expected".

- [ ] **LOBSTER's sample files: one NASDAQ stock, one day, level 5 or deeper** (2026-10-27; `TODO.md`, "The edge plan"). Real books with real informed flow, to see what `arena.diagnose`'s "trades move the wall mid" note and negative markouts look like on a real market, next to ABIDES's simulated one.
  - Why a person: lobsterdata.com no longer serves its free samples by a public link (2026-10-27: the old `/info/sample/...zip` paths return the site's app page). It sends a time-limited download link after a request on the site (an account, or for the book samples a purchase proof).
  - Save: the unzipped `*_message_*.csv` and `*_orderbook_*.csv` files in `data/lobster/raw/` (gitignored; the sample's terms are LOBSTER's, so nothing is committed).
  - Done when: `uv run python -m experiments.lobster_days data/lobster/raw` has converted them, and `arena.diagnose`, `experiments.quote_markouts` and the shuffle test on `--data data/lobster` are in `IDEAS.md` beside the ABIDES row.

## C. Books (library access or purchase; use legal copies)

Save scans or ebooks of the chapters named, as `literature_raw/<short-name>.pdf`. The converted markdown is committed
like the rest of `literature_md/`; say so if a book should stay out of git. The agent then follows the workflow
"Add a document to the literature" in `references/wiki/SCHEMA.md` (a chapter map, then only the chapters a question needs).

- [x] **Bouchaud, Bonart, Donier & Gould, *Trades, Quotes and Prices: Financial Markets Under the Microscope*
  (Cambridge University Press, 2018), the full book** (about 460 pages). Save it as `trades_quotes_prices.pdf`, replacing
  the excerpt, so it keeps the slug `trades-quotes-prices`.
  - Why: of all the documents in `literature_raw/`, this is the only incomplete one (checked 2026-10-13). We have a
    47-page excerpt: front matter, contents, preface, chapter 1 and chapter 2 up to section 2.1.4. The chapters we lack
    are the ones we need most: 4–7 (order-book statistics, queue dynamics), 11–14 (price impact), 15–17 (the Kyle
    model, what sets the spread, whether market making pays).
  - Done when: the full book replaces the excerpt and the wiki is rebuilt from it, following "Replace a document with a
    fuller copy" in `references/wiki/SCHEMA.md`: a new chapter map, chapters 11, 16 and 17 read first, every existing
    citation re-pointed to the full copy's lines and pages, and `python3 references/wiki/lint.py --pages` clean.
  - Done 2026-10-13: saved as `trades_quotes_prices_full.pdf` (the only file matching the slug's prefix), converted, and the source page rebuilt with a chapter map; every earlier citation re-pointed and `lint.py --pages` clean.
- [ ] **(Low priority) Final versions of four documents we have as drafts or preprints.** All four are complete in
  content (checked 2026-10-13); only the version differs. Save each under its current file name in `literature_raw/`.
  - [x] Avellaneda & Stoikov, "High-frequency trading in a limit order book", *Quantitative Finance* 8(3), 2008. Done
    2026-10-13: the user saved the published version; it replaced the preprint and the wiki was rebuilt from it. It has
    the `γσ²(T−t)` term. **It was the
    one worth getting:** our copy is the 24 April 2006 preprint, whose spread formula has no `γσ²(T−t)` term, while
    Hummingbot's version has one (`references/wiki/sources/hft-in-a-limit-order-book.md`, Traps). The published
    version would settle which formula the paper ends with.
  - Cont, Kukanov & Stoikov, "The price impact of order book events", *Journal of Financial Econometrics* 12(1), 2014
    (ours: the March 2011 working paper).
  - Cartea, Donnelly & Jaimungal, "Enhancing trading strategies with order book signals", *Applied Mathematical
    Finance* 25(1), 2018 (ours: the accepted manuscript).
  - Harris, *Trading and Exchanges: Market Microstructure for Practitioners* (Oxford University Press, 2003), the
    printed edition (ours: a 2003 draft with all 29 chapters). Only if a page number must match the printed book:
    swapping it in means re-citing every Harris line in the wiki.
  - Done when: each is obtained and the wiki rebuilt from it as for the full Bouchaud book, or ticked as "the
    version we have is enough".
- [ ] **(Only if you expect options) one options text**: Natenberg, *Option Volatility and Pricing* (2nd ed.), or Sinclair,
  *Option Trading*, or Hull, *Options, Futures and Other Derivatives* (probably in your library). Only the Greeks and
  volatility chapters, as `options-chapters.pdf`.
  - Done when: converted, or ticked as "no options expected".
- [ ] **(Low priority, mostly overlaps what we have)** Lehalle & Laruelle, *Market Microstructure in Practice*; Guéant,
  *The Financial Mathematics of Market Liquidity*; López de Prado, *Advances in Financial Machine Learning* (backtesting
  chapters only); Chan, *Algorithmic Trading*; Vidyamurthy, *Pairs Trading* (only if baskets matter).
  - Done when: each is obtained, or the item is ticked as "skipped".

## D. Papers from the 2026-10-13 triage (`references/SEARCH_LOG.md`)

The user is getting these through the library. Save each in `literature_raw/` under the name given; the agent registers it in
`literature_md/convert.sh`, converts it and writes its source page.

- [x] *Limit order trading with a mean reverting reference price* (Risk and Decision Analysis, 2017) as `mean-reverting-reference-price.pdf`. **First:** it bears on `contradictions.md` row 1, a skew on a pegged product.
- [x] Guilbaud & Pham, *Optimal high-frequency trading with limit and market orders* (Quantitative Finance, 2013) as `limit-and-market-orders.pdf`.
- [x] Fernandez-Tapia, *High-frequency trading meets online learning* (Market Microstructure and Liquidity, 2016) as `online-learning-market-making.pdf`.
- [x] (Only if teams share one market) *On optimal pricing model for multiple dealers in a competitive market* (Computational Economics, 2017) as `competing-dealers.pdf`.
- [x] (Only if the Arena matches pro-rata) Guilbaud & Pham, *Optimal high-frequency trading in a pro rata microstructure with predictive information* (Mathematical Finance, 2013) as `pro-rata-microstructure.pdf`.
  - Done when (each): converted, with a source page, or ticked as "not needed" once the Arena's rules are known.
  - Done 2026-10-13: all five saved (published versions), converted and given source pages; the first three read, the conditional two mapped. The mean-reverting paper's prediction was tested on P4 Osmium (`IDEAS.md`, "Skew on a pegged product").

- [x] (Only if the Arena has ETF or basket products) Two ICAIF 2025 papers on order flow between an ETF or index and its constituents, only on the ACM Digital Library: *Data-driven trade flow decomposition for exchange-traded funds and their constituents* as `etf-trade-flow-decomposition.pdf`, and *From constituents to index: interpretable price movement prediction via cross-asset order flow* as `cross-asset-order-flow.pdf` (`references/SEARCH_LOG.md`, the ICAIF table).
  - Done when: converted with a source page, or ticked as "no baskets in the Arena".
  - Done 2026-10-13: the user saved both (open access) and Wang et al.'s MARL paper; all three converted with source pages. Legs leading the basket was tested on P3: they don't.

## E. ICAIF 2020–2021 papers (the local proceedings for those years list only titles)

Save in `literature_raw/` under the name given (ACM Digital Library; several also on arXiv or SSRN). The 2022–2024 picks are already inside `ICAIF_<year>_proceedings.pdf`; the agent can split them out itself. See `references/SEARCH_LOG.md`, the ICAIF 2020–2024 table.

- [x] Xiong & Cont, *Interactions of market making algorithms: a study on perceived collusion* (ICAIF 2021) as `market-making-perceived-collusion.pdf`.
- [x] Vyetrenko et al., *Get real: realism metrics for robust limit order book market simulations* (ICAIF 2020) as `realism-metrics-lob-simulation.pdf`.
  - Done 2026-10-14 by the agent: the arXiv version (1912.04941) is `literature_md/lob-simulation-realism/`, with a source page.
- [x] **(Wanted since 2026-10-14)** Wang, Hoang & Wellman, *Learning-based trading strategies in the face of market manipulation* (ICAIF 2020) as `trading-under-manipulation.pdf`. Backs D3 in `references/wiki/concepts/harder-rounds.md`: how book-reading traders can be made robust to a spoofer, next to `spoofing-abm`.
  - Done 2026-10-14: saved by the user, converted (`literature_md/trading-under-manipulation/`), with a source page.
- [x] (Maybe) Zhao & Linetsky, *High frequency automated market making algorithms with adverse selection risk control via reinforcement learning* (ICAIF 2021) as `mm-adverse-selection-rl.pdf`.
- [x] (Maybe) Mahfouz, Balch, Veloso & Mandic, *Learning to classify and imitate trading agents in continuous double auction markets* (ICAIF 2021) as `classify-trading-agents.pdf`.
- [x] (Only with ETF products) Shearer, Byrd, Balch & Wellman, *Stability effects of arbitrage in exchange traded funds: an agent-based model* (ICAIF 2021) as `etf-arbitrage-abm.pdf`.
  - Done 2026-10-14: the user's `_v2` file is the right paper; converted (`literature_md/etf-arbitrage-abm/`) with a source page.
  - Done when (each): converted with a source page, or ticked as "not needed".
  - Done 2026-10-14 for Xiong & Cont, Zhao & Linetsky and Mahfouz et al.: saved by the user under their titles, converted and ingested together with the 2022–2024 picks (order stacking, decomposed OFI, scaled beta, collective liquidity taking). **Still missing:** the ETF-arbitrage paper; the file "Stability Effects of Arbitrage in Exchange Traded Funds- An Agent-Based Model.pdf" is a byte-identical copy of "Detecting Collective Liquidity Taking Distributions.pdf". The user's "Get Real…", "The Effect of Liquidity on the Spoofability…" copies duplicate papers another session had already ingested (`lob-simulation-realism`, `spoofability-and-liquidity`) and were not converted again.

## F. Spoofing and manipulation (harder-round D2 and D3)

The free ones (Tao et al. on arXiv, the two Cartea et al. papers on SSRN, Li et al. on arXiv, Goldblum et al. on arXiv, Wang & Wellman on ijcai.org) the agent fetches itself on request. Only these need a person (`references/SEARCH_LOG.md`, the spoofing table):

- [x] Byrd, *The accidental pump and dump: when agentic AI meets autonomous trading* (ICAIF 2025, ACM) as `accidental-pump-and-dump.pdf`. Raised from maybe on 2026-10-14: it is one of two papers for the LLM zoo (D2).
- [x] (Maybe) Lee, Eom & Park, *Microstructure-based manipulation: strategic behavior and performance of spoofing traders* (Journal of Financial Markets, 2013) as `spoofing-traders-empirical.pdf`.
  - Done when (each): converted with a source page, or ticked as "not needed".
  - 2026-10-14: everything else on the spoofing and harder-round lists was fetched or split out by the agent and ingested (12 papers, `references/SEARCH_LOG.md`). Lee et al.'s spoof criterion is known second-hand (`references/wiki/sources/optimal-spoofing.md`), so that paper is optional now.

## G. Overfitting, second pass (`TODO_DONE.md`, "Second pass on overfitting")

Five papers were fetched and ingested by the agent on 2026-10-19 (Hansen's SPA, Romano–Wolf, Harvey & Liu, Dwork et al., Carr & López de Prado). These need a person:

- [ ] **White, *A Reality Check for Data Snooping* (Econometrica 68(5), 2000)** as `literature_raw/reality-check.pdf`. The two free copies the search found (a course page at users.ssc.wisc.edu, a mirror at par.cse.nsysu.edu.tw) did not connect from the agent's network. Lower priority: Hansen's SPA paper restates its test.
- [ ] **López de Prado, *Advances in Financial Machine Learning* (Wiley, 2018), chapters 7 (cross-validation: purging and embargo), 11 (the dangers of backtesting) and 12 (combinatorial purged CV)** as `literature_raw/afml-ch7-11-12.pdf`. Our CSCV blocks touch and positions carry across their edges; these chapters say how wide a gap to leave.
- [ ] **Arian, Norouzi & Seco, *Backtest overfitting in the machine learning era* (Knowledge-Based Systems 305, 2024; SSRN 4778909)** as `literature_raw/backtest-overfitting-ml-era.pdf`. It compares CPCV, walk-forward and k-fold on synthetic markets, the closest test of which method to trust.
- [ ] **Masters, *Testing and Tuning Market Trading Systems* (Apress, 2018), the chapters on permutation tests** as `literature_raw/masters-permutation.pdf`. `arena.grid --permute` is our adaptation of his test without the book (2026-10-19): how he permutes, which statistic he ranks and how he handles a reference strategy should be checked against it.
- [ ] **(Optional) Politis & Romano, *The stationary bootstrap* (JASA 89, 1994)** as `literature_raw/stationary-bootstrap.pdf`, for the block length. Hansen's paper gives the algorithm we use.
  - Done when (each): converted with a source page by the agent, or ticked as "not needed".

## Not on this list

The agent can download these free papers itself on request, so there is nothing for a person to do: Gatheral & Jacquier (SVI),
Avellaneda & Lee, Fodra & Labadie, Lipton et al., Leung & Li. The agent does not look for pirated copies of books.
For why each source is on or off this list, see `references/SEARCH_LOG.md` ("Books and articles") and the "Gaps" section of
`references/wiki/index.md`.
