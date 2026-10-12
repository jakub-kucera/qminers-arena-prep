---
title: Drift, regime change and fixed anchors
type: concept
updated: 2026-10-13
---

# Drift, regime change and fixed anchors

## Summary
Products come in three shapes: pegged (Resin, Osmium), drifting deterministically (Pepper Root, +0.1 per tick), and mean-reverting around a level (Hydrogel, Velvetfruit). The costly mistakes were applying one shape's logic to another, and trusting a fixed anchor after the product stopped being pegged.

## What the sources say
- **Deterministic drift** (Pepper Root, `fair = start + 0.001 × timestamp`). Five answers: Baguette Fromage solved a dynamic program for bid/ask thresholds per position (`prosperity4-baguette-fromage/README.md:433-496`); DU held a deliberate **+76 of 80 long bias** and still took wide fills (`prosperity4-du-trading/README.md:71`); Alpha Search accumulated to the limit without overpaying, then mean-reverted around the *future* mid and quoted below the best ask near the end because the spread grew and the settlement mark was the final mid (`prosperity4-alpha-search/README.md:70-75`); Ryan Challman quoted with an aggressive bid and a wider ask (`prosperity4-ryan-challman/README.md:37`); DTU used an asymmetric inventory penalty (`prosperity4-dtu-quant-lab/README.md:97`).
- **A fixed anchor breaks.** Baguette Fromage hard-coded Osmium at 10,000; in round 2 the anchor did not hold, they sat at max inventory, and they say a fail-safe (drift the assumed fair toward the market mid if inventory stays maxed) was missing (`prosperity4-baguette-fromage/README.md:527-539`). DTU's Hydrogel drifted 70 ticks in one session and the fixed-anchor quoter kept buying (`prosperity4-dtu-quant-lab/docs/journey.md:16`).
- **Regime detector** (DTU round 4): PINNED / TRENDING / NOISY from the rolling σ of mid changes (window 200, thresholds 2.0 and 5.0), with a drift detector and an end-of-day flatten (`prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:287-349`).
- **The handed-out days can mislead.** DTU's Hydrogel capsule days were ~99% pinned; the live day was 100% noisy (`prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:261-296`).
- **Mean-reverting underlying.** Baguette Fromage: Ornstein–Uhlenbeck with mean ≈ 5250, θ ≈ 0.15, σ ≈ 9.8, long-run σ ≈ 18, buy below 5232 and sell above 5268 (`prosperity4-baguette-fromage/README.md:740-759`); DU faded moves beyond 8 from 5,250 (`prosperity4-du-trading/round4.py:240`). Ryan Challman's tape fell 65 ticks net on day 3 and the mean-reversion book that had been tuned on rising days lost (`prosperity4-ryan-challman/README.md:79-87`).

- **The opening price can reveal the regime** (heyman7913): some Velvetfruit days opened already 2.5σ above the anchor and a fixed z = 2 short entry lost money before reverting; they blended thresholds across three regime centres (5245, 5267.5, 5295.5) with Gaussian weights keyed to the day's opening price (`online-snapshots/heyman7913_imc-prosperity-4.README.md:356-371`, their claim).

## Where they disagree
Buy-and-hold (many teams) versus market making around the drift (Baguette Fromage, Alpha Search): the market-making teams argue the spread (~14) is too large to ignore (`prosperity4-baguette-fromage/README.md:429`). See [contradictions](../contradictions.md), row 7.

**Measured in our engine (2026-10-13, P4 rounds 1–2):** every published approach that holds a long position wins. Pepper Root alone earns 83–84k a day with Baguette Fromage's thresholds, 82–84k with DU's +76 bias and 79–80k with DTU at the limit ([DU](../sources/prosperity4-du-trading.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md)). Market making around the drift with no target made −25k to +58k a day. These are the teams' traders on their own development days, and the drift never broke in them.

## What it means for our code
`bots/template.py` has `fixed_fair` and smoothed `mid`/`wall_mid`, and since 2026-10-13 a `target` position that `clear` and `skew` work toward (`bots/template.py:173-185`, `bots/template.py:206`). With `target` 80 and `skew` 20, Pepper Root makes 76–78k a day on rounds 1–2, about 6k short of the best published trader (`IDEAS.md`). There is still no drift line, no regime detector and no fail-safe for a pinned inventory; those would be additions to the fair-value section, not the execution section (`CLAUDE.md`).

## How to test it here
With `--data p4`: Pepper Root (rounds 1–2) for drift, done for the long bias; Hydrogel (rounds 3–4) for the broken anchor, not yet. A fixed anchor versus a rolling median versus DTU's detector, ranked by the worst day (`validation-and-overfitting.md`).

## Sources
[Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [DU Trading](../sources/prosperity4-du-trading.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md). Related: [fair-value-and-wall-mid](fair-value-and-wall-mid.md), [validation-and-overfitting](validation-and-overfitting.md). [heyman7913](../sources/prosperity4-heyman7913.md).
