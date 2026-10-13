---
title: Baskets, ETFs and fixed-sum identities
type: concept
updated: 2026-10-13
---

# Baskets, ETFs and fixed-sum identities

## Summary
Every edition had a product that is a known combination of others (gift baskets, picnic baskets, an ETF) or a family whose prices sum to a constant (Pebbles = 50,000). Trading the deviation is the cleanest structure in the data, but it is capped by position limits, and searching for *unknown* relationships is mostly overfitting.

## What the sources say
- **Known weights.** Prosperity 3 baskets were 6/3/1 and 4/2/0 of Croissants/Jams/Djembes with a stable premium: Frankfurt used a running mean premium, thresholds 80 and 50, a ±90 shift when informed, and hedged the constituents at 0.5 (`prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:409-556`; note the published file never trades: [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md)). Prosperity 2's gift basket spread sat near 370 and was traded on a z-score with a hard-coded mean and a short rolling σ (`prosperity2-linear-utility/README.md:139-160`). UChicago's ETF had a hard bound from a 5-tick swap fee, and the ETF was always the mispriced leg (`uchicago-trading-2026/README.md:103`, `uchicago-trading-2026/README.md:127-134`).
- **Fixed sums (Prosperity 4 round 5).** `PEBBLES_XS + S + M + L + XL ≈ 50,000`, σ ≈ 2.8, range 49,982–50,016 (`prosperity4-dtu-quant-lab/docs/journey.md:32`): found independently by Baguette Fromage (`prosperity4-baguette-fromage/README.md:1068-1075`), DTU (+17.5k live, capped by the limit of 10: `prosperity4-dtu-quant-lab/README.md:198`), DU (sell all five above ~49,990, buy all below ~50,010: `prosperity4-du-trading/README.md:201`), Ryan Challman (`prosperity4-ryan-challman/README.md:111-113`) and Alpha Search (`prosperity4-alpha-search/README.md:157`). Snack packs: chocolate and vanilla mirror around 10,000 (`prosperity4-du-trading/README.md:210`). UV visors: `3 MAGENTA + 2 AMBER + RED ≈ 60k` (`prosperity4-alpha-search/README.md:146`).
- **Searching for unknown relationships is a trap.** In round 5, scanners found "unlimited alpha" in sample; fit on two days, test on the third, and it collapsed: residuals non-stationary, hedge ratios flipping sign (`prosperity4-baguette-fromage/README.md:885-901`). Alpha Search quantified the multiple-testing problem (3-fold "any pass" ≈ 14% false positives), restricted weights to small integers in [−3, 3] within a product family, and ranked baskets by `(σ / cost) × (1 / half-life)` instead of by p-value (`prosperity4-alpha-search/README.md:124-141`). The family-level live attribution of Baguette Fromage's residual baskets was mixed: Microchips −26.8k, Sleep Pods −14.0k (`prosperity4-baguette-fromage/README.md:934-963`).
- **Execution.** Take all legs at once (DU), keep a residual accounting so two strategies share one limit (UChicago: 150 directional, 40 arb, 10 buffer: `uchicago-trading-2026/README.md:205-213`), and give each product to one structural strategy (`prosperity4-alpha-search/README.md:174`).
- **Lead-lag** within a family: Microchip Circle leads the others at 50/100/150/200 ticks (`prosperity4-alpha-search/README.md:160`); an earlier cross-category finding was a pandas alignment bug (`prosperity4-alpha-search/README.md:162`).

**What the literature says** ([Cartea et al., book](../sources/algorithmic-and-hft.md) ch. 11, [Harris](../sources/harris-trading-and-exchanges.md) ch. 17):
- **Pure against speculative arbitrage.** In a pure arbitrage the basis *must* revert. A known basket with a stable premium, or the Pebbles sum, is that kind. In a speculative one (pairs, statistical arbitrage) the basis can be non-stationary and never revert (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:8294` (p. 369)). Round 5's "unlimited alpha" that collapsed out of sample is the speculative kind.
- **"The most common mistake that arbitrageurs make is to incorrectly identify a change in the basis as an arbitrage opportunity"** (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:8574` (p. 381)). Slow convergence is a loss in itself, through carrying costs and the position limit it occupies (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:8667` (p. 385)).
- **Ad hoc bands:** with "enter at ±k standard deviations, exit near the mean", the PnL bunches at multiples of the band. **Sharpe first rises, then falls, as k grows.** A position may still be open at the end (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:6339-6373` (p. 291–294)).
- **Optimal bands for an Ornstein–Uhlenbeck spread** `dε = κ(θ−ε)dt + σdW`, with cost c and urgency ρ (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:6381-6451` (p. 294–296, checked)):
  - The exit level solves `(ε* − c)F₊'(ε*) = F₊(ε*)`, where `F₊(ε) = ∫₀^∞ u^{ρ/κ−1} e^{−√(2κ/σ²)(θ−ε)u − u²/2} du`.
  - Double-sided, the long entry equals the short exit.
  - The book's table (exit 1.7460 at κ = 1, 1.4367 at κ = 4) **reproduces with a standard-library integral**, so the bands can be computed offline per basket and pasted into `PARAMS` *(checked: recomputed 2026-10-12)*.

## Where they disagree
Whether residual baskets beyond Pebbles pay live (Alpha Search traded several; Baguette Fromage lost on Microchips and Sleep Pods).

## What it means for our code
Since 2026-10-13 `bots/template.py` has a `basket` mode (`basket_target`, `hedge_target`: `bots/template.py:354-375`): the basket trades its spread, its wall mid less the legs' weighted wall mids, with the level settings, and legs with `hedge` hold `-weight × hedge_ratio` per basket held. A fixed-sum family is a basket with legs of weight −1. Measured with `experiments/baskets.py` (`IDEAS.md`, "Trading a basket's spread"):
- **The spread reverts within a day around a level that moves between days:** PICNIC_BASKET2's daily means were 58, −4 and 37 with sds of 52–55. So the level comes from the other days, and the band is set in sds.
- **Held out:** 71k on P3 round 2 and 294k on P2 round 3 over three days, against 20k for plain market making. In-sample 139k and 335k (re-run 2026-10-13 after `level_exit` was fixed to fire when the price jumps past the level; before, 83k and 281k).
- **Hedging lost** 11–30% in-sample, as UChicago found for its ETF: the basket is the mispriced leg. Frankfurt's 0.5 hedge is not supported here.
- **Baskets only take:** their price jumps several ticks at once, and under `--resting` full-room quotes on them were picked off (−1,125k on the gift basket).

## How to test it here
Ad hoc bands are done (`uv run python -m experiments.baskets`: k × sd, held-out days). Still open: fit κ, θ, σ of the premium on the training days, compute the optimal bands from Cartea et al.'s (11.2)–(11.4), and compare them with the k × sd grid on held-out days.

Needs `--data p4`. First reproduce the Pebbles sum and its σ from the round 5 files; then test the integer-weight search with out-of-sample days per [validation-and-overfitting](validation-and-overfitting.md). On the day: check the Arena's public data for exact sums before searching anything.

## Sources
[Cartea et al., book](../sources/algorithmic-and-hft.md), [Harris](../sources/harris-trading-and-exchanges.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Linear Utility](../sources/prosperity2-linear-utility.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [DU Trading](../sources/prosperity4-du-trading.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [UChicago](../sources/uchicago-trading-2026.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md).
