# Reference repos

Background reading for the Qminers Algo Trade Arena (7–8 Nov 2026, MFF UK, Prague).
Each folder is a shallow clone (`git clone --depth 1`) of a public GitHub repo.
Together they take about 2 GB, mostly market data. The clones are gitignored.
Run `./clone.sh` to fetch them (see [Cloning / updating](#cloning--updating)).

For the theory behind the strategies (market making, order-book imbalance, price impact, position
sizing), see the papers converted to markdown in [../literature_md/](../literature_md/README.md).

This is third-party code, so read it before installing or running anything.
Only jmerle's three repos have a licence (MIT). The team repos have none, so use them
as reading material and write your own versions instead of pasting their code into a submission.

## At a glance

| Folder | Source | What it is | Size | Last commit |
|---|---|---|---|---|
| `prosperity2-linear-utility/` | [ericcccsliu/imc-prosperity-2](https://github.com/ericcccsliu/imc-prosperity-2) | Team Linear Utility, **2nd of 9,000+** teams in IMC Prosperity 2 (2024). The best write-up here. | 419 MB | 2024-05-21 |
| `prosperity3-alpha-animals/` | [CarterT27/imc-prosperity-3](https://github.com/CarterT27/imc-prosperity-3) | Team Alpha Animals, **9th of 13,500+** in IMC Prosperity 3 (2025), peaking at 2nd. Includes a complete single-file `trader.py` submission. | 198 MB | 2025-04-26 |
| `prosperity3-backtester-jmerle/` | [jmerle/imc-prosperity-3-backtester](https://github.com/jmerle/imc-prosperity-3-backtester) | The open-source Prosperity 3 backtester, plus all Prosperity 3 market data. | 198 MB | 2025-04-25 |
| `prosperity2-backtester-jmerle/` | [jmerle/imc-prosperity-2-backtester](https://github.com/jmerle/imc-prosperity-2-backtester) | The same for Prosperity 2, with data for rounds 0, 1, 3 and 4. | 39 MB | 2024-04-23 |
| `prosperity3-visualizer-jmerle/` | [jmerle/imc-prosperity-3-visualizer](https://github.com/jmerle/imc-prosperity-3-visualizer) | Source of the visualizer for backtest logs. The [hosted version](https://jmerle.github.io/imc-prosperity-3-visualizer/) is easier to use. | <1 MB | 2025-04-21 |
| `algotrade2026-pitfa19/` | [pitfa19/algotrade2026](https://github.com/pitfa19/algotrade2026) | One team's bots and research from AlgoTrade 2026, a 24-hour hackathon in Zagreb (May 2026). | 1.2 GB | 2026-05-17 |

## How these relate to the Arena

**IMC Prosperity is the closest match to "submit a Python file each round."**
- You submit one file containing a `Trader` class.
- The engine calls `Trader.run(state)` once per tick, passing the order book, your position and recent trades. It returns your orders.
- Orders that don't fill are cancelled at the end of each tick.
- You trade only against the game's bots, never against other teams.
- If your orders for a product could take you past its position limit, the engine cancels all of them.

Prosperity also adds products each round, much like the Arena's plan of a forgiving first round building up to a sophisticated finale:

| Round | Prosperity 2 (2024) | Prosperity 3 (2025) |
|---|---|---|
| 1 | Amethysts (fair value fixed at 10,000), Starfruit (random walk) | Rainforest Resin (fixed at 10,000), Kelp (random walk), Squid Ink (spiky, mean-reverting) |
| 2 | Orchids: buy from another island; tariffs, shipping, sunlight and humidity data | Picnic baskets vs. their components (Croissants, Jams, Djembes) |
| 3 | Gift basket vs. chocolate, strawberries and roses | Volcanic Rock + vouchers (call options) |
| 4 | Coconut + coconut coupon (call option) | Magnificent Macarons: buy from another island, sunlight index |
| 5 | Counterparty names revealed | Counterparty names revealed |

**AlgoTrade runs differently.** Bots run live on a team VM and connect to 10 simulated exchanges over
WebSocket. Network latency, rate limits and a reset every 10 minutes all shape the strategy.
Those mechanics won't apply to the Arena, but the way they analysed the market will.

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
- `notebooks/`: basket spreads, volatility smile, a Kalman filter, and `counterparty_edge.ipynb`.
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

## Suggested reading order (about 4 hours)

1. Linear Utility `README.md`, rounds 1 and 3.
2. `prosperity2-linear-utility/round1/round_1_v6.py`: the take / make / clear pattern in about 400 lines.
3. Install `prosperity3bt`, write a small trader for Rainforest Resin and Kelp, backtest it on round 1 and view the result in the visualizer.
4. Alpha Animals `README.md`, then skim `trader.py`.
5. AlgoTrade `analysis/mm_analysis.md` and the participant guide.

## Cloning / updating

```sh
references/clone.sh            # clone any repo that's missing (skips existing ones)
references/clone.sh --update   # also pull the ones already cloned
```

The repo list lives in `clone.sh`. To add a repo, add a line there and a row to the table above.
Only `README.md` and `clone.sh` are committed; the root `.gitignore` ignores everything else in `references/`.
