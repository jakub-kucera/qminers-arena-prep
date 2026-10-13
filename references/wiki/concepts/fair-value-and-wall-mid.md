---
title: Fair value and the "wall mid"
type: concept
updated: 2026-10-12
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
| **Our `bots/template.py`** | **highest-volume level** (`_wall`) | `bots/template.py:157` |

- **Per product:** Resin and Osmium are fixed at 10,000 (but see below); Kelp is a random walk, so the best forecast is the current wall mid (`prosperity3-frankfurt-hedgehogs/README.md:210`); Pepper Root is `start + 0.001 × timestamp`, with the start taken from the first wall mid rounded to the nearest 100 (`prosperity4-baguette-fromage/Strategies/Phase1.py:447-452`).
- **A fair value that lags can be the edge.** Ryan Challman's Black–Scholes-anchored voucher fair lost ~64,000 per strike because a cumulative mean that lagged the rising tape was producing the profit (`prosperity4-ryan-challman/README.md:266`); it reversed when the drift flipped (`prosperity4-ryan-challman/README.md:79-87`).
- **The signature plot measures how noisy a fair value is** ([Bouchaud et al.](../sources/trades-quotes-prices.md), eq. 2.9 and 2.13, `literature_md/trades-quotes-prices/trades-quotes-prices.md:685` (p. 44, checked)): the variance per tick of changes over `τ` ticks is flat for a random walk and falls with `τ` when the price carries noise that reverts. Measured on Prosperity 3 round 1 (2026-10-12), Kelp's mid has 0.611 per tick at lag 1 and 0.022 at lag 200, 28 times more at one tick; its wall mid has 0.064 and 0.020, 3 times. Starfruit's mid 2.87 against 0.18, wall mid 0.33 against 0.17. So the wall mid removes most of the top-of-book noise, but not all of it.
  - Liquid markets have flat signature plots because fast strategies "iron out all irregularities" (`literature_md/trades-quotes-prices/trades-quotes-prices.md:849` (p. 54)). Prosperity's strongly mean-reverting mid suggests nothing does that there, which is the edge the template's take and clear steps exploit *(inferred)*.
- **What the literature estimates instead.** The weighted mid and Stoikov's micro-price estimate the *future* mid from the volumes at the best levels ([book imbalance](book-imbalance-and-micro-price.md)). The wall mid estimates the market maker's quote, which in Prosperity *is* the mark. The two answer different questions: the wall mid what the position is worth now, the micro-price where the top of the book goes next. The literature also predicts that the micro-price adds little at Prosperity's 2–21-tick spreads ([micro-price](../sources/micro-price.md)).

## Where they disagree
The definitions above (see [contradictions](../contradictions.md), row 2). They coincide on Prosperity books where the big bot sits at the outermost level and diverge when a book has two or three levels.

## What it means for our code
`fair` in `bots/template.py` offers `fixed`, `mid` and `wall_mid` (`bots/template.py:129-148`), with exponential smoothing. The `wall_mid` option is the highest-volume definition only. The Arena may not expose the PnL mark, so the one-lot trick needs a check (`ON_THE_DAY.md`).

## How to test it here
`TODO.md`: "Compare the wall-mid definitions on real data": run one simple market maker with each definition on Prosperity 3 and 4 round 1–2 data and compare PnL per day. Add any definition that wins on its worst day as a `fair` option.

## Sources
[Stoikov, micro-price](../sources/micro-price.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Linear Utility](../sources/prosperity2-linear-utility.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Bouchaud et al.](../sources/trades-quotes-prices.md). Related: [market-making-and-inventory-skew](market-making-and-inventory-skew.md), [drift-and-regime-change](drift-and-regime-change.md).
