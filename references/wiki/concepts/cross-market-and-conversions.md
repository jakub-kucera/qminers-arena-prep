---
title: Cross-market trading and conversions
type: concept
updated: 2026-10-10
---

# Cross-market trading and conversions

## Summary
Prosperity 2 (Orchids) and Prosperity 3 (Macarons) let you buy from or sell to another island at a quoted price plus tariffs and transport; AlgoTrade had the same ticker on several exchanges with latency between them. The arbitrage was real, but the backtesters could not simulate it. Prosperity 4 had no such product.

## What the sources say
- **Orchids (P2):** a large local taker lifted sell orders just above the best bid; combined with the foreign market's implied ask it was an arbitrage worth ~60k in a fifth of a day. Once leaked, everyone found it (`prosperity2-linear-utility/README.md:118-137`).
- **Macarons (P3):** Frankfurt computed the local sell/buy prices against the island's bid/ask plus tariffs and transport, traded when a running mean of the edge was positive, and took 0.58 of the edge as the price cut-off (`prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:775-878`). Alpha Animals used a sunlight-index regime and market making around the arbitrage (`prosperity3-alpha-animals/trader.py:1148-1460`) and failed to get it working in round 4 (`prosperity3-alpha-animals/README.md:153`).
- **The tooling gap:** the backtesters do not support conversions (`prosperity3-backtester-jmerle/README.md:83`), so teams tested on the website.
- **Cross-venue (AlgoTrade):** the same ticker bid on one nearby venue far above the ask on another was the scale signal, with latency deciding who got filled (`algotrade2026-pitfa19/docs/VOIDMAKER_EDGE_PROOF.md:48-60`, replays of their own recordings).
- **Creation/redemption (UChicago):** the ETF swap with a 5-tick fee is a conversion in the same sense (`uchicago-trading-2026/README.md:103`).

## Where they disagree
Nothing to compare.

## What it means for our code
`CLAUDE.md` "Known gaps": no conversions. The Arena's product list is unknown; build this only if the Technical Rules introduce another venue or island.

## How to test it here
Not testable until the engine supports conversions. Cost of building: new order type, observation fields and fee handling in `arena/engine.py` and the Prosperity format.

## Sources
[Linear Utility](../sources/prosperity2-linear-utility.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md), [UChicago](../sources/uchicago-trading-2026.md), [jmerle P3 backtester](../sources/prosperity3-backtester-jmerle.md).
