---
title: Market making and inventory skew
type: concept
updated: 2026-10-10
---

# Market making and inventory skew

## Summary
The baseline in almost every top bot is **take → clear → make** around a fair value: take what is better than fair, trade at fair to free room under the limit, then quote one tick inside the book. The open question is whether to skew quotes against inventory, and how.

## What the sources say
- **The pattern.** Linear Utility's `take_best_orders` / `clear_position_order` / `make_orders` (`prosperity2-linear-utility/round1/round_1_v6.py:46`, `prosperity2-linear-utility/round1/round_1_v6.py:114`, `prosperity2-linear-utility/round1/round_1_v6.py:250`) is the ancestor of `bots/template.py`. Frankfurt's Resin trader takes at `wall_mid ± 1`, flattens at fair, and overbids inside the wall with full remaining room (`prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:275-331`).
- **Clearing at zero EV** frees room for better trades: about +3% PnL (`prosperity2-linear-utility/README.md:96`).
- **Skew variants shipped:**
  - Baguette Fromage Osmium: reservation price `10000 - position/12`, i.e. a linear shift (`prosperity4-baguette-fromage/Strategies/Phase1.py:240`); their round 5 market maker uses `wall_mid - 0.4 × position` with quote size 5 and a pull-back beyond ±8 (`prosperity4-baguette-fromage/Strategies/Phase2_Final.py:1374`).
  - DTU's plain market maker: `skew = position / limit × 4` ticks (`prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:656`).
  - Frankfurt: none; full room on both sides, flatten at fair.
  - Alpha Search: skew plus a half spread of 4 for non-bot quotes (`prosperity4-alpha-search/README.md:54`).
  - Ryan Challman: inventory skew `kq` enabled only where it held up across days (`prosperity4-ryan-challman/README.md:71`).
- **What failed:** an Avellaneda–Stoikov skew on pegged Osmium cost DTU 16,593 in backtest (`prosperity4-dtu-quant-lab/README.md:91`, their claim); a layered buy ladder on Hydrogel lost ~21,000 (`prosperity4-ryan-challman/README.md:268`); on news-driven products passive quotes were picked off (`uchicago-trading-2026/README.md:113-121`).
- **Plain beat clever on the live day.** DTU's hybrid replaced its elaborate strategies by the plain wall-mid market maker on UV_VISOR, TRANSLATOR and OXYGEN_SHAKE after live evidence of +11.3k, +10.8k and +0.8k (`prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:560-562`). Baguette Fromage's round 5 backbone was "broad market making" on every product (`prosperity4-baguette-fromage/Strategies/Phase2_Final.py:540`).

## Where they disagree
Whether a skew helps on a pegged product: DTU says an A–S skew lost 16,593 and reverted to a fixed anchor; Baguette Fromage shipped a linear skew (γ = 1/12) on the same product. See [contradictions](../contradictions.md), row 1. Neither number has been reproduced here.

## What it means for our code
`bots/template.py` has `skew` (default 0.0, a linear shift of both quotes by up to `skew` ticks at the full limit: `bots/template.py:200`), `clear_edge`, `take_edge` and `make_edge`. That is the linear variant, off by default.

## How to test it here
`TODO.md` (fair values and skew item): sweep `skew` on Prosperity 3 and 4 round 1 data with `arena.grid`, rank by the worst day and the neighbourhood, and under `--resting`. Theory: `literature_md/hft-in-a-limit-order-book/`, `literature_md/dealing-with-inventory-risk/`, `literature_md/optimal-market-making/` (check formulas against the PDF first).

## Sources
[Linear Utility](../sources/prosperity2-linear-utility.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [UChicago](../sources/uchicago-trading-2026.md), [hftbacktest](../sources/hftbacktest.md) (GLFT examples).
