# Ideas and what the Prosperity data said

Every strategy idea we have tested on Prosperity data, with its result, and the ideas still waiting for a test.

**A result here is a prior about the Arena, not a verdict.** The Arena's products, bots, matching and scoring will differ from Prosperity's. So an idea that loses here stays on this list, marked `dropped here`, and is tested again on the Arena's data. An idea that wins here is tested again too. `ON_THE_DAY.md` ("Every round") points here.

**Keeping it up to date:**
- When a test runs, add the result to its row: the date, the data, the command and the numbers. Keep the earlier results and add the new one under them.
- Each verdict is one of these:
  - `kept`: it is in the template;
  - `dropped here`: it is not in the template, and is re-tested on the day anyway;
  - `measured`: a fact about the data, not a strategy;
  - `open`: tested, with no conclusion yet.
- On the day, for each round, go down the "Re-test on the Arena" column and run the rows whose condition fits that round's products.

## Tested on Prosperity data

| Idea | Result on Prosperity data | Verdict here | Re-test on the Arena |
|---|---|---|---|
| **The template's market maker** (take, clear, make; fixed fair for Resin, `wall_mid` for Kelp) | P3 round 1, all days: 81,292 per tick with `--match-trades all`, 57,774 with `worse`, 28,216 with `none`; 68,043 with `--resting` (`README.md`, "Fill assumptions matter") | `kept` | The first backtest on the Arena's data, in every fill mode, then compare with a playground run (`ON_THE_DAY.md`, "Which backtest settings match the playground?") |
| **Kelp `make_edge` and `take_edge`** | P3 round 1 grid: `make_edge=1, take_edge=1` best by PnL, neighbourhood and worst day under `all` (81,292); `make_edge=0` best under `worse` (63,068). With `--resting`, `make_edge=0` loses 12,474 against one copy of the baseline (`README.md`) | `kept`: `make_edge=1` | Grid each product's edges with `--modes all,worse`; add `--vs` if the market is shared |
| **The template against copies of itself** | P3 round 1: alone 81,292; with one copy 46,875 + 47,674 (per tick) and 32,876 + 33,551 (`--resting`); with two copies about 20,600 each (`README.md`) | `measured` | Only if the Arena is shared (`ON_THE_DAY.md`, "Is the market shared with the other teams?") |
| **The template against the teams' P4 traders in one market** (DU `round2.py`, Baguette Fromage `Phase1.py`, DTU's round 2 trader; one at a time and all three) | 2026-10-13, P4 rounds 1–2, all days, through `arena.engine.run_market` as `--vs` does. In `--resting` the teams' bots were wrapped to cancel all their open orders every tick, so they re-quote each tick as they were written to (the script is not in the repo). <br>**Default mode** (orders live one tick): <br>- **Osmium is shared:** its spread is a fixed pie of 55–62k a round that the bots split. The template keeps 45–51% of it against one rival and 20% against all three. Round 1: alone 53.9k; against DU 25.4k, Baguette Fromage 28.6k, DTU 29.5k; against all three 12.6k. <br>- **Pepper Root's drift pays everyone:** the template makes 232.6k alone and 228.4k against all three. <br>- **Totals against all three:** the template comes last, 241.0k against 253.3–255.4k (round 1) and 238.8k against 254.9–256.9k (round 2). <br>**`--resting`:** the template loses on Osmium. Round 1: −46k against DU, −374k against Baguette Fromage, −377k against all three, where DU makes +221k. Round 2: −43k, −434k and −445k. <br>- **The cause** *(checked on round 1, day 0, against Baguette Fromage)*: a rival's resting order far from fair can be larger than the market maker's wall, and `_wall` picks it. At tick 2,400 a 40-lot bid at 9,906 beat the 23-lot wall at 9,991, and the template's fair became 9,957 against a recorded 10,001.5. The template then sold into the real bids. The fair it saw was 5+ off on 36% of ticks. <br>- **Default mode is immune:** rivals' orders are never visible there. <br>- **Baguette Fromage is hit too:** it loses 65–80k on Osmium against DU and DTU in the same setting (cause not analysed) | `measured`; under `--resting`, a flaw in `wall_mid` (fix candidates: the wall-mid definitions row) | If the market is shared: run `--vs` with every rival bot available, in the engine mode the playground matches. Check that the fair value ignores large orders far from the touch (`ON_THE_DAY.md`, "Is `wall_mid` still the market maker's price?") |
| **`skew` against Kelp's long position** | Kelp sits at +50 about 10% of the time, and `skew` didn't fix it; no numbers recorded (`TODO.md`, "Explain Kelp's long drift") | `dropped here` (default 0.0) | Sweep `skew` per product, using the coefficient the literature gives (`references/wiki/concepts/optimal-quoting-models.md`) |
| **Untuned `wall_mid` market making on P4 rounds 1–2** (Osmium, Pepper Root; limit 80, `make_edge=1`) | 2026-10-12, `uv run python -m arena.backtest bots/template.py 1 --data p4` (then `2`). Round 1: 169,627 (Osmium 53,893, Pepper Root 115,734). Round 2: 27,700 (Osmium 59,915, Pepper Root −32,215). Pepper Root rises about 1,000 a day in both rounds, yet loses in round 2: unexplained | `kept` for Osmium; `dropped here` for Pepper Root: the published traders hold a long position and earn about 80k a day from the drift (next row) | For a drifting product, compare PnL across rounds and days before trusting one; never tune on one round |
| **A long bias on a drifting product** (Pepper Root; DU holds +76, Baguette Fromage a DP model, DTU the limit) | 2026-10-13, the teams' own files in our engine, P4 rounds 1–2 (`references/wiki/sources/prosperity4-du-trading.md` and the DTU and Baguette Fromage pages): Pepper Root alone earns 82–84k a day for DU and Baguette Fromage, 79–80k for DTU's round 2 trader at the full limit of 80, and 49.6k for its round 1 trader capped at 50. The template's market making on it: −25k to +58k a day <br>2026-10-13, a `target` position in the template (`clear` and `skew` work toward it): grid on P4 rounds 1–2, `uv run python -m arena.grid bots/template.py 1 2 --data p4 --grid PARAMS.INTARIAN_PEPPER_ROOT.target=0,40,60,76,80 --grid PARAMS.INTARIAN_PEPPER_ROOT.skew=0,2,5,10 --modes all,worse`, then skew 10–80. Target 80 is best by PnL, neighbourhood, worst day and `worse` fills; skew 10–80 is a plateau (570–576k over the 6 days). With target 80 and skew 20 the template makes 286,496 on round 1 and 289,066 on round 2, Pepper Root 76–78k a day | `kept`: `target` 80, `skew` 20 for Pepper Root | For a product with a steady drift, set `target` toward the drift (the limit, or short of it) and grid `target` and `skew`; never take the value from Prosperity |
| **Do the bots' market trades move the fair value?** | 2026-10-12, P2 round 1 and P3 rounds 1–2: against the wall mid the lasting move is near zero except in the baskets, and takers pay 0.6–2.2 ticks a unit (`references/wiki/concepts/price-impact.md`) | `measured`: quoting near the wall loses little to adverse selection | `analysis.trade_impact` on the first download (printed by `uv run python -m arena.analysis <out>`). If the wall mid follows trades, widen or skew on that product |
| **Do the template's takes earn?** | 2026-10-12, P3 round 1, `analysis.pnl_split`: on day −1, Resin's takes show −6,048 against the mark and +6,272 against the wall mid; Kelp's −1,743 and +1,298. The mark at the fill tick is skewed by the order taken | `measured`: judge takes against the wall mid | `uv run python -m arena.analysis <out> --reference wall_mid` on the first Arena backtest |
| **Does market making pay here, by the textbook's test?** (Bouchaud et al. ch. 17: half the spread against the long-run impact) | 2026-10-13, P3 round 1, the data's market trades: slow margin `−edge − R(50)` and fast margin `−edge·(1 − C(1)) − R(1)` (the book's `s/2` measured as the taker's cost) are 0.94 and 0.81 for Kelp, 1.41 and 1.27 for Resin, 0.95 and 0.80 for Squid Ink against the wall mid, about the same against the mid; 0.2–0.4 of the spread. Rerun with `uv run python -m arena.diagnose 1 --data p3`. Trade-sign correlation `C(1)` 0.09–0.13, against 0.37–0.93 on NASDAQ (`references/wiki/sources/trades-quotes-prices.md`) | `measured`: Prosperity is the zero-intelligence case where making is easy | Run `arena.diagnose` on the first download and again if rivals appear: a margin near zero means the market is competitive, so quote less tightly and lean on signals |
| **How noisy are the mid and the wall mid?** | 2026-10-12, P3 round 1: Kelp's mid varies 28 times more per tick at lag 1 than at lag 200, its wall mid 3 times. Lag-1 autocorrelation of mid changes: −0.48 Kelp, −0.50 Resin, −0.17 Squid Ink (`references/wiki/concepts/fair-value-and-wall-mid.md`) | `measured`: supports `wall_mid` | The signature plot of the mid and each wall-mid definition on the first download |

## Benchmark: the template against the published P4 traders

The teams' own files in our engine (2026-10-13; commands on each team's page under `references/wiki/sources/`). **These are the teams' traders on the days they were built on, so they overstate what they did live.** DTU's 3-day backtests were 135,842 (round 3), 116,090 (round 4) and 501,498 (round 5); its live single days were +3,686, +25,351 and +702,835.

**Rounds 1–2, PnL per day.** The template is level with DTU's round 2 trader and 6–9k a day behind the best:

| Trader | Round 1 | Round 2 |
|---|---|---|
| Template (Pepper Root `target` 80) | 93.9–96.8k | 96.0–96.7k |
| DTU, round 2 trader | 95.5–97.0k | 97.4–98.7k |
| DU, `round2.py` | 100.6–102.1k | 103.0–105.0k |
| Baguette Fromage, `Phase1.py` | 101.9–102.8k | 104.2–105.6k |

**Rounds 3–5, PnL over each round's 3 days, in thousands.** "Template" here is plain market making around `wall_mid` on every product: for each product, `--set 'PARAMS.<PRODUCT>={"limit": <limit>, "fair": "wall_mid", "make_edge": 1}'`. Rounds 3 and 4 share days 1 and 2, so they hold 4 distinct days, not 6.

| Round | Products | Template | DTU | Baguette Fromage | DU |
|---|---|---|---|---|---|
| 3 | VEV vouchers (options) | 11.6 | 47.2 | 604.3 | 366.9 |
| 3 | Hydrogel | 29.5 | 55.5 | 148.8 | 64.8 |
| 3 | Velvetfruit (the vouchers' underlying) | 14.6 | 33.2 | 98.1 | 73.2 |
| 4 | VEV vouchers | 11.3 | 40.0 | 620.2 | 382.5 |
| 4 | Hydrogel | 27.4 | 47.2 | 161.8 | 67.0 |
| 4 | Velvetfruit | 4.9 | 28.9 | 106.5 | 74.7 |
| 5 | Robots (the round-number jumps) | 11.1 | 9.2 | 508.5 | 308.6 |
| 5 | Oxygen shakes | 76.7 | 167.1 | 147.5 | 62.0 |
| 5 | Pebbles (fixed sum) | 33.7 | 54.0 | 73.6 | 56.2 |
| 5 | Microchips | 20.3 | 45.6 | 51.5 | 46.2 |
| 5 | The other six families | 316.0 | 225.6 | 310.0 | 253.4 |
| | **Total, rounds 3 / 4 / 5** | 55.7 / 43.6 / 457.8 | 135.8 / 116.1 / 501.5 | 851.2 / 888.6 / 1,091.0 | 505.0 / 524.3 / 726.5 |

What it says, as priorities for strategy work:
1. **Options** are the largest gap: about 610k against 11k on the vouchers.
2. **Fading the round-number jumps** (the Robots in round 5): 309–509k against 11k.
3. **The spot products of rounds 3–4** (Hydrogel, Velvetfruit): 100–160k each for Baguette Fromage against 5–30k.
4. **Plain market making holds its own** on the other six round 5 families: 316k against 226–310k for the teams. It leads on Galaxy Sounds and Panels and trails mainly on Sleep Pods (54k against Baguette Fromage's 75k).

## Not yet tested

| Idea | Where it comes from | Test, and where it would go |
|---|---|---|
| Other wall-mid definitions: outermost levels, first level with volume ≥ 15, DTU's | `references/wiki/concepts/fair-value-and-wall-mid.md`; contradictions row 2 | `TODO.md`, "Compare the wall mid definitions"; a `fair` option |
| The micro-price or weighted mid as fair value | `references/wiki/concepts/book-imbalance-and-micro-price.md`; row 11 | `TODO.md`, "Try the literature's fair values"; a `fair` option |
| Book imbalance `ρ` as a short-term signal | Same page; row 11. Strong only at 1-tick spreads in the literature | Gould & Bonart's test per product and day first; then a skew or fair adjustment |
| heyman7913's blend: 0.30 × volume-weighted mid + 0.70 × slow EMA + 2.0 × `ρ` | `references/wiki/sources/prosperity4-heyman7913.md` | `TODO.md`, "Try the literature's fair values" |
| The skew coefficient from GLFT's closed form (`σ`, `A`, `k`, one `γ`) | `references/wiki/concepts/optimal-quoting-models.md` | Measure per product, sweep `γ`; sets `skew` |
| Skew on a pegged product | Row 1: DTU lost 16,593 with one on Osmium, Baguette Fromage shipped one | Now testable with `--data p4` round 1: sweep `skew` on Osmium |
| Skewing on correlated products' inventory too (Guéant's `Γ`) | `references/wiki/concepts/many-products-architecture.md` | A cross-product hook in STRATEGY (`TODO.md`, "Add multi-product strategies") |
| Using less than the full position limit | Row 14 (Kelly against full-room quoting) | Grid `make_size` per product, compare mean against worst-day PnL; decide by the Arena's scoring rule |
| Basket spread trading with optimal entry and exit bands | `references/wiki/concepts/baskets-and-fixed-sums.md` | `TODO.md`, "Add multi-product strategies"; P3 round 2, P2 round 3 |
| Inventory control through quote size instead of price: `υ₀·max(1 + κψε, 0)` per side | Bouchaud et al. eq. 17.4 (`references/wiki/sources/trades-quotes-prices.md`); Harris's "change the sizes" | A `size_skew` parameter in `make`, gridded against `skew` per product |
| Posting a side only when the edge beats the expected adverse move | Row 12 (Cartea et al. 2018) | Needs wall-mid markouts first; then a per-side rule in `make` |
| Fading round-number jumps (take the other side, hold three ticks) | `references/wiki/concepts/jumps-and-snap-back.md`; the second-largest gap in the benchmark (Robots, round 5) | P4 round 5 data, now loadable with `--data p4` |
| Quoting far away when one side of the book is empty | `references/wiki/concepts/hidden-takers-and-empty-sides.md` | Probe 14 in `ON_THE_DAY.md`; P4 data has empty sides (781 bid-less rows on round 1 day 0) |
| Following informed counterparties (Olivia, the Marks) | `references/wiki/concepts/informed-counterparties.md`; row 3 | Per-name forward returns, leave-one-day-out, on P3 round 5 and P4 round 4 |
| Options: implied volatility, the smile, delta hedging | `references/wiki/concepts/options-and-vouchers.md`; row 6; the largest gap in the benchmark | `TODO.md`, "Prepare the other later-round mechanics"; P3 round 3, P4 rounds 3–4 |
| Trading a spot product that reverts to a level (Hydrogel, Velvetfruit) | `references/wiki/concepts/drift-and-regime-change.md`; the third-largest gap in the benchmark | P4 rounds 3–4; start from what the teams' files do on these two products |
| Other strategies for a drifting product (Baguette Fromage's dynamic-programming model, accumulate then revert); the long bias is tested above | `references/wiki/concepts/drift-and-regime-change.md`; row 7 | P4 rounds 1–2, Pepper Root: the gap to the best is about 6k a day |
| Flattening before the close | `references/wiki/concepts/risk-and-protecting-a-lead.md` | `TODO.md`, "Let the template flatten before the close" |
