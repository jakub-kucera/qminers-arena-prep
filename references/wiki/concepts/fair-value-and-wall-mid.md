---
title: Fair value and the "wall mid"
type: concept
updated: 2026-10-13
---

# Fair value and the "wall mid"

## Summary
Every strategy in the clones starts from an estimate of the simulator's true price. The simulator marks PnL to the **market maker's mid**, not the top-of-book mid, so teams estimate that. They call the estimate "wall mid", and the code defines it at least five ways.

## What the sources say
- **The mark is the market maker's mid.** Linear Utility found it by buying one lot at the first tick and holding it: their own PnL curve then equalled the website's (`prosperity2-linear-utility/README.md:109`). Frankfurt repeated the trick (`prosperity3-frankfurt-hedgehogs/README.md:882`) and Baguette Fromage reports the same (`prosperity4-baguette-fromage/README.md:268-272`). Positions are zeroed at fair value at the end (IMC webinar notes, in the online-only Ctrl-Alt-DefeatTheMarket repo; second-hand).
- **The top-of-book mid is noisy** because bots overbid and undercut (`prosperity4-baguette-fromage/README.md:261-266`); the "wall" is the large, stable liquidity of the market-making bot (`prosperity3-frankfurt-hedgehogs/README.md:883-885`).
- **Definitions in use:**

| Source | Definition | Where |
|---|---|---|
| Frankfurt Hedgehogs (P3) | mid of the **outermost** bid and ask (`min` of bid prices, `max` of ask prices) | `prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:153` |
| Baguette Fromage, round 1 | mid of the **highest-volume** bid and ask | `prosperity4-baguette-fromage/Strategies/Phase1.py:274` |
| Baguette Fromage, round 5 | trader base class: outermost levels; its market-making class: **first level from the top with volume ≥ 15**, else the best | `prosperity4-baguette-fromage/Strategies/Phase2_Final.py:383`, `prosperity4-baguette-fromage/Strategies/Phase2_Final.py:1333` |
| DTU Quant Lab, plain market maker | `(min bid + max ask) / 2` if each side has ≥ 2 levels, else the plain mid | `prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:613` |
| Linear Utility (P2 Starfruit) | mid of the best ask and bid among levels of **size ≥ 15**, plus a mean-reversion correction `-0.229 × last return` | `prosperity2-linear-utility/round1/round_1_v6.py:160` |
| Alpha Search | wall mid "with volumes as a filter", forward-filled when a side is missing | `prosperity4-alpha-search/README.md:48` |
| **Our `python/bots/template.py`** | **highest-volume level** (`wall_mid`, `_wall`); since 2026-10-13 also the outermost levels (`outer_mid`) and the first level from the top with at least `wall_size` (`sized_mid`) | `python/bots/template.py:442`, `python/bots/template.py:353-409` |

- **Per product:** Resin and Osmium are fixed at 10,000 (but see below); Kelp is a random walk, so the best forecast is the current wall mid (`prosperity3-frankfurt-hedgehogs/README.md:210`); Pepper Root is `start + 0.001 × timestamp`, with the start taken from the first wall mid rounded to the nearest 100 (`prosperity4-baguette-fromage/Strategies/Phase1.py:447-452`).
- **A fair value that lags can be the edge.** Ryan Challman's Black–Scholes-anchored voucher fair lost ~64,000 per strike because a cumulative mean that lagged the rising tape was producing the profit (`prosperity4-ryan-challman/README.md:266`); it reversed when the drift flipped (`prosperity4-ryan-challman/README.md:79-87`).
- **The signature plot measures how noisy a fair value is** ([Bouchaud et al.](../sources/trades-quotes-prices.md), eq. 2.9 and 2.13, `literature_md/trades-quotes-prices/trades-quotes-prices.md:685` (p. 44, checked)): the variance per tick of changes over `τ` ticks is flat for a random walk and falls with `τ` when the price carries noise that reverts. Measured on Prosperity 3 round 1 (2026-10-12), Kelp's mid has 0.611 per tick at lag 1 and 0.022 at lag 200, 28 times more at one tick; its wall mid has 0.064 and 0.020, 3 times. Starfruit's mid 2.87 against 0.18, wall mid 0.33 against 0.17. So the wall mid removes most of the top-of-book noise, but not all of it.
  - Liquid markets have flat signature plots because fast strategies "iron out all irregularities" (`literature_md/trades-quotes-prices/trades-quotes-prices.md:849` (p. 54)). Prosperity's strongly mean-reverting mid suggests nothing does that there, which is the edge the template's take and clear steps exploit *(inferred)*.
- **Measured: the definitions compared** (2026-10-13). The template on its own, with only the product's `fair` changed, run with `arena.backtest`. "DTU" is the min-bid/max-ask rule that needs two levels a side; `sized_mid` uses 15 lots. PnL per day in thousands, then the worst day; default engine mode:

  | Product (data) | `wall_mid` (largest) | `outer_mid` (Frankfurt) | DTU | `sized_mid` (first ≥ 15) |
  |---|---|---|---|---|
  | Starfruit (P2 round 1) | 18.3 · 18.1 · 17.3; worst 17,282 | 18.6 · 18.3 · 17.5; worst 17,501 | 10.1 · 9.5 · 9.8; worst 9,517 | 18.2 · 18.0 · 17.2; worst 17,160 |
  | Kelp (P3 rounds 1–2; the rounds share two days) | 9.5 · 9.2 · 8.6 · 9.2 · 8.6 · 9.2; worst 8,616 | the same to within 1; worst 8,616 | 7.4 · 7.6 · 6.5 · 7.6 · 6.5 · 7.5; worst 6,472 | 9.5 · 9.2 · 8.7 · 9.2 · 8.6 · 9.2; worst 8,644 |
  | Osmium (P4 rounds 1–2) | 17.4 · 18.6 · 17.9 · 19.7 · 20.5 · 19.7; worst 17,354 | 17.5 · 18.6 · 17.9 · 19.7 · 20.5 · 19.8; worst 17,480 | 16.8 · 18.1 · 16.8 · 18.6 · 19.1 · 18.6; worst 16,750 | 17.2 · 18.4 · 17.5 · 19.3 · 19.7 · 19.2; worst 17,206 |
  | Pepper Root (P4 rounds 1–2) | 76.5 · 78.2 · 77.9 · 76.3 · 75.9 · 76.9; worst 75,885 | 76.9 · 78.0 · 77.9 · 76.3 · 75.9 · 76.9; worst 75,885 | 75.9 · 77.9 · 77.2 · 74.5 · 76.2 · 74.4; worst 74,355 | 75.6 · 78.7 · 75.3 · 77.0 · 77.6 · 75.0; worst 75,032 |

  - **On its own, the outermost level wins by a hair.** It ties or beats the largest level on every product's worst day, also under `--resting` and `--match-trades worse`, by 0–1.3%. `sized_mid` is within 2.3% of the largest level. Under `--resting` it is 1.0% ahead on Pepper Root (474,322 against 469,636) and 2.3% behind on Osmium.
  - **DTU's rule loses everywhere except Pepper Root under `--resting`:** −45% on Starfruit and −21% on Kelp. With one level on a side it falls back to the plain mid, and its noise is close to the mid's (below).
  - **Rivals' resting orders reverse the order.** In one market with the teams' P4 bots under `--resting` (the setting of [shared market](shared-market-and-adversaries.md)), Osmium against all three made, in rounds 1 / 2:
    - the largest level: −377k / −445k;
    - the outermost: −654k / −716k;
    - DTU's: −611k / −653k;
    - `sized_mid`: **+39k / +21k**.

    Against Baguette Fromage alone, `sized_mid` made +17.5k where the largest level lost 374k. A large order far from the touch is both the largest and the outermost level, but it is never the first sizable level from the top. So `sized_mid`'s error is bounded by the market maker's distance from the touch *(inferred from the definitions)*. Worked through on the book the template saw at tick 2,400: 9,999.5 against a recorded 10,001.5, where the largest level gave 9,957 (`python/tests/test_template.py`, `test_outer_and_sized_mids`, has the same case). When orders live one tick, the rivals' orders are never visible: on Osmium the largest, outermost and sized levels are within 2.5k of each other, and DTU's rule is up to 6.4k behind.
  - **Noise** (signature ratio, variance per tick at lag 1 over lag 200; the plain mid in brackets): Starfruit 1.9 / 1.8 / 14.2 / 2.1 (15.6); Kelp 3.6 / 3.5 / 29.1 / 3.7 (29.6); Osmium 14.3 / 14.2 / 23.1 / 18.7 (35.3), in the table's column order. The outermost and largest levels filter the most, `sized_mid` a little less, and DTU's rule hardly at all on P2/P3.
  - **`wall_size`:** from 10 to 20 the bot's PnL stays within 3% of the best on all four products (round 1 of each), and it drops at 5 and at 25–30. The market maker's level has a median of 19–26 lots, and the other levels reach at most 11–18 (bid side, round 1 day 0). On new data, pick a size between the two.
- **What the literature estimates instead.** The weighted mid and Stoikov's micro-price estimate the *future* mid from the volumes at the best levels ([book imbalance](book-imbalance-and-micro-price.md)). The wall mid estimates the market maker's quote, which in Prosperity *is* the mark. The two answer different questions: the wall mid what the position is worth now, the micro-price where the top of the book goes next. The literature also predicts that the micro-price adds little at Prosperity's 2–21-tick spreads ([micro-price](../sources/micro-price.md)).

## Where they disagree
The definitions above (see [contradictions](../contradictions.md), row 2). They coincide on Prosperity books where the big bot sits at the outermost level and diverge when a book has two or three levels.

## What it means for our code
`fair` in `python/bots/template.py` offers `fixed`, `mid`, `wall_mid`, `outer_mid` and `sized_mid` (`python/bots/template.py:353-409`), with exponential smoothing. The Prosperity products keep `wall_mid`, the best on their own data. **In a shared market with resting orders, use `sized_mid`,** with `wall_size` set from the data (above). The Arena may not expose the PnL mark, so the one-lot trick needs a check (`ON_THE_DAY.md`).

## How to test it here
Done 2026-10-13 (above; `IDEAS.md` has the commands). On the day: grid `fair` over `wall_mid`, `outer_mid` and `sized_mid` per product, and, if the market is shared, repeat it with `--vs` rivals under the engine mode that matches the playground. Originally: add any definition that wins on its worst day as a `fair` option.

## Sources
[Stoikov, micro-price](../sources/micro-price.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Linear Utility](../sources/prosperity2-linear-utility.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Bouchaud et al.](../sources/trades-quotes-prices.md). Related: [market-making-and-inventory-skew](market-making-and-inventory-skew.md), [drift-and-regime-change](drift-and-regime-change.md).
