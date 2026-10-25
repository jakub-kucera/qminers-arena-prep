# On the day: what to find out

The organisers won't answer questions. Everything here has to come from their docs, the
playground, or a probe bot (see [Probes](#probes)). Settle the **first hour** list before writing
any strategy, because those answers change the code.

The tooling assumes IMC Prosperity's rules unless told otherwise. Each item says what we assume
now, and what to change if the Arena differs. **Write the answer in under each item as soon as
you know it**, with where it came from (docs, probe, email), so the whole team works from the
same facts.

## The day: timeline and roles

The official times are from the organisers' e-mail of 7 Oct (`references/algo_trade_arena_conversation.json`, its first message; see "Known so far"). The plan column, the roles and the rota are ours: try them in the mock round and change them there (`TODO.md`, "Run a mock round" and "Agree the roles and the sleep rota").

| Time | Official | Our plan |
|---|---|---|
| Sat 08:00–09:00 | arrival, registration | Laptops on power and a connection (eduroam or our own); `git pull`, `uv run pytest` passes; `references/` was cloned at home (2 GB). |
| 09:00–09:30 | opening ceremony | The Technical Rules are published and explained now: one person reads them in full and writes every answer they give into "First hour" below. |
| 09:30–10:30 | workshop | The API and data format: start the three tracks of "Splitting the first hour" as soon as either is shown. By 10:30, decide on a fallback bot ("A fallback first?" in "Spend the round's submissions"). |
| 10:30–12:00 | **playground (90 min)** | The probe bot first (its risky probes run last), then the plain template once its ADAPTER runs, to measure the engine's error. The loader and `arena.diagnose` on any data they give. |
| 12:00–13:00 | lunch | The template's ADAPTER finished, `arena.validate` with their time limit, the round-1 candidates written down in order. |
| 13:00–18:00 | **round 1 (10%)** | The round's protocol below. Round 1 is the "forgiving market": get a validated upload in early. |
| 18:00–19:00 | dinner | Handover note. |
| 19:00–24:00 | **round 2 (20%)** | The round's protocol; B may nap if it looks like round 1 (Sleep, below). |
| Sun 00:00–01:00 | coffee break | Handover note. |
| 01:00–06:00 | **round 3 (30%)** | The round's protocol; A, round 4's driver, may nap if it looks like round 2 (Sleep, below). |
| 06:00–07:00 | breakfast | Handover note. Before round 4, decide in writing how much risk to keep (the lead in weighted points; "How is PnL scored?"). |
| 07:00–12:00 | **round 4 (40%)** | Both at the keyboard; no naps. |
| 12:00–14:00 | lunch, closing | |

**Each round (5 hours, T = its start).** Each agent session starts from `KICKOFF_PROMPT.md`, which holds the same times:
- T+0:00: download the data and the round's rules; write what changed into "Rule changes" and "Products".
- T+0:15: `arena.diagnose`; backtest the last round's bot on the new days in every fill mode.
- T+2:00: a validated bot that is at least as good, and an upload by the submission rule ("Spend the round's submissions by a rule written before the first score").
- T+4:30: stop changing the strategy; validate the final candidate and upload it.
- T−0:10: check which submission is marked final.

**Roles.** We are two (2026-10-24), so each holds two of the four; write the names in before the event:
- **A** (<name>), **driver** and **recorder**: owns the bot file and every upload (nobody else uploads, except as "Sleep" says); writes each answer into this file with its source, keeps the round's submission list, and writes the handover note. In the first hour: the checklist, then the probes.
- **B** (<name>), **data** and **research**: the loader, `arena.diagnose`, backtests, grids, stress; the "Every round" items, re-tests from `IDEAS.md`, the round's zoo. In the first hour: the data track.

**Sleep.** Both of us stay on site all night, with no accommodation (the user, 2026-10-24). Sleeping bags and mats aren't allowed in the building (Known so far), so a nap is on a chair, a table or the floor. No sleep is planned. A nap of up to 90 minutes is taken only in round 2 or 3, and only when the round looks like the one before: no new products or rules at T+0:00, the same `arena.diagnose` notes at T+0:15, and the last round's bot backtesting about as well on the new days, validated and uploaded. Then one sleeps between T+0:30 and T+4:00 while the other runs the protocol: B in round 2, A in round 3, since A drives round 4 (40%). While A sleeps, B uploads only candidates already on the written list. Nobody naps in round 4, or in a round that brought anything new. Whoever wakes reads the round's notes so far before touching the bot.

**Handover note** at the end of each round, in `data/arena/round<N>/HANDOVER.md` (kept with the round's data, not committed): what was uploaded and why, its portal score against the local backtest, the questions still open, and the next round's first three actions.

## Splitting the first hour

Each agent session starts from [`KICKOFF_PROMPT.md`](KICKOFF_PROMPT.md): one prompt for round 1 and one for rounds 2–4, with the data, the rules, the deadline and the session's track filled in.

Three tracks can run in parallel (with two of us: A the checklist, then the probes; B the data; "The day: timeline and roles"):
- **Checklist:** read the docs and fill in every answer they give.
- **Probes:** rewrite `python/bots/probe.py`'s ADAPTER for their API, set `PRODUCT` and `LIMIT`, and run it in the playground (see "Probes" below).
- **Data:** write the loader in `python/arena/formats/qminers.py`, so the backtester runs on their data as soon as possible: follow "The format swap, step by step" below. Then run `arena.diagnose` on it (see "What kind of market is each product?").

## The format swap, step by step

Practised on the drill format (2026-10-17, `python/arena/formats/drill.py`, `python/bots/drill/template.py`), which differs from Prosperity's in every way we could think of. The plug-in took about 300 lines and the bot's ADAPTER about 100. Running the tools on it found four Prosperity habits, now fixed; the steps below avoid the rest.

1. **Copy `python/arena/formats/drill.py` to `qminers.py`** and register it in `FORMATS`. Set `RESTING = True` if their orders rest until cancelled.
2. **The loader** fills `Day`, `Tick`, `Book` and `MarketTrade`:
   - Books best price first, with positive volumes. If they send book changes, keep the book and publish it once a step, as `drill.py` does.
   - **Prices as integers of one unit for every product**, the smallest their prices use (cents). Prices then compare exactly, and PnL adds up across products. Per-product tick sizes go in `Day.info`, limits in `Day.limits`, and the loader must raise on a product without one.
   - If trades say which side was the taker, keep it (drill: as the trade's buyer or seller).
3. **Check the loader before anything else:** `arena.diagnose` on their data. Its spreads are in ticks, but its prices (edge, R, drift, the fixed level) are in the loader's unit.
4. **The bot wrapper** builds their view each step and turns the bot's actions into `Order`s and `Cancel`s:
   - Their order ids map to the engine's through `Order.tag`. The engine copies the tag to the order's `OpenOrder` and `Fill`s.
   - `begin_day(day)` gives the wrapper `Day.info`.
   - With `fresh_each_tick`, keep exactly the state their engine keeps between calls, and drop the rest (the validator compares the two runs).
   - Provide the bot exactly their API: their classes, their constructor signatures, nothing of ours. `arena.validate` can only catch a call their exchange would reject if the provided module rejects it too. Our Prosperity datamodel has extensions (`Cancel`, `Order(..., ioc=True)`, `state.open_orders`), so a bot that passes against it could fail on IMC's real one.
5. **The bot:** in a copy of `python/bots/template.py`, rewrite the imports, PARAMS and ADAPTER, and nothing else. `python/bots/drill/template.py` shows how:
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
- **Submissions per round are capped** (the number is not in the code). The newest upload becomes your final one automatically, and you can mark an earlier one as final instead. (Changed by 2026-10-25: only once it completes successfully; see below.)
- **Evaluation:** a new upload is "queued for evaluation on the public backtest", and a button offers **"Download public backtest data"** for each round, so historical data is provided. Submissions have a type, PUBLIC or PRIVATE, and the detail page has an "Evaluated submission" link, which suggests a private run of a public submission. The final score is probably on hidden data.
- **Round weights:** the live leaderboard ("Market simulation rankings") shows Phase 1 to 4 at **10%, 20%, 30% and 40%**, plus a weighted total. The first round, the "forgiving market", is worth the least.
- **Technical Rules are published at the start** and explained in the opening briefing: permitted resources and tools, evaluation process, scoring, tie-breaks and technical limits. Read them before anything else.
- The final solution must be Python. Other languages, AI tools, literature and public online resources are allowed for preparing it, unless the Technical Rules say otherwise.
- Teams must work independently, and may not post questions about the task publicly or ask anyone outside the team during the event. (Reading public material is fine.)
- All leaderboards are preliminary. The organisers verify the validity and **reproducibility** of the top solutions and may rerun them. Keep the bot deterministic: seed any randomness and don't depend on wall-clock time.
- Prizes: 100,000 / 60,000 / 40,000 CZK for places 1 to 3. Bring your own internet connection or use eduroam.

From the site again on 2026-10-25 (`references/check_arena_site.py` against the 10 Oct snapshot, then `--save`), the portal gained:
- **Metrics on each submission:** filled orders, traded volume (lots), end position (lots), cash (in the Czech text), a **mark-out price**, a **position-limit penalty**, a **PnL standard error**, and the 50 / 68 / 95 / 99.7% quantiles of |position|. What each means is not in the code; "How are position limits enforced?" and "How is PnL scored?" say what we read into them.
- **One evaluation at a time:** a team can't submit again until its previous submission has finished evaluating.
- **Which submission is final, changed:** a new one "becomes your final submission once it completes successfully (your first one is final straight away)". On 10 Oct it became final at upload.
- **The leaderboard:** "Each team's final submission, evaluated on the private backtest", which "runs after the submission deadline": a ranking of rank, team and PnL (with ties), and a chart of each team's PnL over time, the time axis in seconds and PnL in thousands of dollars (linear or log).

From the organisers' e-mail of 7 Oct (saved as the first message of `references/algo_trade_arena_conversation.json`, the conversation it was pasted into):
- 200+ participants, with a waiting list.
- The schedule: Saturday 08:00 arrival, 09:00 opening, 09:30 workshop, **10:30–12:00 playground**, 12:00 lunch, **round 1 13:00–18:00**, 18:00 dinner, **round 2 19:00–24:00**; Sunday 00:00 coffee break, **round 3 01:00–06:00**, 06:00 breakfast, **round 4 07:00–12:00**, 12:00 lunch, 13:00–14:00 closing. "The day: timeline and roles" plans around it.
- Strictly in person, with no way to take part off site. Members may leave to rest or sleep, but **at least one member of each team must always be on site**. Sleeping bags and mats are not allowed by the building; the organisers suggest booking accommodation nearby and taking turns.
- Coffee, tea and water throughout; lunch, dinner, midnight refreshments, breakfast and a light lunch are provided.
- A last e-mail comes about a week before the event, with travel, parking and the final instructions (`MANUAL_TODO.md`, A: save it).
- Still unknown: whether all teams share one market or each team trades alone (the leaderboard calls itself a market simulation, and one of the four skills listed is "game theory... anticipate competitors"), the bot interface, the data format, and the runtime limits.

## First hour: answers that change the code

- [ ] **How is the bot called?**
  - Find out: the entry point (class or function), its arguments, and what it must return. Is it called once per tick with a snapshot, or fed events as they happen? AlgoTrade 2026 was a websocket with a broadcast every 100 ms.
  - We assume: `Trader().run(state)` once per tick, returning `(orders, conversions, traderData)`.
  - What the Arena site implies: a single `.py` file uploaded to a portal and run by their simulator on a backtest, not a live socket client. That favours our file-and-adapter setup over an event-driven client. Read the Technical Rules for the entry point.
  - Weak prior only: Qminers' earlier Quant Hackathon (2022, 2024, 2025) was a different task, and this year is expected to be a big shift from those. There they gave out the server's own evaluation loop (the same code in 2024 and 2025, `references/wiki/sources/qminers-hackathon-2024.md`) and a stub `Model` class called per step with pandas DataFrames (see `references/README.md`), so keep the ADAPTER the only place that touches their types, and check whether pandas and numpy are allowed (probe 10).
  - If it does turn out to be event-driven, `references/` has a model for it: Optiver's Ready Trader Go kit (see the "Read online" list) uses callbacks for book updates and fills.
  - If different: write `python/arena/formats/qminers.py`, modelled on `prosperity.py`, and rewrite the template's ADAPTER. An event-driven API also needs engine work, so flag it at once.
- [ ] **Do unfilled orders rest between ticks?**
  - Find out: probe 1.
  - We assume: no. Everything unfilled is cancelled at the end of the tick.
  - If they rest: backtest with `--resting`. The template already handles both. On a product whose fair is known exactly (Resin-like, `fair` "fixed"), quote at `make_edge` 1, not 2: with resting orders, a rival one tick tighter took 99% of Resin's passive fills from ours at 2, and 1 is the best reply to every rival edge (`IDEAS.md`, "Against a rival that undercuts us"). Against fields of three to six rivals, Resin at 2 kept 0.9–18.8k where 1 kept 24–40k (`IDEAS.md`, "Our settings against a field of rival archetypes"). But on a product that `arena.diagnose` notes as jumping, take only (`make_size` 0): resting quotes there get filled at stale prices. On P4 round 5 that turned 2–27k per product into losses of 0.7–2.4M (`IDEAS.md`).
  - If they don't rest: a jumping product is worth quoting, at the edge its fill mode favours. Squid Ink made +10.1k at 0.5 under `worse` and +29.6k at 1 under `all` on P3 days it was never tuned on, while every quote lost 45–72k with `--resting` (`TODO.md`, the Squid Ink decision).
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
  - From the site (2026-10-25): each submission's metrics include a **position-limit penalty**, so a breach may be charged rather than only rejected. The template never sends more than its room, so a charge doesn't touch it; a backtest of a bot that does (a zoo bot, a rival) would need a penalty in `_breaches` to match. Probe 4 tells which.
  - We assume: Prosperity's rule. If all your buys, or all your sells, filling could breach the limit, every order for that product is cancelled. Limits are symmetric.
  - If different: update the limits table (`LIMITS` in the format module), the template's `Plan` room, and the engine's `_breaches` if backtests need to match.
  - In a shared market: another team can fill one of your orders between your decision and your next orders. If a breach cancels every order for the product, the whole tick's quotes go. Leaving a few lots of room under the limit avoids that.
- [ ] **Is the market shared with the other teams?**
  - Hints from the site, which point both ways: the leaderboard is called "Market simulation rankings", one of four listed skills is "game theory... anticipate competitors", and submissions come in PUBLIC and PRIVATE types. That fits a solo run on historical data for the public score and a shared simulation of the final files for the private one. It also fits two solo runs. Nothing says which. The leaderboard (2026-10-25) charts every team's PnL over time on the private backtest, which fits either.
  - Find out: do trades or book levels appear that the exchange's own bots couldn't explain? Are counterparties named?
  - Find out also: when several teams' orders arrive at the same tick, who goes first? Random, by time sent, or a fixed order?
  - We assume (with `--vs`): a random order, drawn again every tick.
  - If shared: tune with `--vs` (copies or variants of your bot) as well as alone, and prefer settings that hold up in both.
  - If shared: score the candidate settings against fields of rivals, not one copy: `uv run python -m experiments.rival_field --data <folder> --days <days> --candidate PARAMS.<P>.make_edge=0.5,1,2 --engine rust` (Prosperity format only, until the archetypes' ADAPTERs are rewritten for the Arena's API). On Prosperity data the best reply changed with the field, and the reply to one copy was neither the max-min nor the mean choice (`IDEAS.md`, "Our settings against a field of rival archetypes"). Take one of those two.
  - If shared, in either mode: a market trade goes to the best-priced order first, so a rival quoting nearer fair than our quote (which `make` keeps one tick inside the book) takes the trades. Per tick, Gemini's zoo market maker took most of Resin that way, whatever Resin's `make_edge` (2026-10-23, `IDEAS.md`, "Why the zoo beat the template head to head"). Test quoting nearer fair against the day's zoo (`IDEAS.md`, not yet tested).
  - If shared and orders rest: run the adversarial rivals too (`python/bots/rivals/`; `uv run python -m experiments.adversaries --data <folder> --days <days>`, once the rivals' ADAPTERs are rewritten for the Arena's API: in another format only the template copy runs). On Prosperity data the one attack that worked was a large order far behind the best, against a fair value that reads the largest level; keep every fair value on `sized_mid` or fixed (`IDEAS.md`, "Adversarial rivals").
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
  - Then: write the loader in `python/arena/formats/qminers.py`, and run the template and validator on it before changing any strategy.
  - If no data is provided: have the probe bot print the full book and trades every tick, and build a dataset from the logs.
- [ ] **Is the data a real series in disguise?** An idea to explore, **only once the user explicitly approves it**: the search can cost an agent a lot of tokens, so agree a budget first.
  - Why: last year's data (hockey) was the Czech league with the years changed, so that the source couldn't simply be looked up (the user, 2026-10-22).
  - Find out: look for fingerprints in the download that survive relabelling: the shape of each series after rescaling, the gaps and session structure in the timestamps, the volatility, the correlations between products, and any dated jumps. Compare them by shape, not by date, with public historical data that could have been used: indices, futures, FX, crypto, and sports or other event data if the products look like that.
  - We assume: the prices are simulated (the site promises a "realistic" simulated exchange), so nothing outside the download predicts them.
  - Then: if a source turns up, first check that the Technical Rules allow using it. If they do, it tells you what kind of process each product is (a level it returns to, trends, news jumps), and possibly how the private run continues.
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
  - We assume: the per-tick mode with `--match-trades all`, which was the most optimistic on Prosperity data (P3 round 1, the template as committed: 72.7k, against 63.3k under `worse` and 28.2k under `none`; `README.md`, "Fill assumptions matter").
  - Then: use the closest settings for every backtest and grid. If none is close, rank grid results by the most conservative mode.
  - If several settings stay possible (the probes can't tell `back` from `front`, or whether other teams compete for the fills), grid under each as a `--scenario` and take the summary's `pick`, which must beat the bot as is under every one: e.g. `--modes all,worse --scenario rest:resting,queue=back --scenario front:resting,queue=front --scenario thin:fill=0.5 --scenario war:vs=BOT@PARAMS.<P>.make_edge=0`. Don't choose by the `worst` column: on Prosperity and simulated days that rule lost money most often (`IDEAS.md`, "Choosing a cell by its worst case over fill-model scenarios").
  - For a grid of hundreds of cells, add `--screen 0.25` and put the closest-matching mode first in `--modes`: the screen ranks on the first day under the first mode only. Take the pick from the summary's last section, on the days the screen didn't see. For many settings at once, `--halving 0.5` on `--engine rust` (100,000 cells in about 100 s; with one mode, the last day stays unseen), and `--sample N` past a few hundred thousand cells.
  - `--engine rust` makes a grid about 40 times faster with the same output, for bots with a Rust twin (`rust/twins.json`): `python/bots/template.py` in the Prosperity format and `python/bots/drill/template.py` in the drill format. The Arena's template is a twin by config, with no Rust code of its own, if its ADAPTER follows the drill's conventions (or Prosperity's) on six choices: prices in ticks or in the format's unit, trader names in the trades, our fills among them, the limit from PARAMS or the exchange, the products in the books' or the exchange's order, resting orders sorted or as listed. Three steps: (1) write the ADAPTER by those conventions; (2) add its row to `rust/twins.json`: `{"kind": "template", "format": "qminers", "adapter": "drill" or {the six choices}, "rust": "rust/src/bots/template.rs", "reads": ["DEFAULTS", "PARAMS"]}`, with `"sha256": ""` until it is recorded; (3) `uv run python -m experiments.rust_bench --twin <the bot> --data <folder> --days <days> --format qminers --record`, which compares every recorded field in 23 cases on the round's own data and records the hash if all are identical (`rust/README.md`, "A new twin"). Until it is identical, grid in Python.
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
  - From the site (see Known so far): single `.py` upload, a cap per round, public and private evaluations. As of 2026-10-25: one evaluation at a time; a submission becomes final only once it completes successfully (the first one at once); the ranking is each team's final submission on the private backtest, run after the deadline.
  - So: run `arena.validate` before every upload. Never spend a submission on untested code. Before the deadline, check which submission is marked final.
  - The round's first upload is final before it has run, so make it one that works ("A fallback first?" below). A later upload that fails leaves the final as it was, but one that completes replaces it: after an exploratory upload, mark the chosen one final again. Each upload blocks the next until it has run, so time the first evaluation and leave room for it before the deadline.
  - Also find out what the leaderboard shows of other teams. In Qminers' 2024 hackathon it showed every team's score, runtime and RAM, and the winner read rivals' models from it. They also capped their own public score at a tenth of the model's until the last hours, so others wouldn't try harder (`references/wiki/sources/qminers-hackathon-2024.md`). If a public score here doesn't count toward the ranking, the same applies: don't show the full bot early. A scored round's result does count (10/20/30/40%), so never hold back there.
- [ ] **Can you submit several times during a round, and see each score before the deadline?**
  - Find out: the Technical Rules, then the portal's submissions table on the first upload. Does a score come back during the round, how long does it take, and is it the public backtest's or the private run's?
  - We assume: yes, several times, each with a public-backtest score back within the round. The portal's table lists submissions with a status and a score, the cap is per round, and an earlier upload can be marked final (Known so far). Not confirmed.
  - From the site (2026-10-25): several, one at a time (the next waits until the previous has run). A score during the round can only be the public backtest's, since the private one runs after the deadline, and the public backtest data can be downloaded, so that score is probably on the download (the last bullet).
  - If only one upload per round, or no score until the round ends: every choice is made locally. Skip the protocol below except its first step, and spend the time on `arena.validate`, the grid's `pick` and `arena.stress`.
  - If scores come back but the public backtest is the downloaded data: the score checks our engine, not the strategy (it is in-sample). Use it as probe 16, not to choose between variants.
- [ ] **Spend the round's submissions by a rule written before the first score.** From Dwork et al.'s reusable holdout (`references/wiki/sources/reusable-holdout.md`): a score checked again and again overfits the data behind it, and every look is a trial. The safe use answers from local evidence and lets the hidden score speak only when it disagrees, within a budget.
  - **Before any upload**, write down the round's candidates in order (no more than the cap), each with its local result. Each must pass `arena.validate` and come from the grid's `pick` under `--modes all,worse`, or from `python/experiments/selection_rules.py`'s rule for anything gridded by hand.
  - **A fallback first? Decided on the day, by 10:30** (the user, 2026-10-24). A 40–60-line market maker written straight against their API (fair at the mid or the largest level, quote one tick inside, cancel and requote each step, stay inside the limit) could be the first upload while the template's ADAPTER is finished. Write it if both hold: the cap leaves room for an extra round-1 upload, and their API is far enough from Prosperity's that the ADAPTER may not be validated by 13:00 (on the drill it took about 100 lines). With two of us, an agent session writes it from their docs (the zoo's `market_maker` prompt, `python/bots/zoo/PROMPTS.md`), so neither of us leaves a track. Upload it once it runs in the playground, let the template replace it once validated, and keep it as a `--vs` rival and a check of our loader: both engines should give it similar fills (probe 16). The evidence and options: `TODO_DONE.md`, "Write a fallback bot against the Arena's API in the playground?".
  - **Upload the plain template first, early.** It catches format errors, and the gap between its portal score and our backtest on the same data is the engine's error, `T`. Measure it as a share of PnL, per product if the portal shows that.
  - **A later score agrees** if it is within `T`, plus a margin, of what the local backtest predicts. Then the local result decides, and the score only confirms.
  - **A score that disagrees beyond that** spends one unit of a budget of 2 per round. Find out why (probe 16: compare fills) before letting it change a choice. Once the budget is spent, stop reading scores for choices and decide locally.
  - **Never choose between two variants by portal score when their scores are within `T` of each other.** That is selecting on the holdout.
  - **If scores are the only evidence** (no local data, or the engine can't be matched): use the 37% stopping rule (`references/wiki/sources/deflated-sharpe-ratio.md`). Upload about a third of the planned candidates to explore, then mark final the first later one that beats all of them.
  - **Before the deadline,** mark final the candidate the local evidence chose, unless a disagreement was explained and favours another. The newest upload that completes becomes final by default (Known so far), so check the mark.
- [ ] **What does an exception do?** Probe 6. Is the tick skipped, the bot stopped, or the round lost? The template catches errors per product unless `STRICT` is set.
- [ ] **What are the price units?** Integer ticks? Tick size? Cents? The template rounds prices to `int`.
  - We assume: a tick of 1. The template hard-codes it: `make` steps to `best_bid + 1` / `best_ask - 1` and rounds with `floor`/`ceil`, and `Trader.run` sends `int(price)`. The Prosperity loader also reads prices with `int(float(...))` (every P2–P4 price is a whole number, checked 2026-10-13).
  - If the tick isn't 1: add a `tick` parameter and use it in `make` and the rounding, and keep prices as the exchange's type in the loader and the ADAPTER. With a tick of 0.01, `int(price)` would send prices off by up to a whole unit.
- [ ] **How is PnL scored?**
  - From the site (2026-10-25): the ranking is by PnL (the leaderboard shows rank, team and PnL). Each submission shows a **mark-out price**, probably the price the end position is valued at: if it differs from the mid, flattening pays (the next bullets). It also shows a **PnL standard error** and |position| quantiles: a standard error suggests the score averages several runs, or a noisy simulation, so one run's PnL is a draw and a small gap between two variants means nothing. None of this is confirmed: read the Technical Rules.
  - At which price are open positions valued: mid, last trade, or a settlement price?
  - Are positions liquidated at the end, and at what price? If badly, flatten before the close: `flatten_from` about 200 ticks before the end (it crosses up to the spread, so every Prosperity day closed flat). It cost 1.7–3.3% of a day valued at the mid (`IDEAS.md`), so it pays once the liquidation's discount times the units held beats that.
  - If holding inventory costs something (a bad liquidation price, a penalty for risk or drawdown, a trend, or fills followed by adverse moves in probe 18): re-test the inventory skew. On Prosperity, where none of these held, every GLFT `skew` lost PnL (`IDEAS.md`, "The skew coefficient from GLFT's closed form"). `uv run python -m experiments.glft_skew --data <folder> --days <days> --format qminers --bot <our bot>` measures `σ`, `A` and `k` per product (every product the bot trades there, or `--products`) and backtests the skew for each `γ`.
  - How are the rounds combined into a ranking? Is there a penalty for risk or drawdown?
  - If the ranking is relative, size the risk for the chance of placing, not for PnL. Qminers' 2024 winner simulated the other finalists to pick their stake, then halved it in the last round while far ahead and kept first (`references/wiki/concepts/risk-and-protecting-a-lead.md`). Before round 4 (40%), compute the lead in weighted points and decide in writing how much risk to keep.
- [ ] **Are there fees, rate limits or caps?** Fees or rebates per trade, the maximum number of orders per call or per second, and the maximum number of open orders. AlgoTrade closed your connection above 500 messages a second, and allowed 6,000 open orders.

## Every round

- [ ] **Stress the bot before submitting:** `uv run python -m arena.stress <bot> <days> --data <folder>`. Set each product's `stop_loss` to about 3× the "plain drawdown" it prints, then rerun: no product's worst day should be much beyond its stop. A fixed-fair product gets `fixed_guard` (a few ticks beyond its usual wall). The level and voucher bets are the exposure on a trend (`IDEAS.md`, "Stress: what a regime change costs").
- [ ] **Re-test the ideas register:** go down `IDEAS.md` and re-run every row that fits this round's products, on the Arena's data. The experiments behind the rows take it as `--data <folder> --days <days> --format qminers --bot <our bot>`, plus each one's own options (`python/experiments/README.md` has the commands). The results there come from Prosperity data and are priors only: an idea dropped there may work here, and a kept one may not. Write each Arena result into its row.
- [ ] **Re-test the grid's pick rule on the Arena's own days.** The `pick` (SPA, then StepM, then every `--modes` entry) was chosen after scoring ten rules on the same Prosperity days (`IDEAS.md`, "Selection rules on unseen days"), so that choice is itself the best of ten. It was the only rule never to lose there, and on fresh simulated days it lost least often among the rules that gained (2 of 120 runs, `python/experiments/selection_rules_sim.py`). That is evidence it isn't luck, but the Prosperity part is still in-sample.
  - Once two rounds' data exist: `uv run python -m experiments.selection_rules --data <folder> --format qminers --bot <our bot> --train <round 1's days> --test <round 2's days> --products <the products> --grid make_edge=0.5,1,1.5,2 --grid take_edge=0,1,2` (any two axes the round tuned), training on the earlier round and testing on the later. Check that the pick still loses least often under the mode the playground matches.
  - If another rule does better there, use it for the remaining rounds and write the result into the row.
- [ ] **The round's zoo.** Write the round's spec in the style of `python/bots/zoo/SPEC.md` (their products, API and example), and run `python/bots/zoo/PROMPTS.md`'s prompts through two or three models early in the round. Those bots are the baseline and the herd: the template must beat each alone and head to head under `worse` (`IDEAS.md`, "The LLM zoo").
  - We assume: teams code with hosted frontier models (ChatGPT, Claude, Gemini, free tiers included), so the herd comes from those, by hand, two samples per model and prompt: the same pair can give both a profitable bot and one that loses millions.
  - If the venue's internet is poor ("Bring your own internet connection or use eduroam", Known so far): make a fallback baseline locally with gemma4:26b and `python/bots/zoo/local.py --n 2` (3–4 minutes a bot), while the team works on other things. Local models aren't the field (`python/bots/zoo/LOCAL_MODELS.md`), so judge the template against the hosted bots once the connection allows.
  - Serving the model: `python/bots/zoo/LOCAL_MODELS.md`. A loaded model holds 13–16 GB of the Mac's 36 GB, so stop the server before a memory-heavy grid.
  - The zoo bots are written for the round's own API, so they run through `python/arena/formats/qminers.py` like ours.
  - Score them in one run: `uv run python -m arena.compare <our bot> <days> --format qminers --data <folder> --bot python/bots/zoo/<round>/*.py --modes all,worse`. Our bot is the baseline, and the summary's `pick` names any zoo bot that beats it under every mode. Read its PnL per product for what to borrow.
- [ ] **Products:** the new products, their position limits, and whether any are related, such as baskets, ETFs or options. AlgoTrade defined each ETF's fair value as the mean of its constituents.
  - For a basket or ETF with known weights: measure its spread's daily means and sds (`python/experiments/baskets.py` does it for Prosperity's). If the means agree across days, set `basket`, `level` (their mean) and a `level_band` of 0.5–1.5 sds, with `make_size` 0, and check by held-out days. A family whose prices sum to a constant is a basket with legs of weight −1.
  - For options: run `python/experiments/p4_vouchers.py` on them, with `--data`, `--underlying`, `--prefix` (the options' common name; the strike is the number at the end) and `--expiry` (days to expiry at each day's open). We assume P4's picture: implied vol flat within a day, and each option within half a spread of Black–Scholes at one vol. If so, give each option `follow` (its underlying) and `strike`, so it rides the underlying's view as extra room. If the residuals are larger than the spread, price each option off the underlying instead: `smile` (the parabola from part 1 of `uv run python -m experiments.p3_smile --data <folder> --days <days> --underlying <U> --prefix <P> --expiry <day>=<days>,...`, or one flat vol), `underlying`, `strike`, `expiry` (days at the round's open), `take_edge` 0.5 and `make_size` 0, on the strikes whose fast residual beats half their spread. On P3's volcanic vouchers that made 529k over five days against 155k for following the underlying, every day positive; quoting them lost when orders rested, and the delta hedge halved the gain (`IDEAS.md`).
- [ ] **Other traders:** are there exchange bots, and are counterparties named? In Prosperity's round 5, the names gave away informed traders.
  - If named: run `uv run python -m experiments.counterparties --data <folder> --days <days> --format qminers --bot <our bot>` on the download. Follow a name with the template's `copy` mode only if it is right on nearly every trade on every day, not just on average: on P3 round 5, choosing names by their mean move lost 400k on held-out days, and choosing by hit rate found only Olivia (+54k). Use it only on products where the name's moves are large next to the spread and to what market making makes there (on Kelp, copying her lost). Our own fills against a name show it only in `own_trades`; the template reads both (`IDEAS.md`, "Following informed counterparties").
- [ ] **Is `wall_mid` still the market maker's price?** It takes the largest level on each side. In a shared market, another team's large quote can be the largest level and drag your fair value with it. Against a rival copy, this cost Kelp `make_edge=0` 4,920 under `--resting`. Against the teams' real P4 bots under `--resting`, it cost the template 374k on Osmium in one round. A rival's 40-lot bid 85 below fair outweighed the market maker's 23-lot wall, so on 36% of ticks the template's fair was 5+ off (`IDEAS.md`). Check that the walls have the stable size and spacing of an exchange bot. If teams' orders compete, pick out the market maker by its usual size instead: `fair: sized_mid`, with `wall_size` between the market maker's usual size and the other levels' (15 on Prosperity). Against the teams' bots it made +39k on Osmium in the round where `wall_mid` lost 377k.
  - We assume: a product the template has no tuned `fair` for uses `sized_mid` with `wall_size` 15 (`DEFAULTS`, since 2026-10-15). With no level of that size it falls back to the mid. If the market maker's usual size is far from 15, set `wall_size` per product (or in `DEFAULTS`) first.
  - A shared market may also hold spoofers: large orders posted to move book-readers, then cancelled. They profit most in thin markets (`references/wiki/sources/spoofability-and-liquidity.md`). If large levels appear and vanish without trading, switch `fair` to `sized_mid` for that product.
- [ ] **Evaluation data:** is the round scored on the data you were given, or on fresh data? The leaderboard ranks each team's final submission on a private backtest, run after the deadline (Known so far, 2026-10-25), so the score that counts is probably on data we don't have. If fresh, trust the grid's `nbhd` and `min day` measures over its best `pnl`, and read its held-out days. Read its overfitting lines too, and run grids with `--modes all,worse`: change a setting only to the summary's `pick` (StepM's best cell that beats the bot as is under every mode, the rule of ten that lost least often on unseen Prosperity and simulated days, `IDEAS.md`, "Selection rules on unseen days"). A DSR below 0.95 alone is not a reason to keep the bot as is: on wide grids it is too strict (`references/wiki/contradictions.md`, row 18). With PBO near 50%, which cell wins is noise. Count every grid on the same data, and every public-backtest submission compared by score, as trials: the grid only counts its own cells. With only a few days and measures that disagree, the rehearsal took the best worst day. Check whether the download reuses earlier rounds' days, as Prosperity did: the grid flags it.
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

`python/bots/probe.py` answers most of the first-hour list in one playground run of about 420 ticks. It
runs probes 7, 1–2, 5, 3, 12, 4, 11, 17, 18, 13 and 9 in that order, each in its own window,
cancelling and flattening between them (except the lot probe 13 holds to the end). The three that can end the run come
last: 10 (importing numpy, pandas and scipy can be slow, and a sandbox that scans the source may refuse a file that uses
`importlib`), 6 (an exception) and 8 (sleeps up to 500 ms). They sit in one marked block, RISKY PROBES: if their rules
forbid dynamic imports or sleeps, or submissions are scarce, delete the block and upload the rest first. Each tick it prints a `SEEN` line with the book, position,
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
16. **Same trader, two oracles:** run one deterministic trader on the portal's public backtest and in our engine, and compare the fill lists. One team measured +2,415 locally against +436 live on the same window (`references/wiki/contradictions.md`, row 10). The portal's metrics (Known so far) are the quickest comparison once `arena.backtest` prints the same ones (`TODO.md`, "Print the portal's metrics in `arena.backtest`").
17. **Own impact:** in a quiet product, take the whole best ask once, then send nothing for 20 ticks. Compare those ticks' books with the same timestamps in the downloaded data: identical books mean a replay; a moved wall or a slow refill means the market reacts to us.
18. **Passive fills and their markout:** for a few hundred ticks, keep one lot at the best bid and one at the best ask, with no signal, re-posting when the price moves away. Record how often each fills and the mid 1, 10 and 50 ticks after each fill. Negative markouts mean the fills come with adverse moves (`references/wiki/sources/negative-drift-of-a-fill.md`); run the same orders in our engine on the same data and compare (as in probe 16). This is the live experiment of `references/wiki/sources/market-makers-dilemma.md` in miniature. On Prosperity data the template's own passive fills had no state with a negative value (`IDEAS.md`, "Passive fills' value by state"): run `uv run python -m experiments.quote_markouts --data <folder> --days <days> --format qminers --bot <our bot>` on the download too, and if some state's total is negative on every day, gate that side in `make`.
