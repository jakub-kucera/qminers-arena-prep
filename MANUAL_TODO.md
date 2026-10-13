# Manual to-do: things only a person can obtain

Items the agent cannot get itself: documents only the team has, pages its fetch tool is blocked from,
and books or papers that need a library or a purchase. Everything else is in `TODO.md`.

**How to hand something over:** save it where the item says, then tell the agent. It ingests the file
following `references/wiki/SCHEMA.md` (a source page, updates to the concept pages it touches, a `log.md`
entry, `python3 references/wiki/lint.py`), writes what it found, and ticks the item here.
**Never save one-time login links, passwords or other people's personal data.** Strip them first.
Event: 7–8 Nov 2026. Section A is worth doing as soon as anything arrives; the rest is best done before about 1 Nov.

## A. Arena-specific material (highest value)

- [ ] **Every organiser e-mail, document or link the team has received**: registration confirmation, schedule,
  rules, FAQ, any technical note. Save as PDF or text in `references/arena-docs/` (ignored by git).
  - Why: it is the only primary evidence about the Arena. The site's own text is already tracked by
    `references/check_arena_site.py`; this is everything else.
  - Done when: each file is in the folder and `ON_THE_DAY.md` "Known so far" and the item answers it settles
    cite the file as their source.
- [ ] **Anything the portal shows before the event**: a playground or practice round, an example bot, the
  "Download public backtest data" button, the result-file format, error messages. Save pages as PDF, data
  and result files unchanged, in `references/arena-docs/portal/`.
  - Why: it decides the bot interface, data format and limits (`ON_THE_DAY.md`, "First hour"). Note that the
    "mock round in the week of 26 Oct" in `TODO.md` is **our own rehearsal**; we do not know that the
    organisers offer one.
  - Done when: the files are saved and the loader work (`arena/formats/qminers.py`, `ON_THE_DAY.md`) has what it needs, or the
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

## B. Free web pages the agent cannot read exactly

Open each page in a browser and print it to PDF into `literature_raw/`, with the suggested name. The agent then
registers it in `literature_md/convert.sh` and converts it. All links returned HTTP 200 on 2026-10-11 except Quant.SE.

- [ ] **Quant.SE: "How do we estimate position of our order in order book"**:
  <https://quant.stackexchange.com/questions/3782/how-do-we-estimate-position-of-our-order-in-order-book>
  as `quant-se-order-position.pdf`. Blocked for the agent's tool (403).
  - Done when: the PDF is converted and cited in `references/wiki/concepts/queue-position-and-fills.md`.
- [ ] **Rigtorp, "Estimating order queue position"**: <https://rigtorp.se/2013/06/08/estimating-order-queue-position.html>
  as `rigtorp-queue-position.pdf`.
- [ ] **Databento, "Getting queue position from L2 and order book data"**:
  <https://databento.com/blog/getting-queue-position-from-l2-and-order-book-data> as `databento-queue-position.pdf`.
  - Why for both: the agent has only a summary, and the queue-model TODO (`--queue back|prob|front`) needs the exact formula.
  - Done when: both are converted and `references/wiki/sources/online-articles.md` cites them by line.
- [ ] **Hummingbot Avellaneda–Stoikov guide and technical deep dive**:
  <https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/> and
  <https://hummingbot.org/blog/technical-deep-dive-into-the-avellaneda--stoikov-strategy/> as `hummingbot-as-guide.pdf`
  and `hummingbot-as-deep-dive.pdf`.
  - Why: the guide's formulas are images, so the agent's summary of them is unreliable.
  - Done when: the PDFs are converted and the formulas checked against `literature_md/hft-in-a-limit-order-book/`.
- [ ] **(Only if you expect options) Optiver primers**: <https://www.optiver.com/insights/explainers/options-pricing/>,
  <https://www.optiver.com/insights/explainers/option-greeks/>, <https://www.optiver.com/insights/explainers/options-volatility/>,
  and <https://www.optiver.com/insights/explainers/orders-and-the-order-book/> as `optiver-<topic>.pdf`.
  - Why: `literature_md/` has no options material; these are a free, short primer.
  - Done when: converted, or ticked as "no options expected".

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
  - Avellaneda & Stoikov, "High-frequency trading in a limit order book", *Quantitative Finance* 8(3), 2008. **The
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

## Not on this list

The agent can download these free papers itself on request, so there is nothing for a person to do: Gatheral & Jacquier (SVI),
Avellaneda & Lee, Fodra & Labadie, Lipton et al., Leung & Li. The agent does not look for pirated copies of books.
For why each source is on or off this list, see `references/SEARCH_LOG.md` ("Books and articles") and the "Gaps" section of
`references/wiki/index.md`.
