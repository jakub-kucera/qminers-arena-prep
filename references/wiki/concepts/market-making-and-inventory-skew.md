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

- **Quoting design under a tight limit** (heyman7913): two passive layers (inner ±5, outer ±7 from fair) so the position limit does not leave the bot idle, and **25 units reserved for aggressive takes** regardless of passive fills; their biggest early mistake was filling the passive layer first and having no room when a clear mispricing appeared (`online-snapshots/heyman7913_imc-prosperity-4.README.md:146-162`). They blended a volume-weighted mid with a slow EMA and an imbalance term `0.30 × micro + 0.70 × EMA + 2.0 × imbalance − inventory penalty` and tested it with a Spearman correlation (`online-snapshots/heyman7913_imc-prosperity-4.README.md:195-233`).
- **Avellaneda–Stoikov as run in practice** (Hummingbot, read through summaries, no local copy): reservation `s − q·γ·σ²·(T − t)` and spread `γσ²(T − t) + (2/γ)·ln(1 + γ/κ)`, with γ and κ **derived from the user's min and max spread**, not estimated from the book ([online articles](../sources/online-articles.md)). Compare with the constant-coefficient linear skews above.
- **Order-book imbalance as a quoting signal** (Cartea, Donnelly & Jaimungal 2018, now in `literature_md/order-book-signals/`): define `ρ = (Vᵇ − Vᵃ)/(Vᵇ + Vᵃ)` from the volumes at the best bid and ask (*checked against the PDF*: `literature_md/order-book-signals/order-book-signals.md:75-79` (p. 5, checked)). On eleven Nasdaq equities ρ predicts the sign of the next market order and the price change right after it, and putting ρ into a limit-order market-making control problem raised out-of-sample profit by cutting adverse selection (`literature_md/order-book-signals/order-book-signals.md:43` (p. 2)). Their motivating findings: 91.6–99.9% of market orders are filled by the volume at the best price alone, so deeper limit orders rarely fill, and a strategy that always posts at the touch **has negative expected earnings** from adverse selection (`literature_md/order-book-signals/order-book-signals.md:61-63` (p. 4), `literature_md/order-book-signals/order-book-signals.md:87` (p. 6)). Caution from the AlgoTrade analysis: the sign of an imbalance's predictive power **flips per instrument** (`algotrade2026-pitfa19/analysis/mm_analysis.md:172-197`).

## Where they disagree
Whether a skew helps on a pegged product: DTU says an A–S skew lost 16,593 and reverted to a fixed anchor; Baguette Fromage shipped a linear skew (γ = 1/12) on the same product. See [contradictions](../contradictions.md), row 1. Neither number has been reproduced here.

## What it means for our code
`bots/template.py` has `skew` (default 0.0, a linear shift of both quotes by up to `skew` ticks at the full limit: `bots/template.py:200`), `clear_edge`, `take_edge` and `make_edge`. That is the linear variant, off by default.

## How to test it here
`TODO.md` (fair values and skew item): sweep `skew` on Prosperity 3 and 4 round 1 data with `arena.grid`, rank by the worst day and the neighbourhood, and under `--resting`. `TODO.md` also has an item to test the imbalance `ρ` and the volume-weighted mid as fair-value inputs per product (check formulas against the PDF first). Theory: `literature_md/hft-in-a-limit-order-book/`, `literature_md/dealing-with-inventory-risk/`, `literature_md/optimal-market-making/` (check formulas against the PDF first).

## Sources
[Linear Utility](../sources/prosperity2-linear-utility.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [UChicago](../sources/uchicago-trading-2026.md), [hftbacktest](../sources/hftbacktest.md) (GLFT examples). [Cartea et al. 2018](../../../literature_md/order-book-signals/order-book-signals.md), [heyman7913](../sources/prosperity4-heyman7913.md), [online articles](../sources/online-articles.md).
