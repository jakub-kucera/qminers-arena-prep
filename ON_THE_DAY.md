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
- **Probes:** rewrite `bots/probe.py`'s ADAPTER for their API, set `PRODUCT` and `LIMIT`, and run it in the playground (see "Probes" below).
- **Data:** write the loader in `arena/formats/qminers.py`, so the backtester runs on their data as soon as possible: follow "The format swap, step by step" below. Then run `arena.diagnose` on it (see "What kind of market is each product?").

## The format swap, step by step

Practised on the drill format (2026-10-17, `arena/formats/drill.py`, `bots/drill/template.py`), which differs from Prosperity's in every way we could think of. The plug-in took about 300 lines and the bot's ADAPTER about 100. Running the tools on it found four Prosperity habits, now fixed; the steps below avoid the rest.

1. **Copy `arena/formats/drill.py` to `qminers.py`** and register it in `FORMATS`. Set `RESTING = True` if their orders rest until cancelled.
2. **The loader** fills `Day`, `Tick`, `Book` and `MarketTrade`:
   - Books best price first, with positive volumes. If they send book changes, keep the book and publish it once a step, as `drill.py` does.
   - **Prices as integers of one unit for every product**, the smallest their prices use (cents). Prices then compare exactly, and PnL adds up across products. Per-product tick sizes go in `Day.info`, limits in `Day.limits`, and the loader must raise on a product without one.
   - If trades say which side was the taker, keep it (drill: as the trade's buyer or seller).
3. **Check the loader before anything else:** `arena.diagnose` on their data. Its spreads are in ticks, but its prices (edge, R, drift, the fixed level) are in the loader's unit.
4. **The bot wrapper** builds their view each step and turns the bot's actions into `Order`s and `Cancel`s:
   - Their order ids map to the engine's through `Order.tag`. The engine copies the tag to the order's `OpenOrder` and `Fill`s.
   - `begin_day(day)` gives the wrapper `Day.info`.
   - With `fresh_each_tick`, keep exactly the state their engine keeps between calls, and drop the rest (the validator compares the two runs).
5. **The bot:** in a copy of `bots/template.py`, rewrite the imports, PARAMS and ADAPTER, and nothing else. `bots/drill/template.py` shows how:
   - Convert their prices to whole ticks of each product at the boundary, and back. STRATEGY's "one tick inside" means +1.
   - Pass resting orders oldest first.
   - Take the limit from their API if it gives one.
6. **Run every tool once on their data** (`backtest`, `validate`, `grid`, `stress`, `analysis`), then compare a few fills by hand with their example or the playground.

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
  - If they rest: backtest with `--resting`. The template already handles both. On a product whose fair is known exactly (Resin-like, `fair` "fixed"), quote at `make_edge` 1, not 2: with resting orders, a rival one tick tighter took 99% of Resin's passive fills from ours at 2, and 1 is the best reply to every rival edge (`IDEAS.md`, "Against a rival that undercuts us"). But on a product that `arena.diagnose` notes as jumping, take only (`make_size` 0): resting quotes there get filled at stale prices. On P4 round 5 that turned 2–27k per product into losses of 0.7–2.4M (`IDEAS.md`).
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
  - If shared and orders rest: run the adversarial rivals too (`bots/rivals/`, `experiments/adversaries.py` with the Arena's products). On Prosperity data the one attack that worked was a large order far behind the best, against a fair value that reads the largest level; keep every fair value on `sized_mid` or fixed (`IDEAS.md`, "Adversarial rivals").
  - If ranking is relative, a rival may be built to hurt others rather than to profit: in Wang, Ventre & Polukarov (arXiv 2510.25929, not fetched) a maker trained to minimise its opponent's PnL took the flow and tightened spreads. Fetch it if the market is shared.
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
  - If orders rest: also try `--queue back`, `prob` and `front`. If the market maker re-posts its walls every tick (their size stays the same while trades print at their price, as in Prosperity), `front` is the nearer one. It only matters for quotes that join a level.
  - The quote's distance depends on it (`IDEAS.md`, "Why the zoo beat the template head to head"): under `all` a wider quote earns more (Kelp `make_edge` 1.5 best), under `worse` and in a market that reacts a tighter one does (0.5: half a tick from a half-integer wall mid, which is what the LLM-written bots quote). Once the mode is known, grid `make_edge` 0.5, 1, 1.5 on every wall-quoted product under it.
  - **The template's Kelp `make_edge` 0.5 was chosen on Prosperity 3 data** (2026-10-15), on the guess that the Arena fills like `worse`. If the playground matches `all` instead, that guess was wrong: on Prosperity data `make_edge` 1 made 81k against 73k. A jumpy product's quotes only pay if orders don't rest (Squid Ink lost its stop every day under `--resting`): if they rest, take only on such products.
  - Prior from the simulated market (2026-10-15, `IDEAS.md`, "Replay against a market that reacts"): where the market reacts, `worse` was within 10% of the bot's PnL in the market on Kelp and `all` was 2.8 times too high; with resting orders and a maker that re-posts every tick, every replay mode understated it.
- [ ] **Do our own trades move the market?**
  - Find out: probe 17. After a take that clears a level, does the next tick's book match the downloaded data (a replay), or does the price move and the level refill slowly (bots that react)?
  - We assume: a replay. Our engine shows the recorded book on the next tick, so our takes have no lasting impact, and on Prosperity data the bots' own trades left the wall mid where it was (`references/wiki/concepts/price-impact.md`).
  - If the market reacts: takes cost more than the backtest says. Take smaller pieces, expect the mid to move about the taken volume over twice the depth, and judge take-heavy variants on the portal rather than in the grid.
    - Fit `arena.sim`'s presets to the download: change them with `--spec` until `arena.diagnose` on generated days matches the real ones. Then run the bot inside it (`uv run python -m arena.sim run BOT --spec ...`) to see which replay mode agrees with the market.

## Before the first submission

- [ ] **Cap the quote of a product that holds a target.** A drift bet (`target` with `skew`, Pepper Root-like) quoted with the full room offers the whole position one tick above fair, and a rival with the same view takes it in a tick: against a copy of the template, Pepper Root made 213k with the full room and 430k quoting 10 at most (`IDEAS.md`, "Using less than the full position limit"). Grid `make_size` alone and take the smallest value that costs nothing (the market's passive flow per tick); it never binds alone on Prosperity data.
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
  - Are positions liquidated at the end, and at what price? If badly, flatten before the close: `flatten_from` about 200 ticks before the end (it crosses up to the spread, so every Prosperity day closed flat). It cost 1.7–3.3% of a day valued at the mid (`IDEAS.md`), so it pays once the liquidation's discount times the units held beats that.
  - If holding inventory costs something (a bad liquidation price, a penalty for risk or drawdown, a trend, or fills followed by adverse moves in probe 18): re-test the inventory skew. On Prosperity, where none of these held, every GLFT `skew` lost PnL (`IDEAS.md`, "The skew coefficient from GLFT's closed form"). `uv run python -m experiments.glft_skew` measures `σ`, `A` and `k` per product and backtests the skew for each `γ`, but its `PRODUCTS` (product: data alias and rounds) are hard-coded to Prosperity until the `TODO.md` item "Point the quoting experiments at the day's data" is done: edit that dict to the download's products first.
  - How are the rounds combined into a ranking? Is there a penalty for risk or drawdown?
  - If the ranking is relative, size the risk for the chance of placing, not for PnL. Qminers' 2024 winner simulated the other finalists to pick their stake, then halved it in the last round while far ahead and kept first (`references/wiki/concepts/risk-and-protecting-a-lead.md`). Before round 4 (40%), compute the lead in weighted points and decide in writing how much risk to keep.
- [ ] **Are there fees, rate limits or caps?** Fees or rebates per trade, the maximum number of orders per call or per second, and the maximum number of open orders. AlgoTrade closed your connection above 500 messages a second, and allowed 6,000 open orders.

## Every round

- [ ] **Stress the bot before submitting:** `uv run python -m arena.stress <bot> <days> --data <folder>`. Set each product's `stop_loss` to about 3× the "plain drawdown" it prints, then rerun: no product's worst day should be much beyond its stop. A fixed-fair product gets `fixed_guard` (a few ticks beyond its usual wall). The level and voucher bets are the exposure on a trend (`IDEAS.md`, "Stress: what a regime change costs").
- [ ] **Re-test the ideas register:** go down `IDEAS.md` and re-run every row that fits this round's products, on the Arena's data. The results there come from Prosperity data and are priors only: an idea dropped there may work here, and a kept one may not. Write each Arena result into its row.
- [ ] **The round's zoo.** Write the round's spec in the style of `bots/zoo/SPEC.md` (their products, API and example), and run `bots/zoo/PROMPTS.md`'s prompts through two or three models early in the round. Those bots are the baseline and the herd: the template must beat each alone and head to head under `worse` (`IDEAS.md`, "The LLM zoo").
  - We assume: teams code with hosted frontier models (ChatGPT, Claude, Gemini, free tiers included), so the herd comes from those, by hand, two samples per model and prompt: the same pair can give both a profitable bot and one that loses millions.
  - If the venue's internet is poor ("Bring your own internet connection or use eduroam", Known so far): make a fallback baseline locally with gemma4:26b and `bots/zoo/local.py --n 2` (3–4 minutes a bot), while the team works on other things. Local models aren't the field (`bots/zoo/LOCAL_MODELS.md`), so judge the template against the hosted bots once the connection allows.
  - Serving the model: `bots/zoo/LOCAL_MODELS.md`. A loaded model holds 13–16 GB of the Mac's 36 GB, so stop the server before a memory-heavy grid.
  - The zoo bots are written for the round's own API, so they run through `arena/formats/qminers.py` like ours.
- [ ] **Products:** the new products, their position limits, and whether any are related, such as baskets, ETFs or options. AlgoTrade defined each ETF's fair value as the mean of its constituents.
  - For a basket or ETF with known weights: measure its spread's daily means and sds (`experiments/baskets.py` does it for Prosperity's). If the means agree across days, set `basket`, `level` (their mean) and a `level_band` of 0.5–1.5 sds, with `make_size` 0, and check by held-out days. A family whose prices sum to a constant is a basket with legs of weight −1.
  - For options: run `experiments/p4_vouchers.py` on them, with `--data`, `--underlying`, `--prefix` (the options' common name; the strike is the number at the end) and `--expiry` (days to expiry at each day's open). We assume P4's picture: implied vol flat within a day, and each option within half a spread of Black–Scholes at one vol. If so, give each option `follow` (its underlying) and `strike`, so it rides the underlying's view as extra room. If the residuals are larger than the spread, the smile is worth trading, and the template has nothing for that yet. P3's volcanic vouchers were like that (`IDEAS.md`); there, following the underlying still made money in-sample.
- [ ] **Other traders:** are there exchange bots, and are counterparties named? In Prosperity's round 5, the names gave away informed traders.
  - If named: run `uv run python -m experiments.counterparties` on the download (it reads the Prosperity format; point its `DATASETS` at the Arena's days once their loader exists). Follow a name with the template's `copy` mode only if it is right on nearly every trade on every day, not just on average: on P3 round 5, choosing names by their mean move lost 400k on held-out days, and choosing by hit rate found only Olivia (+54k). Use it only on products where the name's moves are large next to the spread and to what market making makes there (on Kelp, copying her lost). Our own fills against a name show it only in `own_trades`; the template reads both (`IDEAS.md`, "Following informed counterparties").
- [ ] **Is `wall_mid` still the market maker's price?** It takes the largest level on each side. In a shared market, another team's large quote can be the largest level and drag your fair value with it. Against a rival copy, this cost Kelp `make_edge=0` 4,920 under `--resting`. Against the teams' real P4 bots under `--resting`, it cost the template 374k on Osmium in one round. A rival's 40-lot bid 85 below fair outweighed the market maker's 23-lot wall, so on 36% of ticks the template's fair was 5+ off (`IDEAS.md`). Check that the walls have the stable size and spacing of an exchange bot. If teams' orders compete, pick out the market maker by its usual size instead: `fair: sized_mid`, with `wall_size` between the market maker's usual size and the other levels' (15 on Prosperity). Against the teams' bots it made +39k on Osmium in the round where `wall_mid` lost 377k.
  - We assume: a product the template has no tuned `fair` for uses `sized_mid` with `wall_size` 15 (`DEFAULTS`, since 2026-10-15). With no level of that size it falls back to the mid. If the market maker's usual size is far from 15, set `wall_size` per product (or in `DEFAULTS`) first.
  - A shared market may also hold spoofers: large orders posted to move book-readers, then cancelled. They profit most in thin markets (`references/wiki/sources/spoofability-and-liquidity.md`). If large levels appear and vanish without trading, switch `fair` to `sized_mid` for that product.
- [ ] **Evaluation data:** is the round scored on the data you were given, or on fresh data? The site hints at a private evaluation next to the public backtest. If fresh, trust the grid's `nbhd` and `min day` measures over its best `pnl`, and read its held-out days. With only a few days and measures that disagree, the rehearsal took the best worst day. Check whether the download reuses earlier rounds' days, as Prosperity did: the grid flags it.
- [ ] **Extra information:** news, external prices, or conversions to another market.
  - News or text may be written by an LLM, and in a shared market another team may be steering it: an RL trader that could post to the feed learned to pump the bots following it (`references/wiki/sources/accidental-pump-and-dump.md`). Check a text signal against the next prices before trading on it.
  - If the book shows a side total or depth beyond the priced levels, keep it out of `fair` and the imbalance: that is what real spoofers on the Korea Exchange exploited, until the exchange showed prices instead (`references/wiki/sources/spoofing-traders-empirical.md`).
- [ ] **Rule changes:** anything different from the previous round, such as limits, fees or matching.
- [ ] **Which of the harder-round mechanisms does this round have?** Go down the list in `references/wiki/concepts/harder-rounds.md` (a reactive market, a regime shift, organiser bots that punish the playbook, an agent-written field, fees, caps, latency, settlement, scoring) and check each entry's "tell" against the docs, the data and the probes.
  - We assume: the later rounds add at least one of them, above all the finale (40%).
  - Then: apply each entry's "prep". Where the private run can't be seen, as with a regime shift, assume it: prefer the grid's worst day over its best PnL, and keep the loss stops on.
  - For a regime shift, also run the bot in a market that reacts: `uv run python -m arena.sim run <bot> --products ... --regime trend_up` (and the other three). A fixed anchor needs `fixed_guard`. For a level bet nothing won in every regime on Prosperity data. If the round's level is known to trend away, try `cpd_action: "drop"` (with `cpd_reversion` and `cpd_sd` measured on the download) or a stop near 1.25× the plain-day drawdown, and compare them on the trend and shift columns (`IDEAS.md`, the two changepoint and regime rows).
  - Spoofed walls (D3): look for large levels that appear and vanish without trading, and for an imbalance that is one-sided just before market trades and back to normal after (`references/wiki/sources/detecting-spoofing-strategies.md`). If found, a `fair` that ignores new large levels until they persist.
  - The close (C5): if positions are marked to an average over a closing window, watch that window for one-sided runs of market orders (`references/wiki/sources/benchmark-manipulation.md`), and settle inventory before it.
  - Our own bot must not look like a spoofer: no large orders we mean to cancel, and a check that tuning didn't learn them (`references/wiki/sources/learning-not-to-spoof.md`). This is a default, not a rule we know of: read the Technical Rules for a market-abuse clause (spoofing, marking the close, deliberately hurting other teams). If they allow it, and the market is shared with resting orders or reacts to us, see `IDEAS.md`, "Manipulating other bots". Say which in this item, with the rule's wording.

## Probes

`bots/probe.py` answers most of the first-hour list in one playground run of about 420 ticks. It
runs probes 10, 9, 7, 1–2, 5, 3, 12, 4, 11, 6, 8, 17, 18 and 13 in that order, each in its own window,
cancelling and flattening between them. Each tick it prints a `SEEN` line with the book, position,
open orders and fills, and each probe prints one `PROBE <name>: <finding>` line. Rewrite its ADAPTER
for their API first, as for the template. In our own engine it finds:
- per tick: orders don't rest, and limits reject every order for the product;
- with `--resting`: orders rest, and the book doesn't show our own;
- both: no self-trade, fills reported one call later, called again after an exception, and every kind of state kept.

So any other answer on the platform is a difference to act on. Probes 14–16 compare with data outside the bot. The probes:

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
18. **Passive fills and their markout:** for a few hundred ticks, keep one lot at the best bid and one at the best ask, with no signal, re-posting when the price moves away. Record how often each fills and the mid 1, 10 and 50 ticks after each fill. Negative markouts mean the fills come with adverse moves (`references/wiki/sources/negative-drift-of-a-fill.md`); run the same orders in our engine on the same data and compare (as in probe 16). This is the live experiment of `references/wiki/sources/market-makers-dilemma.md` in miniature. On Prosperity data the template's own passive fills had no state with a negative value (`IDEAS.md`, "Passive fills' value by state"): run `uv run python -m experiments.quote_markouts` on the download too (point its `DATASETS` at it, until the `TODO.md` item "Point the quoting experiments at the day's data" adds flags), and if some state's total is negative on every day, gate that side in `make`.
