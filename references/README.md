# Reference repos

Background reading for the Qminers Algo Trade Arena (7–8 Nov 2026, MFF UK, Prague).
Each folder is a shallow clone (`git clone --depth 1`) of a public GitHub repo.
Together they take about 2.6 GB, mostly market data. The clones are gitignored.
Run `./clone.sh` to fetch them (see [Cloning / updating](#cloning--updating)).
[`SEARCH_LOG.md`](SEARCH_LOG.md) records how they were chosen and what was rejected. Read it before searching again.
**[`wiki/index.md`](wiki/index.md) is the way into the clones: a wiki in Karpathy's LLM-wiki pattern with one page per repo, 17 concept pages that synthesise across them, a page of contradictions, and a lint (`python3 wiki/lint.py`). Start there on the day.**

For the theory behind the strategies (market making, order-book imbalance, price impact, position
sizing), see the papers converted to markdown in [../literature_md/](../literature_md/README.md).

This is third-party code, so read it before installing or running anything.
jmerle's backtesters and visualizer, the Prosperity 4 backtester, `hftbacktest`, DTU Quant Lab and the Qminers 2025 solution are MIT
(checked against their `LICENSE` files). The other team repos have no licence file, so use them
as reading material and write your own versions instead of pasting their code into a submission.
Every rank below is the team's own claim from its README. None is checked against the leaderboard.

## At a glance

| Folder | Source | What it is | Size | Last commit |
|---|---|---|---|---|
| `prosperity2-linear-utility/` | [ericcccsliu/imc-prosperity-2](https://github.com/ericcccsliu/imc-prosperity-2) | Team Linear Utility, **2nd of 9,000+** teams in IMC Prosperity 2 (2024). The best write-up here. | 419 MB | 2024-05-21 |
| `prosperity3-alpha-animals/` | [CarterT27/imc-prosperity-3](https://github.com/CarterT27/imc-prosperity-3) | Team Alpha Animals, **9th of 13,500+** in IMC Prosperity 3 (2025), peaking at 2nd. Includes a complete single-file `trader.py` submission. | 198 MB | 2025-04-26 |
| `prosperity3-backtester-jmerle/` | [jmerle/imc-prosperity-3-backtester](https://github.com/jmerle/imc-prosperity-3-backtester) | The open-source Prosperity 3 backtester, plus all Prosperity 3 market data. | 198 MB | 2025-04-25 |
| `prosperity2-backtester-jmerle/` | [jmerle/imc-prosperity-2-backtester](https://github.com/jmerle/imc-prosperity-2-backtester) | The same for Prosperity 2, with data for rounds 0, 1, 3 and 4. | 39 MB | 2024-04-23 |
| `prosperity3-visualizer-jmerle/` | [jmerle/imc-prosperity-3-visualizer](https://github.com/jmerle/imc-prosperity-3-visualizer) | Source of the visualizer for backtest logs. The [hosted version](https://jmerle.github.io/imc-prosperity-3-visualizer/) is easier to use. | <1 MB | 2025-04-21 |
| `algotrade2026-pitfa19/` | [pitfa19/algotrade2026](https://github.com/pitfa19/algotrade2026) | One team's bots and research from AlgoTrade 2026, a 24-hour hackathon in Zagreb (May 2026). | 1.2 GB | 2026-05-17 |
| `algotrade2026-negative-eevee/` | [alexbolfa/algotrade-negative-eevee](https://github.com/alexbolfa/algotrade-negative-eevee) | The **1st-place** AlgoTrade 2026 entry (their claim): a README on the strategy and four Rust files (a cross-exchange IOC arbitrage bot). All teams traded in one shared market. No licence file. Not yet read in depth. | <1 MB | 2026-05-12 |
| `prosperity3-frankfurt-hedgehogs/` | [TimoDiehm/imc-prosperity-3](https://github.com/TimoDiehm/imc-prosperity-3) | Frankfurt Hedgehogs, **2nd of 12,000+** in Prosperity 3 (2025). A long write-up plus their final `FrankfurtHedgehogs_polished.py`. Origin of the "wall mid". | <1 MB | 2025-06-23 |
| `prosperity4-baguette-fromage/` | [Durpie-Git/imc-prosperity-4](https://github.com/Durpie-Git/imc-prosperity-4) | Une Baguette Fromage, **4th of 18,803** in Prosperity 4 (2026). The most detailed write-up of the newest edition, with strategies in `Strategies/`. | 27 MB | 2026-07-11 |
| `prosperity4-du-trading/` | [FoxHenderson/imc-prosperity-4](https://github.com/FoxHenderson/imc-prosperity-4) | DU Trading, **10th globally** in Prosperity 4. Short, builds on the Frankfurt Hedgehogs write-up. Code for rounds 2, 4 and 5 only. | <1 MB | 2026-09-19 |
| `prosperity4-dtu-quant-lab/` | [DataAthleteChamp/dtu-quant-lab-imc-prosperity-4](https://github.com/DataAthleteChamp/dtu-quant-lab-imc-prosperity-4) | DTU Quant Lab, **28th** in Prosperity 4, a first-time team. Traders and data for every round, and `docs/literature_review.md`: which papers they shipped and which they killed in backtests. | 212 MB | 2026-06-06 |
| `prosperity4-ryan-challman/` | [nathanw3456/Prosperity_4_Writeup](https://github.com/nathanw3456/Prosperity_4_Writeup) | Team Ryan Challman, **57th** in Prosperity 4. Traders for rounds 3 to 5, and an honest "what didn't work" section. | 2 MB | 2026-07-21 |
| `prosperity4-alpha-search/` | [fabianbaiertum/IMC-Prosperity-4](https://github.com/fabianbaiertum/IMC-Prosperity-4) | Alpha Search Team, Prosperity 4. **README only**, the code isn't published. Claims 4th in round 4 (not overall), 23rd and 27th in the round 3 and 2 algorithmic rankings. | 3 MB | 2026-05-28 |
| `prosperity4-backtester/` | [nabayansaha/imc-prosperity-4-backtester](https://github.com/nabayansaha/imc-prosperity-4-backtester) | `prosperity4btest` on PyPI, the Prosperity 4 port of jmerle's backtester. **Includes the Prosperity 4 data**, rounds 0 to 5. | 192 MB | 2026-04-29 |
| `uchicago-trading-2026/` | [konnorlo/UChicago-Trading-Competition-2026](https://github.com/konnorlo/UChicago-Trading-Competition-2026) | Winner of the algorithmic case at the 2026 UChicago Trading Competition (1st of 41). A live exchange shared with other teams. README plus the organisers' `case-packet.pdf`. | 60 MB | 2026-05-11 |
| `uchicago-2025-case2-humzah/` | [HumzahM/UTC2025-Case2-Writeup](https://github.com/HumzahM/UTC2025-Case2-Writeup) | A #1 entry (their claim) on the **file-upload** case of the 2025 UChicago competition: a 100-line `Allocator` class plus a notebook explaining how they found the data's 10-tick structure. No licence file. | 7 MB | 2025-11-29 |
| `qminers-hackathon-2025/` | [vitktor/Qminers-Hackathon-2025](https://github.com/vitktor/Qminers-Hackathon-2025) | One team's solution to Qminers' own Quant Hackathon 2025 (sports betting), with the **organisers' files**: `src/environment.py` (their evaluation loop) and `problem_info_en.md`. A weak prior on how Qminers builds a competition. | 2 MB | 2026-10-08 |
| `qminers-hackathon-2024/` | [AdamBobocky/qminers-24](https://github.com/AdamBobocky/qminers-24) | The **1st-place team's post-mortem** of Qminers' Quant Hackathon 2024 (NBA betting), with the organisers' files: `COMPETITION_README.md`, `problem_info.md`, `src/submit_model/environment.py`. Shows the format (online qualification, then a reset 3-round final) and how the winner chose risk for the final. Weak prior on the task. | 90 MB | 2026-10-13 |
| `hftbacktest/` | [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest) | The reference open-source backtester for market making with queue position and latency models. We read it for its queue models and its tutorial notebooks (GLFT, order-book-imbalance alpha, queue-based quoting). | 131 MB | 2025-12-23 |

## How these relate to the Arena

**IMC Prosperity is the closest match to "submit a Python file each round."**
- You submit one file containing a `Trader` class.
- The engine calls `Trader.run(state)` once per tick, passing the order book, your position and recent trades. It returns your orders.
- Orders that don't fill are cancelled at the end of each tick.
- You trade only against the game's bots, never against other teams.
- If your orders for a product could take you past its position limit, the engine cancels all of them.

Prosperity also adds products each round, much like the Arena's plan of a forgiving first round building up to a sophisticated finale:

| Round | Prosperity 2 (2024) | Prosperity 3 (2025) | Prosperity 4 (2026) |
|---|---|---|---|
| 1 | Amethysts (fair value fixed at 10,000), Starfruit (random walk) | Rainforest Resin (fixed at 10,000), Kelp (random walk), Squid Ink (spiky, mean-reverting) | Ash-Coated Osmium (stationary around 10,000, wide spread), Intarian Pepper Root (drifts up 0.1 per tick) |
| 2 | Orchids: buy from another island; tariffs, shipping, sunlight and humidity data | Picnic baskets vs. their components (Croissants, Jams, Djembes) | The same two products, plus a blind bid for "extra market access" |
| 3 | Gift basket vs. chocolate, strawberries and roses | Volcanic Rock + vouchers (call options) | Hydrogel Pack, Velvetfruit Extract and its call vouchers (VEV_4000 to VEV_5500) |
| 4 | Coconut + coconut coupon (call option) | Magnificent Macarons: buy from another island, sunlight index | Counterparty names revealed (`Mark 01`, `Mark 22`, ...) |
| 5 | Counterparty names revealed | Counterparty names revealed | 50 products in 10 families of 5, position limit 10 each |

Prosperity 4 (from its write-ups) also made rounds 1 and 2 a qualifier and reset the leaderboard for rounds 3 to 5.

**AlgoTrade runs differently.** Bots run live on a team VM and connect to 10 simulated exchanges over
WebSocket. Network latency, rate limits and a reset every 10 minutes all shape the strategy.
Those mechanics won't apply to the Arena, but the way they analysed the market will.

**What the Arena site says about itself is the best evidence.** `ON_THE_DAY.md` ("Known so far") lists it:
a web portal where you upload one `.py` file per round, a capped number of submissions, a backtest on
public data, and a leaderboard weighted 10/20/30/40% over the four rounds. That looks much closer to
Prosperity's "submit a file, we run it" than to a live connection. The text is only in the site's
JavaScript bundle, which is why a plain page fetch found nothing.

**Qminers' earlier Quant Hackathon is only a weak prior.** The Arena is a different task and is
expected to be a big shift from it. The 2025 files in `qminers-hackathon-2025/` are still the only
look at how Qminers builds a competition:
- **A repo with everything but the hidden data:** the runtime environment (`pyproject.toml`, a conda file), **the evaluation loop the server runs** (`src/environment.py`), training data, and a stub.
- **One class, one method, pandas in and out.** You submit a class named `Model` with `place_bets(summary, opps, inc)`. It is called once per day with DataFrames and returns a DataFrame of bets.
- **All-or-nothing validation:** if a day's bets exceed the bankroll, `_validate_bets` rejects all of them. It's the same shape as Prosperity's limit rule.
- **Online qualification, then an in-person final** where finalists get new data and tune in real time. CTU's news says the 2024 final ran 6 hours over 3 rounds in which teams could react to each other.
- **What won (Qminers' own summaries):** simple models, strong risk management and bet sizing, and no overfitting.
- **The 2024 edition (`qminers-hackathon-2024/`) ran on the same evaluation loop** (only the columns changed), with the same 1 CPU / 5 GB limit and RTE / MLE / TLE statuses. Its winner's post-mortem adds: a 20-submission cap in the qualification, a leaderboard showing every team's score, runtime and RAM, scrambled finals data whose period was worth working out, and a final whose risk they sized by simulating the other finalists.

Editions in 2020, 2022, 2024 and 2025 were found, run with CTU's Intelligent Data Analysis group.

## Where to look

### `prosperity2-linear-utility/`
- `README.md`: read at least rounds 1, 3 and 4.
- `round1/round_1_v6.py`: their final round 1 submission, about 400 lines. It shows the take / make / clear pattern around a fair value.
- `round*/`: every round has its own copy of their backtester plus notebooks. `dashboard/` contains their Dash visualizer.

Lessons:
- **Use the large market-maker bot's mid as fair value.** For Starfruit they ignored small orders and used the mid of the bot quoting large size on both sides. Buying 1 unit and holding it showed the game marked PnL to that same price.
- **Clear inventory with zero-EV trades.** This frees room under the position limit for profitable trades and added about 3% to PnL.
- **Trade the basket spread with a z-score.** The spread is basket − components. They used a fixed mean and a short rolling standard deviation.
- **Expect live results to be worse than the backtest.** In round 3 the teams ahead of them had overfit more, which is how they climbed to 2nd.
- **Cut variance when you're ahead.** In round 4 they left delta exposure unhedged, lost money and fell from 2nd to 26th.
- **Look for quirks in how the game was built.** In round 5 they found that the previous year's public data predicted this year's prices almost perfectly (R² ≈ 0.99).

### `prosperity3-alpha-animals/`
- `trader.py` (1,800 lines) + `datamodel.py`: a complete single-file submission covering every product.
- `python/notebooks/`: basket spreads, volatility smile, a Kalman filter, and `counterparty_edge.ipynb`.
- `data/`: Prosperity 3 data for rounds 1–5.

Lessons:
- **The same fair-value trick worked for Kelp** (the large bot's mid). For Resin they hard-coded 10,000.
- **Position-limit bugs were their most expensive mistakes.** In round 2 their orders tried to exceed the limit, so the engine cancelled them and the basket strategy never ran.
- **Missing features in a backtester mislead you.** jmerle's backtester doesn't support conversions (buying from the other island). They misunderstood how conversions worked and lost money on conversion costs.
- **Score traders to find insiders.** Once names were revealed, they scored every trader on how well-timed their trades were. That surfaced "Olivia", whose trades they copied.

### `prosperity3-backtester-jmerle/` and `prosperity2-backtester-jmerle/`
- **Run it:** `pip install -U prosperity3bt`, then `prosperity3bt my_trader.py 1` backtests on all round 1 days. Add `--vis` to open the visualizer.
- **Use it as the template for your own backtester.** Read `prosperity3bt/runner.py` and the "Order Matching" section of its README. Orders match against the book first, then against market trades. `--match-trades worse` is the stricter fill rule Linear Utility used.
- **Data:**
  - Location: `prosperity3bt/resources/round{0..8}/`.
  - `prices_*.csv` has 3-level book snapshots, separated by `;`.
  - `trades_*.csv` has market trades. In Prosperity 2's `*_wn.csv` files they include buyer/seller names.
  - It's enough for practice and for the mock round.
- **Gotcha from the README:** Prosperity 3's Rainforest Resin data was identical to Prosperity 2's Amethysts data. Organisers reuse their generators, so check whether Arena rounds repeat data too.

### `prosperity3-visualizer-jmerle/`
- Use the hosted version to view logs. The source is useful mainly for its panels (PnL, position, the book at each tick, your orders vs. fills), which are worth copying into your own analysis notebook.

### `algotrade2026-pitfa19/`
- **Read with caution:**
  - This is probably not the winning team. Their notes guess at what "the leader" was doing.
  - Much of the documentation looks AI-written.
  - The PnL figures come from replaying recorded data, so they're optimistic, as the docs themselves admit.
- `.firecrawl/algotrade-participant-guide.md`: a copy of the official rules. It's a good example of what a hackathon spec covers.
- `analysis/mm_analysis.md`: reverse-engineers the built-in market maker. It quotes a ladder of 50-lot orders, and that pattern makes the bot identifiable. **This is the part that carries over best.**
- `analysis/etf_arb_map.md` covers ETF vs. constituent pricing. `analysis/cash_efficiency.md` argues that with zero fees, many small round trips beat a few large ones.
- `docs/VOIDMAKER_EDGE_PROOF.md`: rests orders at the legal price extremes (1 cent and 999,999) to catch other teams' bots sweeping through the book. This only works when teams share a market, so keep it in mind in case the Arena does.
- `tools/simple_mm_backtest.py`: a conservative replay that fills only against visible depth.
- **Note:** this repo contains its own `CLAUDE.md` and `AGENTS.md`. Claude Code reads them when it works inside this folder.

### `prosperity3-frankfurt-hedgehogs/` and `prosperity4-baguette-fromage/`
Read these two first among the new ones: 2nd in Prosperity 3 and 4th in Prosperity 4, and the second
builds on the first. Both are long, honest write-ups with the reasoning, not just the result.
- Frankfurt Hedgehogs: `README.md` (rounds 1 to 5, then an FAQ) and `FrankfurtHedgehogs_polished.py`.
- Baguette Fromage: `README.md` (the "Tools & Infrastructure", "Wall Mid" and round sections) and `Strategies/`.

Lessons:
- **Fair value is the "wall mid".** Both teams found the true price by buying 1 lot and reading the PnL. It matched the mid of the deepest, most stable bid and ask levels (the market maker's quotes), not the best bid and ask. This is our `wall_mid` option. Check on the day that the walls are still the exchange's.
- **Use the backtester as a filter, not as ground truth.** It has no market impact, a simplified book and imperfect bots. Discard what fails it, and distrust what looks too good (Baguette Fromage). Never optimise for the website's score either (Frankfurt Hedgehogs).
- **Organisers reuse their generators.** Prosperity 3's bots behaved like Prosperity 2's to over 95%, so teams hard-coded trades at known timestamps. Frankfurt Hedgehogs reported it and IMC fixed it. In Prosperity 4, takers reappeared at the same timestamp, side and size on the next day (97.7% for size 7 and up on Osmium). Look for repeats across days and rounds.
- **Empty book sides pay.** On both Prosperity 4 products, about 8% of the time a quote on an empty side was taken by a hidden taker. Baguette Fromage estimated that quoting about 100 from the wall mid was worth about 18.6k a day on Osmium alone.
- **A blind bid can be a trap.** Round 2's "extra market access" only meant about 20% more quotes, i.e. more competition. They bid 0. The median bid was 50.
- **Most counterparty names carried little signal** in Baguette Fromage's tests, while DU Trading found one informed buyer (Mark 67, velvetfruit). Test every name, and act only on the ones that survive.
- **Round 5 tempts you into overfitting.** With 50 products, in-sample scanners found "unlimited alpha". Baguette Fromage got more sceptical, not less.
- **AI-assisted work:** they kept exploratory tooling messy and "vibe coded", but production strategy code had to be understood line by line. They say preparation mattered "extremely".

### `prosperity4-dtu-quant-lab/`
- `docs/literature_review.md`: **the most useful file for us.** Every paper they read, with the round where they shipped it, or the reason they dropped it. They shipped Avellaneda–Stoikov, the micro-price, Huang–Lehalle–Rosenbaum's queue-reactive model, Guéant–Lehalle–Fernandez-Tapia, Black–Scholes with a parabola fit to the smile (Gatheral), and Avellaneda–Lee's statistical arbitrage. They dropped VPIN, PIN, Hawkes, square-root impact, Kalman betas, copulas, random-matrix trimming and OU-optimal exit thresholds.
- **Inventory skew on a pegged product is contested.** `round_1/README.md` says a fixed fair value with a micro-price refinement beat an Avellaneda–Stoikov reservation price on Osmium, which cost 16,593 in backtest before they reverted. Baguette Fromage's final Osmium quoter did the opposite: a reserve price shifted linearly with inventory (`10000 - γ·Q`, γ = 1/12). The numbers are theirs and we haven't reproduced either. DTU's literature table still lists A–S as shipped in rounds 1 to 4, so read `round_N/algorithmic/trader.py` for what was actually used. Test our `skew` on Resin-like products under `worse`, `--resting` and `--vs`.
- `docs/journey.md`: **a first-time team's honest arc** (2,609th after round 1, 1,742nd after round 3, 28th after round 5). A fixed-fair-value market maker kept buying into a 70-tick drift after the product stopped being pegged. The comeback came from splitting one big trader into per-cluster strategies (`ClusterStrategy`) and from a worst-day rule: **a variant only ships if its worst single backtest day is positive**.
- The same basket sum (`PEBBLES_XS + S + M + L + XL`) sat in a range of about 34 around 50,000 every day, which a dedicated arbitrage class took.
- `round_N/algorithmic/trader.py` for each round. Round 5's data is 110 MB of the 212 MB.

### `prosperity4-du-trading/`, `prosperity4-ryan-challman/` and `prosperity4-alpha-search/`
Shorter write-ups of the same competition, useful as second opinions.
- DU Trading (10th): `README.md`, then `round2.py`, `round4.py`, `round5.py`. It shows how they identified an informed counterparty (Mark 67, on velvetfruit) and traded on it with a 500-timestamp signal window.
- Ryan Challman (57th): the "Notes" section. A Black–Scholes-anchored voucher fair lost about 64,000 per strike in training, because the lag they took for a defect was the alpha. A layered ladder lost about 21,000 on Hydrogel. **Their main regret: they opened the new day's data too early**, so every later choice was tuned to it. The fix is to commit the change list in writing, then open the unseen data once. They also re-ran the whole parameter sweep after every change of baseline.
- Alpha Search (README only): the options rounds 3 and 4 and the 50-asset round 5, plus the manual-round maths.

### `prosperity4-backtester/`
- `prosperity4bt` is the Prosperity 4 port of jmerle's backtester. `prosperity4bt/resources/round{0..5}/` has the Prosperity 4 data in the same `;`-separated format (round 4 trades carry `Mark XX` buyer and seller names and a `currency` column).
- **This is practice data for our own backtester.** We only have Prosperity 2 and 3 today. Using it needs a `p4` alias and a limits entry per new product, which is small. It is a follow-up in `TODO.md`.
- Its `LIMITS` table only lists the 50 round 5 products. Everything else falls back to 50, so check the real limits for Osmium, Pepper Root, Hydrogel, Velvetfruit and the vouchers before relying on it.
- Fast alternative: [GeyzsoN/prosperity_rust_backtester](https://github.com/GeyzsoN/prosperity_rust_backtester), which Ryan Challman used to run a 50-variant sweep in minutes instead of an afternoon. We haven't cloned it.

### `uchicago-trading-2026/`
The only write-up here from a **live exchange shared with other teams**, which is what the Arena may turn out to be.
- It ran 12 rounds of 15 minutes, with ETF arbitrage, options (put-call parity, box spreads) and a prediction market. A round's score came from the team's rank, so a lead could be defended.
- Late-game adversaries: some teams bought out one side of a product's book and posted extreme prices on the other, trapping resting orders. Their defence was **not to post resting orders in products they were unsure about**. This is close to the "voidmaker" idea in `algotrade2026-pitfa19`, seen from the other side.
- The exchange froze sporadically. While it was frozen they couldn't flatten, and one freeze plus a news event on the prediction market cost about 200k in seconds.
- For the last round, they computed the rank they needed to keep first place overall and stopped the bot after about 8 minutes.
- `case-packet.pdf` is the organisers' spec, a second example of what a spec covers (after AlgoTrade's participant guide).

### `qminers-hackathon-2025/`
See [How these relate](#how-these-relate-to-the-arena) for what it shows about how Qminers runs a competition. Read `problem_info_en.md` and `src/environment.py`. `src/model.py` there is this team's own solution (gradient boosting on the bookmaker's odds, 25% fractional Kelly), not the organisers' stub. The stub's layout is described in other teams' READMEs, e.g. [BrystofKlazek/QMinersHackathon42](https://github.com/BrystofKlazek/QMinersHackathon42). The model itself matters little for the Arena apart from its sizing discipline.

### `qminers-hackathon-2024/`
Read `README.md` (the post-mortem, 10 minutes) and `COMPETITION_README.md` (the organisers' rules, in Czech). The points for the Arena are on `wiki/sources/qminers-hackathon-2024.md`. The model code is NBA-specific and unread. The user's own team repo for 2025 (`jakub-kucera/QQH-2025`, private) has a copy of this repo on its `kuca-ai-merge-2024` branch; its other branches are the organisers' 2025 files and the team's betting models.

### `hftbacktest/`
- **Our `--resting` queue model is hftbacktest's `RiskAdverseQueueModel`.** Compare `hftbacktest/hftbacktest/src/backtest/models/queue.rs` with the module docstring of `python/arena/engine.py`. Both do the same two things: a trade at the price reduces the volume ahead, and when the visible level shrinks below the volume ahead, the front is clipped to the new level size (`front = min(front, level)`). Their docs call this the most conservative model for fills.
- Their less conservative `ProbQueueModel` is the principled middle between our rule and the "front of the queue" option in `TODO.md`. When the level shrinks (after trades are subtracted), a share `prob` of the decrease is taken to be *behind* you and the rest ahead. `queue.rs` offers several `prob` functions: `f(back) / (f(back) + f(front))` with `f(x) = x**n` or `log(1 + x)`, `f(back) / f(back + front)`, and `1 - (front / (front + back))**n` (`PowerProbQueueFunc3`). The last is the family that fits Databento's order-by-order evidence; `log(1 + x)` blames the back more than uniform only while you are nearer the back, so it is not the realistic middle it was taken for (`wiki/sources/rigtorp-queue-position.md`, `wiki/sources/databento-queue-position.md`). `examples/Probability Queue Models.ipynb` compares them.
- `examples/` has tutorial notebooks worth skimming for ideas: GLFT market making (the paper is in `literature_md/`), order-book-imbalance as an alpha, queue-based quoting for large ticks, and the effect of order latency.
- We don't use it as a backtester. It replays event streams (depth changes and trades), while our data is one snapshot per tick, so we only borrow its ideas.

### Read online, not cloned

Looked at and judged worth a visit, but too big for what they add, or only worth one page.
- [chrispyroberts/imc-prosperity-3](https://github.com/chrispyroberts/imc-prosperity-3): CMU Physics, 7th in Prosperity 3 (and first in the US). A deep write-up per product in the README. The repo is 1.2 GB of data, so only the README is saved: `online-snapshots/chrispyroberts_imc-prosperity-3.README.md`. Read in part; the state-wipe incident (a logger pushed the submission over 100 MB and a Lambda restart wiped local variables) is in `wiki/sources/prosperity3-cmu-physics.md`.
- [Leo-Hawking/IMC-Prosperity-4-Review](https://github.com/Leo-Hawking/IMC-Prosperity-4-Review): top 0.5% in Prosperity 4, done by two people working with an AI agent and a `Claude.md`, the closest match to how we work. **Read its "Overall Retrospective".** LLMs drifted toward generic microstructure ideas (imbalance, latency, queue priority) instead of local alpha. A human and an AI agreeing entrenched a wrong belief (that the round 5 jumps had no alpha). One backtester shared across all rounds bloated, so they'd write a light one per round and keep only the matching layer generic. 245 MB, so the README is saved: `online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md`; see `wiki/sources/prosperity4-leo-hawking-review.md`.
- [heyman7913/imc-prosperity-4](https://github.com/heyman7913/imc-prosperity-4): JaneRT, 19th in Prosperity 4 (their claim). By its headings: micro-price fair value, Black–Scholes IV scalping, regime detection from the opening price, signals from named participants. 184 MB, so the README is saved: `online-snapshots/heyman7913_imc-prosperity-4.README.md`. Partly read (micro-price blend, opening-price regime, Mark 67 event study); see `wiki/sources/prosperity4-heyman7913.md`.
- [MarkBrezina/Ctrl-Alt-DefeatTheMarket](https://github.com/MarkBrezina/Ctrl-Alt-DefeatTheMarket): a community guide to Prosperity. Its `RESOURCES.md` lists the public repos of previous top teams by rank for Prosperity 1 to 3, and `Webinar notes.md` has IMC's answers (positions are zeroed at fair value at the end; speed doesn't matter, strategy does).
- [oscar-chw/imc-prosperity-4-shdc](https://github.com/oscar-chw/imc-prosperity-4-shdc) and [alexyesilyurt/imc-prosperity-writeup](https://github.com/alexyesilyurt/imc-prosperity-writeup) (83rd): short Prosperity 4 write-ups. SHDC's lesson: local replays warned them, and no go or no-go rule acted on the warning.
- [jmerle/imc-prosperity-2](https://github.com/jmerle/imc-prosperity-2) (9th) and [jmerle/imc-prosperity-3](https://github.com/jmerle/imc-prosperity-3) (25th): his own traders, plus a submitter and an optimizer. Also [Stanford Cardinal's Prosperity 1 repo](https://github.com/ShubhamAnandJain/IMC-Prosperity-2023-Stanford-Cardinal) (2nd).
- [GeyzsoN/prosperity_rust_backtester](https://github.com/GeyzsoN/prosperity_rust_backtester): a Rust port that agrees with the Python backtester and runs about 10 times faster. It ships the Prosperity 4 data too.
- [Diego-2510/prosperity4-mark-analyzer](https://github.com/Diego-2510/prosperity4-mark-analyzer): a CLI and dashboard that labels counterparties from their flow. Only relevant if the Arena names counterparties.
- [Optiver Ready Trader Go](https://readytradergo.optiver.com/) (2021 to 2023): the kit is mirrored at [jpli02/Optiver_autotrader](https://github.com/jpli02/Optiver_autotrader) (AGPL, so read only). **Its autotrader is event-driven**: callbacks such as `OrderBookMessageHandler`, `OrderFilledMessageHandler` and `HedgeFilledMessageHandler`, against an exchange simulator you can read, with four market data files. It is the model for the event-driven case in `ON_THE_DAY.md`. No winning bot is public that we could find.
- Rigtorp, Databento and the Quant.SE thread on queue position, and Hummingbot's two Avellaneda–Stoikov posts, now have local copies and source pages (`wiki/sources/rigtorp-queue-position.md`, `databento-queue-position.md`, `quant-se-order-position.md`, `hummingbot-avellaneda-stoikov.md`). The finding that matters: on Databento's one measured order, cancels came almost all from behind, close to our `--resting` rule, and `log(1 + x)` is not the back-biased middle the TODO assumed.
- [Competing at the 2026 UChicago Trading Competition](https://www.cs.utexas.edu/~kavish/blog/uchicago-trading-competition-2026.html): another team's account of the same market-making case. Its fair-value model worked and its execution failed once the books thinned. Orders of 40 walked the book, and unwinding 200 in chunks moved the price against it.
- [cryptotradingaddiction/TradingArenaPrep](https://github.com/cryptotradingaddiction/TradingArenaPrep): someone else's practice lab for this Arena (4 commits, no stars). Its `on_start`, `on_book`, `on_fill` and `on_end` callbacks are the author's guess, not Qminers' API, so don't rely on it.
- [ABIDES](https://github.com/abides-sim/abides) ([paper](https://arxiv.org/abs/1904.12066)): an agent-based market simulator with zero-intelligence and market-making agents. The way to model rivals properly, but far heavier than `--vs`.
- Found since: the AlgoTrade 2026 winners' write-up is `algotrade2026-negative-eevee/` (the link in their LinkedIn post, `lnkd.in/eeVSBCnW`, only shows in the page's HTML). The official Prosperity wikis (Notion) are downloaded to `prosperity-wikis/` by `fetch_notion.py`; see below. Timo Diehm's article ["How to (Almost) Win Against Thousands of Other Teams"](https://medium.com/@td.timodiehm/how-to-almost-win-against-thousands-of-other-teams-in-competitive-environments-bc31387e4b26) returns a 403 to our fetch tool; the user printed it to PDF and it is in `literature_raw/`, converted to `literature_md/how-to-almost-win/`. The Quant.SE queue-position thread is blocked for our fetch tool; the user printed it to PDF on 2026-10-13 (`literature_md/quant-se-order-position/`).

## Suggested reading order (about 6 hours)

1. Linear Utility `README.md`, rounds 1 and 3.
2. `prosperity2-linear-utility/round1/round_1_v6.py`: the take / make / clear pattern in about 400 lines.
3. Install `prosperity3bt`, write a small trader for Rainforest Resin and Kelp, backtest it on round 1 and view the result in the visualizer.
4. Alpha Animals `README.md`, then skim `trader.py`.
5. AlgoTrade `analysis/mm_analysis.md` and the participant guide.
6. Qminers' own files: `qminers-hackathon-2025/problem_info_en.md` and `src/environment.py` (15 minutes), then the 2024 winner's `qminers-hackathon-2024/README.md` (10 minutes). They're the only evidence of how Qminers builds a competition.
7. Frankfurt Hedgehogs `README.md` (round 1 and the FAQ), then Baguette Fromage's "Tools & Infrastructure", "A Note on Backtester Limitations" and "Wall Mid".
8. DTU Quant Lab `docs/literature_review.md` and `docs/journey.md`, then Ryan Challman's "Notes".
9. The "Overall Retrospective" of Leo-Hawking's review, which is about working with an AI agent.

## Cloning / updating

```sh
references/clone.sh            # clone any missing repo, and put every clone on its pinned commit
references/clone.sh --check    # only report clones that aren't on their pin (exit 1 if any)
references/clone.sh --update   # move every repo to its newest commit and rewrite the pins
```

Each repo is pinned to a commit in `clone.sh`. The wiki's `path:line` citations, the Prosperity
data, the parity test and the results in `IDEAS.md` were made on those commits, so every machine
must be on them; `python/tests/test_references.py` fails for a clone that isn't. `--update` is a
deliberate step: it prints each repo it moves, old and new commit. Then run
`python3 references/wiki/lint.py` and `uv run pytest`, re-check the citations into any repo that
moved (the lint only checks that a cited line exists), and commit `clone.sh`.

The repo list lives in `clone.sh`. To add a repo, add a line there with its current commit
(`git ls-remote https://github.com/<owner>/<repo>.git HEAD`) and a row to the table above.
Only `README.md`, `clone.sh`, `SEARCH_LOG.md`, `check_arena_site.py` with its snapshot, `fetch_notion.py`, `algo_trade_arena_conversation.json` (the first conversation about the Arena, 2026-10-07, whose first message is the organisers' e-mail with the schedule; `ON_THE_DAY.md`, "Known so far") and `wiki/` are committed; the root `.gitignore` ignores everything else in `references/`.

`check_arena_site.py` re-reads the Arena site and diffs it against `arena-site-snapshot.txt`. Run it every few days before the event, and `--save` after reading a change.

### Prosperity wikis (Notion)

The official wikis are public Notion pages, which a plain page fetch cannot read. `fetch_notion.py` asks the JSON endpoints a browser uses and writes markdown (images and databases are not downloaded; images stay as links). The output goes to `prosperity-wikis/` (gitignored, third-party text):

```sh
python3 -I references/fetch_notion.py references/prosperity-wikis \
  prosperity2=https://imc-prosperity.notion.site/Prosperity-2-Wiki-fe650c0292ae4cdb94714a3f5aa74c85 \
  prosperity3=https://imc-prosperity.notion.site/Prosperity-3-Wiki-19ee8453a09380529731c4e6fb697ea4 \
  prosperity4=https://imc-prosperity.notion.site/Prosperity-4-Wiki-321e8453a093805fbd4bde63ccbf9218
```

Downloaded 2026-10-11: Prosperity 2 (17 pages), 3 (36) and 4 (19). Each folder has an `INDEX.md`. The most useful pages for us are the Prosperity 4 *Writing an Algorithm in Python* (the `Trader`, `TradingState` and `Order` classes, position limits, supported libraries), *Game Mechanics Overview*, *Rules*, *FAQ* and the five round pages. The five empty "Round N" pages in the Prosperity 3 folder are empty at the source (a "[Staging]" copy of the wiki).
