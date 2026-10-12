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
| **`skew` against Kelp's long position** | Kelp sits at +50 about 10% of the time, and `skew` didn't fix it; no numbers recorded (`TODO.md`, "Explain Kelp's long drift") | `dropped here` (default 0.0) | Sweep `skew` per product, using the coefficient the literature gives (`references/wiki/concepts/optimal-quoting-models.md`) |
| **Untuned `wall_mid` market making on P4 rounds 1–2** (Osmium, Pepper Root; limit 80, `make_edge=1`) | 2026-10-12, `uv run python -m arena.backtest bots/template.py 1 --data p4` (then `2`). Round 1: 169,627 (Osmium 53,893, Pepper Root 115,734). Round 2: 27,700 (Osmium 59,915, Pepper Root −32,215). Pepper Root rises about 1,000 a day in both rounds, yet loses in round 2: unexplained | `kept` for Osmium; `dropped here` for Pepper Root: the published traders hold a long position and earn about 80k a day from the drift (next row) | For a drifting product, compare PnL across rounds and days before trusting one; never tune on one round |
| **A long bias on a drifting product** (Pepper Root; DU holds +76, Baguette Fromage a DP model, DTU the limit) | 2026-10-13, the teams' own files in our engine, P4 rounds 1–2 (`references/wiki/sources/prosperity4-du-trading.md` and the DTU and Baguette Fromage pages): Pepper Root alone earns 82–84k a day for DU and Baguette Fromage, 79–80k for DTU's round 2 trader at the full limit of 80, and 49.6k for its round 1 trader capped at 50. The template's market making on it: −25k to +58k a day | `measured`: not in the template yet (row 7 of the contradictions) | For any product with a steady drift, compare holding toward the limit with market making around the drift, per day |
| **Do the bots' market trades move the fair value?** | 2026-10-12, P2 round 1 and P3 rounds 1–2: against the wall mid the lasting move is near zero except in the baskets, and takers pay 0.6–2.2 ticks a unit (`references/wiki/concepts/price-impact.md`) | `measured`: quoting near the wall loses little to adverse selection | `analysis.trade_impact` on the first download (printed by `uv run python -m arena.analysis <out>`). If the wall mid follows trades, widen or skew on that product |
| **Do the template's takes earn?** | 2026-10-12, P3 round 1, `analysis.pnl_split`: on day −1, Resin's takes show −6,048 against the mark and +6,272 against the wall mid; Kelp's −1,743 and +1,298. The mark at the fill tick is skewed by the order taken | `measured`: judge takes against the wall mid | `uv run python -m arena.analysis <out> --reference wall_mid` on the first Arena backtest |
| **How noisy are the mid and the wall mid?** | 2026-10-12, P3 round 1: Kelp's mid varies 28 times more per tick at lag 1 than at lag 200, its wall mid 3 times. Lag-1 autocorrelation of mid changes: −0.48 Kelp, −0.50 Resin, −0.17 Squid Ink (`references/wiki/concepts/fair-value-and-wall-mid.md`) | `measured`: supports `wall_mid` | The signature plot of the mid and each wall-mid definition on the first download |

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
| Posting a side only when the edge beats the expected adverse move | Row 12 (Cartea et al. 2018) | Needs wall-mid markouts first; then a per-side rule in `make` |
| Fading round-number jumps (take the other side, hold three ticks) | `references/wiki/concepts/jumps-and-snap-back.md` | P4 round 5 data, now loadable with `--data p4` |
| Quoting far away when one side of the book is empty | `references/wiki/concepts/hidden-takers-and-empty-sides.md` | Probe 14 in `ON_THE_DAY.md`; P4 data has empty sides (781 bid-less rows on round 1 day 0) |
| Following informed counterparties (Olivia, the Marks) | `references/wiki/concepts/informed-counterparties.md`; row 3 | Per-name forward returns, leave-one-day-out, on P3 round 5 and P4 round 4 |
| Options: implied volatility, the smile, delta hedging | `references/wiki/concepts/options-and-vouchers.md`; row 6 | `TODO.md`, "Prepare the other later-round mechanics"; P3 round 3, P4 rounds 3–4 |
| Strategies for a drifting product (market making around the drift, a long bias, accumulate then revert) | `references/wiki/concepts/drift-and-regime-change.md`; row 7 | P4 rounds 1–2, Pepper Root |
| Flattening before the close | `references/wiki/concepts/risk-and-protecting-a-lead.md` | `TODO.md`, "Let the template flatten before the close" |
