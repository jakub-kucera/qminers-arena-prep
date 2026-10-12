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
- [ ] **Material from earlier Qminers Quant Hackathons**, if a teammate or friend took part (2022 or 2024 problem
  statement, stub class, evaluation code). Save in `references/qminers-hackathon-older/`.
  - Why: `references/qminers-hackathon-2025/` is the only look at how Qminers builds a task; a second or third
    year shows what they reuse. A weak prior, since the Arena is a different task.
  - Done when: the files are saved, or the item is ticked as "nobody has any".
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
like the rest of `literature_md/`; say so if a book should stay out of git.

- [ ] **Bouchaud, Bonart, Donier & Gould, *Trades, Quotes and Prices* (Cambridge University Press, 2018)**: chapters
  4–7 (order-book statistics and queue dynamics, from p. 58), 11–13 (price impact) and 15–17 (the Kyle model, what
  sets the spread, whether market making pays, from p. 290), about 150 pages. Save as `trades-quotes-prices-chapters.pdf`.
  - Why: we have only a 47-page excerpt (front matter, contents, preface, chapter 1 and the start of chapter 2);
    the chapters we lack are the ones on queues and market making.
  - Done when: the chapters are converted and indexed in `literature_md/README.md`.
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
