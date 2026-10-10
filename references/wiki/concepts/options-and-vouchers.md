---
title: Options and vouchers
type: concept
updated: 2026-10-10
---

# Options and vouchers

## Summary
Each edition had a call option on a product (coconut coupon, volcanic vouchers, `VEV_*`). The textbook plan, "fit the smile and trade mispricings", rarely paid. What did: using the vouchers as leveraged exposure to a view on the underlying, quoting a deep-OTM strike at 0/1, and one intrinsic-value arbitrage.

## What the sources say
- **Prosperity 2 coconut coupon:** implied volatility oscillated around 16%; mean-reversion on it plus a partial delta hedge; the unhedged variance hurt when they were already 2nd (`prosperity2-linear-utility/README.md:162-170`).
- **Prosperity 3 volcanic vouchers:** Frankfurt used a quadratic smile in `ln(K/S)/√TTE`, an EMA of price minus theoretical value, and "IV scalping" gated on a deviation level (`prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:559-771`; code never trades as published, parameters are in `prosperity3-frankfurt-hedgehogs/README.md:428-620`). Alpha Animals priced them with Black–Scholes and a rolling volatility (`prosperity3-alpha-animals/trader.py:712-771`).
- **Prosperity 4 `VEV_*` vouchers (ten strikes 4000–6500):**
  - Baguette Fromage: implied volatility nearly constant per strike through the day, so no smile trading; vouchers used to express the underlying's mean-reversion view, with thresholds from a Monte Carlo of the Ornstein–Uhlenbeck underlying including **theta**, objective `E[PnL] − 0.25 Std` (`prosperity4-baguette-fromage/README.md:769-840`); they said the aggressive objective likely explains the worse round 4 (`prosperity4-baguette-fromage/README.md:836`). They market-made only `VEV_4000` (`prosperity4-baguette-fromage/README.md:794`).
  - DU: fitted a parabola but the 5X00 implied vols mean-reverted and spreads were "obscene", so they faded the underlying and every active voucher together (`prosperity4-du-trading/README.md:118-131`); `VEV_4000` tracked `fruit − 4000` with σ ≈ 0.84, take beyond 2 ticks (`prosperity4-du-trading/README.md:153-155`).
  - Alpha Search: vouchers "followed the underlying's direction perfectly"; only 45.6% of observations survived a quality screen for the parabola (`prosperity4-alpha-search/README.md:102-109`).
  - Ryan Challman: a Black–Scholes-anchored fair lost ~64,000 per strike (`prosperity4-ryan-challman/README.md:266`).
  - DTU: a flat σ = 0.20 in round 3 missed the edge; a parabolic correction on top in round 4 recovered some (`prosperity4-dtu-quant-lab/README.md:141`, `prosperity4-dtu-quant-lab/README.md:163`).
- **Deep out-of-the-money strikes (6000, 6500):** bid 0 / ask 1 all day; quote bid 0 in full size, about 150 per round (`prosperity4-du-trading/README.md:112-116`); Alpha Search posted bid 0 / ask 1 after seeing Mark 22 sell at 0 (`prosperity4-alpha-search/README.md:117`). Inventory at the end is settled at fair value (about 1), so it is riskless.
- **UChicago:** put–call parity and box-spread bots found no edge because spreads exceeded any mispricing, and thin option books were the most prone to sniping (`uchicago-trading-2026/README.md:181-195`).
- **Stdlib helpers you can reuse as a pattern:** `bs_call_price`, delta, vega, `implied_vol` and a 3×3 parabola fit in plain `math` (`prosperity4-dtu-quant-lab/round_3/algorithmic/trader.py:416-466`, `prosperity4-dtu-quant-lab/round_3/algorithmic/trader.py:1464`).

## Where they disagree
Smile trading: DTU fitted and traded a parabola; Baguette Fromage, Alpha Search and DU concluded it was not worth it. See [contradictions](../contradictions.md), row 5.

## What it means for our code
`bots/template.py` is per product with no pricing model, no delta hedge, no multi-product state. An options module would need the parent product's book in the same `step` (the Prosperity format provides all order depths each tick).

## How to test it here
Needs `--data p4` (rounds 3–4). Reproduce "implied vol nearly constant per strike" first (a plot), then test the underlying-view approach against a smile approach by the worst day. `literature_md` has no options material; the conditional SVI paper is in `TODO.md`.

## Sources
[Linear Utility](../sources/prosperity2-linear-utility.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DU Trading](../sources/prosperity4-du-trading.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [UChicago](../sources/uchicago-trading-2026.md).
