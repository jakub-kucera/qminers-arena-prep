# On the day: what to find out

The organisers won't answer questions. Everything here has to come from their docs, the
playground, or a probe bot (see [Probes](#probes)). Settle the **first hour** list before writing
any strategy, because those answers change the code.

The tooling assumes IMC Prosperity's rules unless told otherwise. Each item says what we assume
now, and what to change if the Arena differs. **Write the answer in under each item as soon as
you know it**, with where it came from (docs, probe, email), so the whole team works from the
same facts.

## Splitting the first hour

Three tracks can run in parallel:
- **Checklist:** read the docs and fill in every answer they give.
- **Probes:** adapt `bots/template.py`'s ADAPTER into a probe bot and run it in the playground.
- **Data:** write the loader in `arena/formats/qminers.py`, so the backtester runs on their data as soon as possible. Then run `arena.diagnose` on it (see "What kind of market is each product?").

## Known so far

From the Arena site's own front-end code (arena.qminers.com is a JavaScript app, so its text, including the
official rules, is only in the bundle `assets/index-*.js`; read 2026-10-10; re-check with `references/check_arena_site.py`):
- 24 hours in person, 7–8 Nov 2026 at MFF UK: four rounds of 5 hours each. Teams of 2 to 4 university students.
- Python bots trading on a simulated limit-order-book exchange, through "a simple API". Qminers says it will "simulate a realistic exchange", mimicking a limit order book "without many real-world operational complexities".
- **Submission is a web portal, not a live connection.** Teams log in with an e-mailed one-time link. Each round you upload **a single `.py` file** (a size cap exists, value not in the code). The portal shows a table of submissions with status Waiting / Running / Completed / Failed, a score, downloadable result files and the strategy.
- **Submissions per round are capped** (the number is not in the code). The newest upload becomes your final one automatically, and you can mark an earlier one as final instead.
- **Evaluation:** a new upload is "queued for evaluation on the public backtest", and a button offers **"Download public backtest data"** for each round, so historical data is provided. Submissions have a type, PUBLIC or PRIVATE, and the detail page has an "Evaluated submission" link, which suggests a private run of a public submission. The final score is probably on hidden data.
- **Round weights:** the live leaderboard ("Market simulation rankings") shows Phase 1 to 4 at **10%, 20%, 30% and 40%**, plus a weighted total. The first round, the "forgiving market", is worth the least.
- **Technical Rules are published at the start** and explained in the opening briefing: permitted resources and tools, evaluation process, scoring, tie-breaks and technical limits. Read them before anything else.
- The final solution must be Python. Other languages, AI tools, literature and public online resources are allowed for preparing it, unless the Technical Rules say otherwise.
- Teams must work independently, and may not post questions about the task publicly or ask anyone outside the team during the event. (Reading public material is fine.)
- All leaderboards are preliminary. The organisers verify the validity and **reproducibility** of the top solutions and may rerun them. Keep the bot deterministic: seed any randomness and don't depend on wall-clock time.
- Prizes: 100,000 / 60,000 / 40,000 CZK for places 1 to 3. Bring your own internet connection or use eduroam.
- Still unknown: whether all teams share one market or each team trades alone (the leaderboard calls itself a market simulation, and one of the four skills listed is "game theory... anticipate competitors"), the bot interface, the data format, and the runtime limits.

## First hour: answers that change the code

- [ ] **How is the bot called?**
  - Find out: the entry point (class or function), its arguments, and what it must return. Is it called once per tick with a snapshot, or fed events as they happen? AlgoTrade 2026 was a websocket with a broadcast every 100 ms.
  - We assume: `Trader().run(state)` once per tick, returning `(orders, conversions, traderData)`.
  - What the Arena site implies: a single `.py` file uploaded to a portal and run by their simulator on a backtest, not a live socket client. That favours our file-and-adapter setup over an event-driven client. Read the Technical Rules for the entry point.
  - Weak prior only: Qminers' earlier Quant Hackathon (2022, 2024, 2025) was a different task, and this year is expected to be a big shift from those. There they gave out the server's own evaluation loop (the same code in 2024 and 2025, `references/wiki/sources/qminers-hackathon-2024.md`) and a stub `Model` class called per step with pandas DataFrames (see `references/README.md`), so keep the ADAPTER the only place that touches their types, and check whether pandas and numpy are allowed (probe 10).
  - If it does turn out to be event-driven, `references/` has a model for it: Optiver's Ready Trader Go kit (see the "Read online" list) uses callbacks for book updates and fills.
  - If different: write `arena/formats/qminers.py`, modelled on `prosperity.py`, and rewrite the template's ADAPTER. An event-driven API also needs engine work, so flag it at once.
- [ ] **Do unfilled orders rest between ticks?**
  - Find out: probe 1.
  - We assume: no. Everything unfilled is cancelled at the end of the tick.
  - If they rest: backtest with `--resting`. The template already handles both. But on a product that `arena.diagnose` notes as jumping, take only (`make_size` 0): resting quotes there get filled at stale prices. On P4 round 5 that turned 2–27k per product into losses of 0.7–2.4M (`IDEAS.md`).
- [ ] **Where does a new order join the queue?**
  - Find out: probe 11.
  - We assume (in `--resting`): at the back. The visible volume at your price is ahead of you, and you only move up when it shrinks. If the exchange's bots re-quote every tick, as Prosperity's did, you would reach the front much sooner.
  - If you reach the front sooner: `--resting` underestimates passive fills. Compare it with the per-tick mode, which has no queue.
  - If fills are split pro-rata (each resting order at the best gets a share of a trade in proportion to its size), the queue model doesn't apply: size buys priority, and `make_size` sets the share you get, not only your exposure. Then read `literature_md/pro-rata-microstructure/` (Guilbaud & Pham 2013, so far only mapped: `references/wiki/sources/pro-rata-microstructure.md`).
- [ ] **Does the book you see include your own orders?**
  - Find out: probe 2.
  - We assume: no. That's how the backtester shows it in every mode.
  - If it does: in the template's ADAPTER, subtract your open orders from the book before STRATEGY sees it. Otherwise `make` keeps stepping one tick ahead of its own quote.
- [ ] **How do orders, cancels and order types work?**
  - Find out: do orders get ids, and when do you learn them? Can you cancel by id, or cancel all? Are there IOC or market orders? Must orders carry an expiry (AlgoTrade's limit orders did)? Does shrinking an order keep its place in the queue?
  - Find out also: probes 5 and 12. Do your own orders trade with each other? What does cancelling an order that has already filled do: nothing, an error message, or an exception?
  - We assume: ids arrive next tick in `state.open_orders`, `Cancel(order_id)` cancels, `ioc=True` exists, and there's no amend. Your own orders never trade with each other, and cancelling a filled order does nothing.
  - If different: change the ADAPTER. EXECUTION's logic (keep a quote that hasn't moved, cancel the rest) carries over.
- [ ] **How are position limits enforced?**
  - Find out: probe 4. What's the limit per product? Do open orders count, or only the position? Is only the offending order rejected, or every order for the product? Are long and short limits the same (AlgoTrade had +2,000 / −200, plus a cash floor)?
  - We assume: Prosperity's rule. If all your buys, or all your sells, filling could breach the limit, every order for that product is cancelled. Limits are symmetric.
  - If different: update the limits table (`LIMITS` in the format module), the template's `Plan` room, and the engine's `_breaches` if backtests need to match.
  - In a shared market: another team can fill one of your orders between your decision and your next orders. If a breach cancels every order for the product, the whole tick's quotes go. Leaving a few lots of room under the limit avoids that.
- [ ] **Is the market shared with the other teams?**
  - Hints from the site, which point both ways: the leaderboard is called "Market simulation rankings", one of four listed skills is "game theory... anticipate competitors", and submissions come in PUBLIC and PRIVATE types. That fits a solo run on historical data for the public score and a shared simulation of the final files for the private one. It also fits two solo runs. Nothing says which.
  - Find out: do trades or book levels appear that the exchange's own bots couldn't explain? Are counterparties named?
  - Find out also: when several teams' orders arrive at the same tick, who goes first? Random, by time sent, or a fixed order?
  - We assume (with `--vs`): a random order, drawn again every tick.
  - If shared: tune with `--vs` (copies or variants of your bot) as well as alone, and prefer settings that hold up in both.
  - The one paper on competing market makers we have (`references/wiki/sources/competing-dealers.md`) has no price priority in its fill model, so use it only qualitatively: more makers, tighter spreads and lower profits. `--vs` is the better guide.
  - If the order is fixed, or by time sent: the bots that go first win most contested fills, so make the bot fast and cheap per call.
- [ ] **Where does state live between calls?**
  - Find out: probe 7. Do module and instance variables survive between calls? Is there a state string like `traderData`, and how big can it be?
  - We assume: only `traderData` survives. The validator's reload-every-tick check enforces this.
  - If more survives: nothing breaks. Keeping state in `traderData` still works.
- [ ] **What does the runtime allow?**
  - Find out: Python version, allowed imports (probe 10), time limit per call (probe 8), and what happens to prints (probe 9).
  - Then: run `arena.validate` with `--allow numpy` (etc.) and `--time-limit-ms` set to their limit.
- [ ] **What data can you backtest on?**
  - Find out: in which format are the files behind each round's "Download public backtest data" button (the site says they exist)? Does the data the private evaluation uses look the same (book depth, tick spacing)?
  - Then: write the loader in `arena/formats/qminers.py`, and run the template and validator on it before changing any strategy.
  - If no data is provided: have the probe bot print the full book and trades every tick, and build a dataset from the logs.
- [ ] **What kind of market is each product?**
  - Find out: once the loader reads the download, run `uv run python -m arena.diagnose <days> --format qminers --data <folder>`, and go through its notes with the table in `references/wiki/concepts/reading-the-data-on-day-one.md`.
  - We assume the Prosperity picture (P3 round 1):
    - small-tick books;
    - a noisy mid around a quiet wall mid;
    - market trades that don't move the wall mid;
    - market-making margins of 0.2–0.4 of the spread.
  - If different: the table says which template parameter or strategy each note changes. A thin margin, or trades that move the wall mid, means competitive or informed flow: quote wider and look for signals before tuning.
  - Look for a price grid and jumps that snap back on every product (P4 round 5 had both, on a product and day that the other days didn't show): run `uv run python -m experiments.p4_jumps --data <folder> --days <days> --jump-min <about half the jump>` (Prosperity format only until the Arena's loader exists; part 1 only for data other than P4). If any product's jumps reverse well above half the time, switch the template's `jump` mode on for every product, with `jump_min` half the jump size and `jump_edge` above half the spread: its gate keeps it off where jumps don't reverse (`IDEAS.md`, "Fading jumps that snap back").
  - For a product noted `reverts to a level`: compare its daily mean wall mid across the download's days. If they agree within a fraction of the intraday sd, set the template's `level` to their mean and grid `level_band` and `clear_edge` (about half the spread); otherwise start from `level: "day"`, which made 0.6 times as much on P4 (`IDEAS.md`, "Trading toward a known level").
- [ ] **Which backtest settings match the playground?**
  - Find out: run one bot (the template is fine) in the playground, then backtest it over the same period. Try each `--match-trades` mode, with and without `--resting`. Compare the number of passive fills, which fill rule decides most, and the PnL.
  - We assume: the per-tick mode with `--match-trades all`, which was the most optimistic on Prosperity data (81k, against 58k under `worse` and 28k under `none`).
  - Then: use the closest settings for every backtest and grid. If none is close, rank grid results by the most conservative mode.
- [ ] **Do our own trades move the market?**
  - Find out: probe 17. After a take that clears a level, does the next tick's book match the downloaded data (a replay), or does the price move and the level refill slowly (bots that react)?
  - We assume: a replay. Our engine shows the recorded book on the next tick, so our takes have no lasting impact, and on Prosperity data the bots' own trades left the wall mid where it was (`references/wiki/concepts/price-impact.md`).
  - If the market reacts: takes cost more than the backtest says. Take smaller pieces, expect the mid to move about the taken volume over twice the depth, and judge take-heavy variants on the portal rather than in the grid.

## Before the first submission

- [ ] **How do submissions work?** The exact deadline, how many submissions you get per round, the file size cap, and whether the public backtest score counts or only a private run.
  - From the site (see Known so far): single `.py` upload, a cap per round, newest upload becomes final unless you mark another, public and private evaluations.
  - So: run `arena.validate` before every upload. Never spend a submission on untested code. Before the deadline, check which submission is marked final.
  - Also find out what the leaderboard shows of other teams. In Qminers' 2024 hackathon it showed every team's score, runtime and RAM, and the winner read rivals' models from it. They also capped their own public score at a tenth of the model's until the last hours, so others wouldn't try harder (`references/wiki/sources/qminers-hackathon-2024.md`). If a public score here doesn't count toward the ranking, the same applies: don't show the full bot early. A scored round's result does count (10/20/30/40%), so never hold back there.
- [ ] **What does an exception do?** Probe 6. Is the tick skipped, the bot stopped, or the round lost? The template catches errors per product unless `STRICT` is set.
- [ ] **What are the price units?** Integer ticks? Tick size? Cents? The template rounds prices to `int`.
  - We assume: a tick of 1. The template hard-codes it: `make` steps to `best_bid + 1` / `best_ask - 1` and rounds with `floor`/`ceil`, and `Trader.run` sends `int(price)`. The Prosperity loader also reads prices with `int(float(...))` (every P2–P4 price is a whole number, checked 2026-10-13).
  - If the tick isn't 1: add a `tick` parameter and use it in `make` and the rounding, and keep prices as the exchange's type in the loader and the ADAPTER. With a tick of 0.01, `int(price)` would send prices off by up to a whole unit.
- [ ] **How is PnL scored?**
  - At which price are open positions valued: mid, last trade, or a settlement price?
  - Are positions liquidated at the end, and at what price? If badly, flatten before the close.
  - How are the rounds combined into a ranking? Is there a penalty for risk or drawdown?
  - If the ranking is relative, size the risk for the chance of placing, not for PnL. Qminers' 2024 winner simulated the other finalists to pick their stake, then halved it in the last round while far ahead and kept first (`references/wiki/concepts/risk-and-protecting-a-lead.md`). Before round 4 (40%), compute the lead in weighted points and decide in writing how much risk to keep.
- [ ] **Are there fees, rate limits or caps?** Fees or rebates per trade, the maximum number of orders per call or per second, and the maximum number of open orders. AlgoTrade closed your connection above 500 messages a second, and allowed 6,000 open orders.

## Every round

- [ ] **Re-test the ideas register:** go down `IDEAS.md` and re-run every row that fits this round's products, on the Arena's data. The results there come from Prosperity data and are priors only: an idea dropped there may work here, and a kept one may not. Write each Arena result into its row.
- [ ] **Products:** the new products, their position limits, and whether any are related, such as baskets, ETFs or options. AlgoTrade defined each ETF's fair value as the mean of its constituents.
  - For a basket or ETF with known weights: measure its spread's daily means and sds (`experiments/baskets.py` does it for Prosperity's). If the means agree across days, set `basket`, `level` (their mean) and a `level_band` of 0.5–1.5 sds, with `make_size` 0, and check by held-out days. A family whose prices sum to a constant is a basket with legs of weight −1.
  - For options: run `experiments/p4_vouchers.py` on them, with `--data`, `--underlying`, `--prefix` (the options' common name; the strike is the number at the end) and `--expiry` (days to expiry at each day's open). We assume P4's picture: implied vol flat within a day, and each option within half a spread of Black–Scholes at one vol. If so, give each option `follow` (its underlying) and `strike`, so it rides the underlying's view as extra room. If the residuals are larger than the spread, the smile is worth trading, and the template has nothing for that yet. P3's volcanic vouchers were like that (`IDEAS.md`); there, following the underlying still made money in-sample.
- [ ] **Other traders:** are there exchange bots, and are counterparties named? In Prosperity's round 5, the names gave away informed traders.
  - If named: run `uv run python -m experiments.counterparties` on the download (it reads the Prosperity format; point its `DATASETS` at the Arena's days once their loader exists). Follow a name with the template's `copy` mode only if it is right on nearly every trade on every day, not just on average: on P3 round 5, choosing names by their mean move lost 400k on held-out days, and choosing by hit rate found only Olivia (+54k). Use it only on products where the name's moves are large next to the spread and to what market making makes there (on Kelp, copying her lost). Our own fills against a name show it only in `own_trades`; the template reads both (`IDEAS.md`, "Following informed counterparties").
- [ ] **Is `wall_mid` still the market maker's price?** It takes the largest level on each side. In a shared market, another team's large quote can be the largest level and drag your fair value with it. Against a rival copy, this cost Kelp `make_edge=0` 4,920 under `--resting`. Against the teams' real P4 bots under `--resting`, it cost the template 374k on Osmium in one round. A rival's 40-lot bid 85 below fair outweighed the market maker's 23-lot wall, so on 36% of ticks the template's fair was 5+ off (`IDEAS.md`). Check that the walls have the stable size and spacing of an exchange bot. If teams' orders compete, pick out the market maker by its usual size instead: `fair: sized_mid`, with `wall_size` between the market maker's usual size and the other levels' (15 on Prosperity). Against the teams' bots it made +39k on Osmium in the round where `wall_mid` lost 377k.
- [ ] **Evaluation data:** is the round scored on the data you were given, or on fresh data? The site hints at a private evaluation next to the public backtest. If fresh, trust the grid's `nbhd` and `min day` measures over its best `pnl`, and read its held-out days. With only a few days and measures that disagree, the rehearsal took the best worst day. Check whether the download reuses earlier rounds' days, as Prosperity did: the grid flags it.
- [ ] **Extra information:** news, external prices, or conversions to another market.
- [ ] **Rule changes:** anything different from the previous round, such as limits, fees or matching.

## Probes

A throwaway bot can answer most of the first-hour list in one playground run. Have it print
everything it sees (book, open orders, fills, positions) every tick, and run one experiment
at a time:

1. **Resting:** at tick 1, bid well below the best bid. At tick 2, send nothing. If the order is still listed, or fills later, orders rest.
2. **Own orders in the book:** with that bid resting, check the book for a level at its price and size.
3. **Fill timing and price:** send a buy at the best ask. Is the fill reported in the same call, the next call, or later, and at which price?
4. **Limits:** send two buys that together exceed the limit by one. Is one rejected, both, or every order for the product? Is there an error message?
5. **Self-trade:** send a bid and an ask at the same price. Do they trade with each other?
6. **Exceptions:** raise an exception in one tick. Does the bot get called again?
7. **State:** set a module global and an instance attribute, then read them on the next call.
8. **Time limit:** sleep 50, 200 and 500 ms in different ticks. Note what happens at each.
9. **Prints:** print about 10 KB in one call. Where does it show up? Is it cut off?
10. **Imports:** inside `try`, import numpy, pandas and scipy, and print which ones loaded.
11. **Queue position:** join the best bid with a small order. Note the volume shown ahead of you, and how much trades at that price before you fill.
12. **Cancelling a filled order:** send a buy at the best ask, then cancel it by id on the next tick.
13. **What the score is marked to:** in the first tick buy one lot at the best ask and hold it. Compare the platform's PnL (or mark) over time with the mid, the volume-weighted mid and the wall-mid variants in `references/wiki/concepts/fair-value-and-wall-mid.md`. Linear Utility, Frankfurt and Baguette Fromage found the market maker's mid this way.
14. **Far quotes on an empty side:** when one side of the book is empty, quote a small order at increasing distances from the last fair value (for example 20, 50, 100). Note the distance at which it stops filling. Baguette Fromage and DU found hidden takers at about 100 (`references/wiki/concepts/hidden-takers-and-empty-sides.md`).
15. **Is the practice data part of the scored data?** Compare the first rows of the public backtest data with the first ticks of an evaluated run (timestamps, prices, trade sizes). In Prosperity 3 the website's sample was the first 1,000 timestamps of live day 1.
16. **Same trader, two oracles:** run one deterministic trader on the portal's public backtest and in our engine, and compare the fill lists. One team measured +2,415 locally against +436 live on the same window (`references/wiki/contradictions.md`, row 10).
17. **Own impact:** in a quiet product, take the whole best ask once, then send nothing for 20 ticks. Compare those ticks' books with the same timestamps in the downloaded data: identical books mean a replay; a moved wall or a slow refill means the market reacts to us.
