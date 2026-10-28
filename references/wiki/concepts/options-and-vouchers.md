---
title: Options and vouchers
type: concept
updated: 2026-10-13
---

# Options and vouchers

## Summary
Each edition had a call option on a product (coconut coupon, volcanic vouchers, `VEV_*`). The textbook plan, "fit the smile and trade mispricings", rarely paid. What did: using the vouchers as leveraged exposure to a view on the underlying, quoting a deep-OTM strike at 0/1, and one intrinsic-value arbitrage. Measured on P4 (2026-10-13): each voucher's implied vol is flat within a day, so a voucher is the underlying with a fixed delta, and the teams' voucher PnL is almost exactly delta times the underlying's move. What the vouchers add is room under the limits.

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

- **A fitted smile can stop fitting** (CMU Physics, Prosperity 3): their quadratic implied-volatility fit was a poor model on the submission day, so they held long or short vol all day and made almost nothing; using the mean of a short rolling window of mid implied volatility as fair IV took their backtest from about 80k to 200k per day (`online-snapshots/chrispyroberts_imc-prosperity-3.README.md:236`, their claim).
- **A free primer if options appear:** Optiver's explainers on options pricing, Greeks and volatility ([online articles](../sources/online-articles.md)); a shorter route than a textbook.

**Measured in our engine (2026-10-13, the four distinct days of P4 rounds 3–4, `uv run python -m experiments.day.p4_vouchers`; time to expiry 7 days at the start of round 3 day 0, as DTU's code reads it, `prosperity4-dtu-quant-lab/round_3/algorithmic/trader.py:263-267`):**
- **Flat volatility:** on the strikes with time value (5000–5500), the median implied vol is 0.245–0.278, its intraday IQR 0.003–0.009. It creeps up across days (VEV_5000: 0.259, 0.262, 0.270, 0.275). VEV_5400 sits 0.013–0.021 below its neighbours every day: the only smile.
- **No mispricing to trade:** each voucher's wall mid minus Black–Scholes at the day's median vol has an sd of 0.3–0.4 on 5000 and 0.4–1.1 on 5100–5200, under half their spreads (6, 4, 3), and about half the spread on 5300–5500.
- **The rest:** 4000 and 4500 trade at exactly intrinsic (delta 1); 6000 and 6500 at bid 0 / ask 1.
- **The teams' voucher PnL is leveraged underlying** (`python/experiments/study/p4_levels.py`, published files, against the wall mid): Baguette Fromage's carry on 5000–5500 is 697k, of which 690k is delta × Velvetfruit's move; on 4000–4500, all 416k. DU: 666k of which 657k, and all 440k. Crossing the spread cost Baguette Fromage 136k and 184k of it.
- **Cost per unit of delta** (half the spread over delta): 2.3–2.9 on 5100–5400, close to Velvetfruit's 2.5; 3.1–3.3 on 5000; 5.4–13.4 on 5500; 8.0 on 4500 and 10.5 on 4000.

## Where they disagree
Smile trading: DTU fitted and traded a parabola; Baguette Fromage, Alpha Search and DU concluded it was not worth it. See [contradictions](../contradictions.md), row 6: settled for P4 by the measurement above.

## What it means for our code
`python/bots/template.py` is per product with no pricing model, no delta hedge, no multi-product state. An options module would need the parent product's book in the same `step` (the Prosperity format provides all order depths each tick). Since 2026-10-13 the template has the hook and a mode for data like P4's: a product with `follow` and `strike` holds its underlying's target as a share of its own limit (`follow_target` and the Black–Scholes helpers, `python/bots/template.py:658-715`), and `Trader.run` trades the underlying first and hands its plan over. Delta comes from Black–Scholes in total variance σ²T, implied from the option's own price, so no expiry date is needed. On P4 the vouchers following Velvetfruit's level bet made 661k over four days out of sample (1,001k in-sample with Velvetfruit, against Baguette Fromage's 934k). The gate on half the spread per unit of delta never helped: every strike from 4000 to 5500 paid (`python/experiments/day/p4_vouchers_template.py`, `IDEAS.md`). Since 2026-10-18 there is a second mode, `smile` (`smile_fair`, `python/bots/template.py:718-741`): the fair is Black–Scholes at a smile `v(m) = a m² + b m + c` fitted on earlier days, plus an EMA of the option's offset from it, and take, clear and make trade around that; `hedge_ratio` with a `hedge` underlying adds a delta hedge.

## How to test it here
Needs `--data p4` (rounds 3–4). "Implied vol nearly constant per strike" is reproduced (above). P3 round 3's volcanic vouchers, checked 2026-10-13 (`python/experiments/day/p4_vouchers.py` with `--data p3 --underlying VOLCANIC_ROCK --prefix VOLCANIC_ROCK_VOUCHER_ --expiry r3d0=8,r3d1=7,r3d2=6`; 8 days at round 3 day 0, as Frankfurt's code reads it, `prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:644`) are different:
- **The vol moves with the spot within a day** (correlation ±0.6–0.9), though its IQR is small (0.003–0.023): a smile that the spot moves along.
- **Residual sds are 0.4–1.95 against one-tick spreads,** so there is a mispricing to trade, where Frankfurt and CMU Physics traded it.
- **Following the rock** (with its level from the day's running mean) made 198k over three days in-sample, but lost on one day.
**Smile trading, by held-out days (2026-10-18, `uv run python -m experiments.day.p3_smile`):** on the five distinct days, the smile fitted on the other four days is stable (`v ≈ 0.26 m² + 0.01 m + 0.15`, near Frankfurt's published 0.274, 0.010, 0.149). The residual's fast part (less its 20-tick EMA) is 0.7–1.8 on 10000 against a half-spread of 0.5, and gone by the next tick (lag-1 autocorrelation −0.04). Taking it on 9750 and 10000 at `take_edge` 0.5 made 528.8k, every day positive and the same in every fill mode, against 155.4k for following the rock. A flat vol does as well (567.0k with quotes, against 559.4k with the smile), and no option model loses: the edge is pricing the voucher off the rock, not the smile's shape *(inferred)*. The delta hedge halved it, and quotes resting on the vouchers lost 0.6–2.5M. CMU Physics' report that a fitted smile stopped fitting is consistent: the offset EMA absorbs what the fit misses. `literature_md` has no options material; the conditional SVI paper is in `TODO.md`.

## Sources
[Linear Utility](../sources/prosperity2-linear-utility.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DU Trading](../sources/prosperity4-du-trading.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [UChicago](../sources/uchicago-trading-2026.md). [CMU Physics](../sources/prosperity3-cmu-physics.md), [online articles](../sources/online-articles.md).
