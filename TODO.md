# Prep to-do

Work left before the Arena (7–8 Nov 2026). Things to find out at the event itself are in
[`ON_THE_DAY.md`](ON_THE_DAY.md). Tick an item off when its "done when" holds, and add new
items as they come up.

## Research

- [ ] **Find more sources for `references/`.** Do a broad search for repos, write-ups and data that would help, beyond the six we have.
  - Leads:
    - top-team repos and write-ups from every Prosperity edition, including Prosperity 4 (2026) data if it exists
    - other university trading hackathons with a simulated exchange (AlgoTrade in earlier years, and anything Qminers has run or published before)
    - open-source backtesters that model queue position and latency, such as hftbacktest, to check our `--resting` queue model against
  - Done when: every source worth keeping has a row and a "where to look" entry in `references/README.md`, and repos are added to `references/clone.sh`.
- [ ] **Turn `literature_md/` into an LLM wiki.** This is Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern: instead of searching raw text (RAG, or our grep), an agent compiles the sources into a maintained, interlinked markdown wiki and answers from that.
  - **First, analyse the fit.** The literature is roughly 1,200 pages of OCR'd markdown, mostly two books. Would a wiki answer our questions better than searching the converted files? Write the conclusion at the top of the wiki's index.
  - **Then build it**, following the gist's three layers:
    - the converted documents as the read-only sources
    - wiki pages written by the agent: a summary per source, and concept pages
    - a schema file that defines the conventions and the ingest, query and lint workflows
  - **Concept pages to start with:** market making, inventory risk, micro-price, order-flow imbalance, queue position, price impact and Kelly sizing.
  - **Link each concept to our code.** For example: Avellaneda–Stoikov's reservation price against the template's `skew`, the micro-price as a `fair` option, and queue position against `--resting`.
  - **Formulas:** check every formula against the PDF page before it goes in, as `literature_md/README.md` requires, and cite the page.
  - Done when: the index, the source summaries, the concept pages and the schema exist. CLAUDE.md should point sessions to the wiki before the raw text.

## Tooling

- [ ] **Write a probe bot, `bots/probe.py`.** It runs the probes in `ON_THE_DAY.md` one after another and prints everything it sees each tick, so its logs double as a dataset when no historical data is provided. Write it in the Prosperity format, so only its ADAPTER changes on the day.
  - Done when: it runs in the backtester in both modes, and its output answers the probes there.
- [ ] **Add an optimistic queue option to `--resting`.** Today a new order always joins the back of the queue. Prosperity's bots re-quote every tick, so a real resting order there would often be at the front, and the truth probably lies between the two. Model both and backtest under each.
  - Done when: a flag such as `--queue back|front` exists, with tests, and the README's fill-assumption tables show both.
- [ ] **Let the template flatten before the close.** If the Arena liquidates open positions at a bad price, the bot should cut inventory near the end. Add a parameter now, so on the day it only needs a value.
  - Done when: a parameter like `flatten_from` (a timestamp) makes `clear` and `make` work the position to zero after it, with a test.

## Strategy

- [ ] **Explain Kelp's long drift.** Passive buys exceed passive sells (3,629 against 2,330 over round 1), Kelp sits at +50 about 10% of the time, and `skew` doesn't help. Find out whether fair value or quoting is biased, using the fill tables and product charts.
  - Done when: the cause is known, and the fix (or the reason not to fix it) is in the template or in a note here.
- [ ] **Try the literature's fair values and skew in the template.** Candidates: the micro-price, order-book imbalance (Cont et al.), and Avellaneda–Stoikov's inventory skew in place of our linear one. Compare them with `wall_mid` under `worse` fills, `--resting` and `--vs`.
  - Done when: each is a `fair` or skew option with a backtest result recorded here, kept or dropped.
- [ ] **Add multi-product strategies.** The later rounds of both Prosperity editions, and AlgoTrade's ETFs, priced products against each other. The template trades every product on its own, so add a cross-product hook to STRATEGY.
  - Then build a spread module: basket against components, z-score entries and exits, and hedging within the limits. Practise on Prosperity 3 round 2 (picnic baskets) and Prosperity 2 round 3 (gift basket).
  - Done when: the module trades a basket spread profitably on both datasets, under `worse` fills as well as `all`.
- [ ] **Prepare the other later-round mechanics:**
  - options: implied volatility and delta hedging, on Prosperity 3 round 3's volcanic vouchers and Prosperity 2 round 4's coconut coupons
  - mean reversion: Squid Ink
  - counterparty names: Prosperity round 5, to follow the traders who know something
  - Done when: each has a sketch that backtests, even if rough, so none starts from nothing on the day.

## Rehearsal and setup

- [ ] **Run a mock round in the week of 26 Oct.** One teammate prepares data in a format the others haven't seen, with a stated bot API. The rest go from nothing to a validated submission in 5 hours, working through `ON_THE_DAY.md`.
  - Done when: the round is done, and whatever was slow or confusing is fixed in the tooling or the checklist.
- [ ] **Set up every teammate's laptop by 31 Oct.** Each needs `uv sync`, `references/clone.sh` (2 GB, so not on the venue wifi), a passing `uv run pytest`, and the converted literature. Agree who takes which first-hour track in `ON_THE_DAY.md`, and who submits.
  - Done when: everyone has run the template backtest on their own machine.
