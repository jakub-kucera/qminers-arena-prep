---
title: Architecture for many products
type: concept
updated: 2026-10-12
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

- **State must survive a restart** (CMU Physics, Prosperity 3): visualizer logging pushed their submission over 100 MB, the Lambda instance restarted and **wiped all local variables**, which broke the rolling windows behind their basket and Volcanic Rock trades; they fell from 7th to 241st in that round (`online-snapshots/chrispyroberts_imc-prosperity-3.README.md:234`). Alpha Animals' split between `self` and `traderData` has the same exposure.
- **Tooling debt** (Leo-Hawking): one shared backtester grew a branch per market over five rounds; they would keep only the matching mechanics generic and write a light ad hoc backtester per round (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:595-600`).
- **Theory: one risk budget across correlated products** (Guéant 2017, [source](../sources/optimal-market-making.md)): a market maker in several correlated assets should skew asset i on `Σ_j Γ^{ij} q^j`, the inventories of all of them, not on `qⁱ` alone. A short in one and an equal long in a highly correlated one may need no skew at all (`literature_md/optimal-market-making/optimal-market-making.md:794` (p. 23)). See [optimal quoting models](optimal-quoting-models.md).

## Where they disagree
Aggregating by averaging targets (Baguette Fromage) versus exclusive ownership (Alpha Search): averaging lets a weak signal dilute a strong one; ownership leaves capacity unused. Not tested.

## What it means for our code
`bots/template.py` already has a per-product `Plan` that keeps all orders inside the room under the limit, a `Trader.run` with a try/except per product swallowed unless `STRICT`, and `arena.validate`. It lacks intents, shared state across products and a global tick-volume cap.

## How to test it here
Port a toy two-strategy product (a market maker plus a target-position strategy) onto the template and check with `arena.validate` and the parity-pinned engine that no limit breaches appear. A tick-volume cap is a one-line experiment.

## Sources
[Guéant 2017](../sources/optimal-market-making.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [UChicago](../sources/uchicago-trading-2026.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md). [CMU Physics](../sources/prosperity3-cmu-physics.md), [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md).
