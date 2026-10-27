---
title: Wang, Hoang & Wellman, "Learning-based trading strategies in the face of market manipulation" (ICAIF 2020)
type: source
repo: literature_md/trading-under-manipulation
status: read
updated: 2026-10-14
---

# Wang, Hoang & Wellman, "Learning-based trading strategies in the face of market manipulation" (ICAIF 2020)

## What it is
An 8-page sequel to [spoofing-abm](spoofing-abm.md) by the same group, in the same market:
- a mean-reverting fundamental;
- traders who see it with noise and update a Kalman filter (here the variance step reads correctly, `trading-under-manipulation.md:94` (p. 3, checked));
- 64 background traders and one exploiter, who buys cheap, spoofs and sells (`trading-under-manipulation.md:179` (p. 5)).

The question is the defender's side of D3 in [harder-rounds](../concepts/harder-rounds.md): how a trader that reads the book can stay useful without being spoofed. The user saved it from the ACM Digital Library on 2026-10-14.

## Main results
- **Two defences** for a book-reading (HBL) trader:
  - **Block one price level** when learning (`trading-under-manipulation.md:126` (p. 4)). Parameter `K` is the level ignored, counted from the inside, symmetric on both sides; `K = 1` drops the best bid and ask.
  - **Shift the learned price** by a uniform random offset in `[R_min, R_max]` (`trading-under-manipulation.md:128` (p. 4)).
- **The spoofer:** after buying below `r̄`, it holds 200 lots one tick behind a chosen level `K` from `t = 1,000`, and sells above `r̄` from `t = 2,000` (`trading-under-manipulation.md:140` (p. 4), `trading-under-manipulation.md:179` (p. 5)).
- **What each level is worth** (Table 2, `trading-under-manipulation.md:201` (p. 6); values from the PDF's text layer, since the conversion is scrambled, see Traps):
  - **Without spoofing, ignoring the best quotes costs the learner; ignoring a deeper level costs nothing.** Standard HBL earns 651 / 655 / 645 in the three environments. Blocking level 1 earns 643 / 643 / 634 (significant). Blocking level 2 or 3 earns 646–652.
  - **The spoof pays only right behind the best bid.** With the spoof one tick behind level 1, the exploiter earns 494 / 330 / 221. Behind level 2 it earns 475 / 313 / 195, behind level 3 470 / 305 / 202, and without spoofing 468 / 305 / 199. So the spoof adds 22–26 to a trade that earns about 200–470 on its own.
- **Blocking the right level neutralises the spoof** and restores the learners' surplus. With the blocking option, learning strategies stay as competitive as before in markets without spoofing (`trading-under-manipulation.md:237` (p. 7)).
- **A small negative offset helps in general.** It makes the learner's price slightly more aggressive, by 10–40 ticks against a 10⁵ fundamental. It raises learners' payoffs, adds trades, and makes a spoof's price effect wear off faster (`trading-under-manipulation.md:241` (p. 7), `trading-under-manipulation.md:253` (p. 7)). It doesn't by itself protect against spoofing; combining it with blocking does (`trading-under-manipulation.md:269` (p. 8)).

## Assumptions against the Arena
- **The victims learn fill probabilities by price from recent orders.** Our template doesn't: it reads the book's levels directly through `wall_mid` or `sized_mid`. The defence carries over as "ignore the level a spoofer would use" *(inferred)*.
- **The spoofer is shielded behind a best bid** that single-unit traders can't get through. In a Prosperity-like book, a large take could reach a fake wall *(inferred)*.

## In our notation
- **Blocking level `K`** maps onto how `fair` picks its level:
  - `wall_mid` takes the largest level anywhere in the book, the place a 200-lot spoof one tick behind the best would win;
  - `outer_mid` takes the outermost;
  - `sized_mid` takes the first level from the inside with at least `wall_size` (`python/bots/template.py:347`, `fair_value`).

  The paper's finding, that the inside quotes carry the information and a deeper level can be dropped at little cost, argues for a `fair` that doesn't jump to a new largest level the moment one appears. That is the wall-persistence check in [harder-rounds](../concepts/harder-rounds.md), D3 *(inferred)*.
- **The negative offset** is a slightly tighter `make_edge`. The paper's gain comes from re-entry, more trades sooner, which the template already gets by re-quoting every tick.

## Traps
- **OCR: Table 2 is scrambled** (line 201).
  - The environment names moved into the first column and LSHN became "SLHN".
  - The values shifted one column left, and the no-spoof EXP column was lost.
  - "594" stands where the PDF has 494, and "192" where it has 199.

  Use the values above, read from the PDF's text layer.
- **The gains are averages over 40,000 or more simulated runs.** Differences of 1–2% (651 against 643) are significant there, but would be invisible in a few days of Arena data.

## Read depth
- **Read:** the whole paper. Table 2 was read from the PDF's text layer.
- **Not read:** the online appendix (equilibrium profiles).

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [spoofing-abm](spoofing-abm.md).
