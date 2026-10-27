---
title: Tao, Day, Ling & Drapeau, "On detecting spoofing strategies in high frequency trading" (2022)
type: source
repo: literature_md/detecting-spoofing-strategies
status: partly-read
updated: 2026-10-27
---

# Tao, Day, Ling & Drapeau, "On detecting spoofing strategies in high frequency trading" (Quantitative Finance 22(8), 2022; arXiv:2009.14818)

## What it is
A static model of a spoofer who moves a multi-level book imbalance to buy cheaper, the conditions under which spoofing pays, and a real-time detector calibrated on TMX level-2 data (`detecting-spoofing-strategies.md:5` (p. 1)). For harder-round item D3 (`references/SEARCH_LOG.md`, the spoofing table); fetched from arXiv.

## Main results
- **Where spoofing pays** (`detecting-spoofing-strategies.md:87` (p. 4)): when the spoofer's genuine order is large next to the book's depth, when the book starts balanced, and with the spoof posted away from the top. Whether thin books are more spoofable is inconclusive in the model.
- **The condition** (Proposition 3.3, eq. 3.4, `detecting-spoofing-strategies.md:266` (p. 9, checked); the same in eq. 5.1, `detecting-spoofing-strategies.md:497` (p. 19, checked)): no spoof pays at any depth `k` while `2ρµ+(1 − ı̄)ı̄w_k ≤ Q_kρ + ν_k` for every `k`. `ı = B/(B + A)` is the depth-weighted bid share, `µ+` the mean next move per unit of `2ı − 1` (`µ(ı) = µ+(2ı − 1)`, `detecting-spoofing-strategies.md:195` (p. 8, checked)), `w_k` level `k`'s weight in the imbalance, `ρ` the real order over the book's depth, `Q_k` the chance a market order goes past level `k` and `ν_k` how far past on average (`detecting-spoofing-strategies.md:239` (p. 9)). The Marker text of (3.4) drops the `ı̄`; the PDF has it. Spoofing is likelier with a large `µ+`, `w_k` or `ρ`, a small `Q_k`, and `ı̄` near 1/2 (`detecting-spoofing-strategies.md:271-276` (p. 9)).
- **The detector** (`detecting-spoofing-strategies.md:93` (p. 4)): a spoof only pays if a market order follows it, so compare the imbalance just before each market order with its usual distribution (and with the imbalance just after), by a Wasserstein distance; a spoofed book shows an imbalance before the trade that snaps back after it.

## Assumptions against the Arena
- A static, one-shot spoof on level-2 data; the Arena gives us snapshots, which is enough for imbalances by level *(inferred)*.
- **The tell for the day** *(inferred)*: in a product where large levels appear, look at the multi-level imbalance on ticks with market trades against all ticks; a spoofer shows as an imbalance that is unusually one-sided before trades and back to normal after.

## In our notation
The multi-level imbalance is computable from `Book` (volumes by level, weighted by depth); market orders are the data's `Tick.trades` classified against the book.

`arena.diagnose` computes the condition as a score per product (2026-10-27; the `spoof` column, its inputs in the CSV) *(our choices, inferred)*:
- `w_k` equal over the best 3 levels (the paper fits them by maximum likelihood, `detecting-spoofing-strategies.md:382-388` (p. 14)), so `ı` is the bid's share of the volume there;
- `µ+` the least-squares slope of the mid's next move, in ticks, on `2ı − 1`, over ticks without market trades (theirs is the mean of `dp+`, the moves from limit orders);
- each tick's market buys (sells) as one order of size `H`, and `y = F(H)` the levels it empties (`detecting-spoofing-strategies.md:382` (p. 14, checked));
- `ρ` the orders' mean size over the mean 3-level depth on the side they hit (their `ρ̄`), `ı̄` the mean imbalance on the tick after them (sells mirrored).

Results (`IDEAS.md`, "A spoof tell from the data"): on the products the template makes markets in, the next move goes against the depth imbalance (µ+ −0.5 to −0.8 ticks a unit of 2ı − 1 on P4 Osmium and Pepper Root, −3.3 to −7.9 on P2/P3 Resin, Amethysts, Kelp, Starfruit, Squid Ink; −18 and −44 on P4 Velvetfruit and Hydrogel), so no spoof pays (scores −0.01 to −0.79). 15 of 136 product-rounds score above 0, all on a book whose depth leans toward where the mid goes next: P2's gift basket (+0.14, µ+ 7.7), P3's Picnic Basket 1 (+0.10 to +0.11, µ+ 5.5–5.7), Macarons (+0.17, µ+ 10) and some volcanic vouchers (+0.01 to +0.07). The ABIDES days: µ+ +0.025, orders 19% of the 3-level depth, reaching level 0's end 16% of the time: −0.01, just short.

## Traps
- None found in what was read.

## Read depth
- **Read:** abstract, introduction (with its summary of conditions and the detection idea); section 3.1 (Definition 3.2, Proposition 3.3), the calibration of `dq` and `w` (section 4), and section 5's monitoring and eq. 5.1.
- **Skimmed:** the optimal strategy (Proposition 3.4) and the TMX tables.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md).
