---
title: Architecture for many products
type: concept
updated: 2026-10-10
---

# Architecture for many products

## Summary
Round 5 had 50 products with a limit of 10 each. The teams that kept control did three things: one object per product, strategies that propose targets instead of sending orders, and safety nets above the strategies.

## What the sources say
- **Intents** (Baguette Fromage): each strategy calls `add_intent(name, target_pos, weight, max_buy_price, min_sell_price)`; the product trader averages the weighted targets, clips to the limit and takes liquidity to reach the target, then posts the remainder one tick inside (`prosperity4-baguette-fromage/Strategies/Phase2_Final.py:275-548`). A product with no intent gets "broad market making": best bid +1 and best ask −1 with all the room (`prosperity4-baguette-fromage/Strategies/Phase2_Final.py:540`). That baseline was the backbone of their round.
- **Cluster strategies** (DTU): an abstract `ClusterStrategy` with `load_state`, `dump_state`, `update` (`prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:510`); ten subclasses with isolated state; a master `Trader` that merges, clips and serialises with a schema version (`prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:2833`). The point, in their words: iterate one cluster "without risking" another (`prosperity4-dtu-quant-lab/docs/journey.md:30`).
- **Hard product ownership** (Alpha Search): each product belongs to at most one structural strategy; market making runs only on unclaimed products, so two strategies never pay each other the spread (`prosperity4-alpha-search/README.md:174`).
- **Budgeting one limit between strategies** (UChicago): 150 of the 200 limit for directional, 40 for arbitrage, 10 buffer; the arbitrage bot's position is `exchange_position − directional_position` (`uchicago-trading-2026/README.md:205-213`).
- **Safety nets above the strategies** (DTU): drop all of a product's orders if their sum could breach the limit; zero a cluster that tries to trade more than 200 units in a tick; a `try/except` per cluster; a version check that resets state (`prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:2908`, `prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:2829`, `prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:2885-2895`). A drawdown halt was declared and never wired (`prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:2827`). Alpha Animals instead wrapped all of `run` in one `try` (`prosperity3-alpha-animals/trader.py:1548`), so one bad product can abort the lot.
- **Silent limit failures cost rank**: Alpha Animals' basket strategy tried to exceed the limit, the engine cancelled the orders and it never ran (`prosperity3-alpha-animals/README.md:119`).

## Where they disagree
Aggregating by averaging targets (Baguette Fromage) versus exclusive ownership (Alpha Search): averaging lets a weak signal dilute a strong one; ownership leaves capacity unused. Not tested.

## What it means for our code
`bots/template.py` already has a per-product `Plan` that keeps all orders inside the room under the limit, a `Trader.run` with a try/except per product swallowed unless `STRICT`, and `arena.validate`. It lacks intents, shared state across products and a global tick-volume cap.

## How to test it here
Port a toy two-strategy product (a market maker plus a target-position strategy) onto the template and check with `arena.validate` and the parity-pinned engine that no limit breaches appear. A tick-volume cap is a one-line experiment.

## Sources
[Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [UChicago](../sources/uchicago-trading-2026.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md).
