---
title: Jumps that snap back (round-number discretisation)
type: concept
updated: 2026-10-10
---

# Jumps that snap back

## Summary
In Prosperity 4 round 5 several products' prices jumped by multiples of 100 and then returned within a few ticks. Three teams describe the same effect; the simplest rule (take the opposite side after a jump, hold three ticks) was reported to have produced hundreds of thousands in one round.

## What the sources say
- **DU's rule:** a product is "discrete" when its wall mid has been an exact multiple of 100 for three consecutive ticks; on the next move, go to the full opposite position at the far wall and hold `HOLD_TICKS = 3` (`prosperity4-du-trading/round5.py:721-770`, `prosperity4-du-trading/round5.py:178`). Applied to **all** products, not only those showing it in the sample; ~660,000 of the round's PnL, payoff about +1,000 if it reverts and −160 if not (`prosperity4-du-trading/README.md:182-197`). Their reading: the internal price is a random walk and a rounding function is applied, so it bounces between e.g. 49 and 50 internally.
- **Baguette Fromage's "100-jump":** detect a large move (≥ 60) after a few stable ticks, assume reversion, take the opposite side (`prosperity4-baguette-fromage/README.md:1000-1041`, constants `prosperity4-baguette-fromage/Strategies/Phase2_Final.py:672-677`); Oxygen Shake Chocolate was the clearest case and the family made +669k (`prosperity4-baguette-fromage/README.md:919-931`).
- **DTU:** `OXYGEN_SHAKE_CHOCOLATE` alone made +587,831 of +702,835 through plain inside-the-spread market making on a "dislocated" book, and they deliberately left it on the plain variant (`prosperity4-dtu-quant-lab/README.md:191-202`). Whether this is the same effect is their wording, not their statement.
- **A related, riskier regime:** Ryan Challman's `ROBOT_DISHES` had lag-1 return autocorrelation of −0.001, −0.004 and −0.290 on three days; the mean-reversion book made $389k on the hot day versus $11k and $4k; they sized it at 0.06 so as not to bet on the hot regime recurring (`prosperity4-ryan-challman/README.md:115-141`).

- **Missed by a strong team:** Leo-Hawking believed the round-100 jumps carried no alpha and the AI agent agreed; they list it as the missed "sub-obvious alpha" of round 5 (algorithmic rank 96th) (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:581-609`).
- **The same kind of structure elsewhere:** in UChicago 2025 Case 2 the returns jumped on exactly every 10th tick, found by zooming in on the data (`uchicago-2025-case2-humzah/chicago8.py:35`).

## Where they disagree
Sizing: DU applied the rule to every product at full size; Ryan Challman cut a similar signal to a small weight on purpose; Baguette Fromage's family gain was concentrated in one product. No team shows the rule failing live.

## What it means for our code
Nothing in `bots/template.py`. It needs a per-product "last k wall mids were multiples of N" detector in the fair-value section and an aggressive taker in the execution section.

## How to test it here
Needs `--data p4` (round 5). Scan the wall mids for multiples of 100 and the share of jumps that revert within 3 ticks, per product and per day; then run the rule with the worst-day criterion. On the day: look for a grid in the Arena's prices before anything else; this is a property of one generator.

## Sources
[DU Trading](../sources/prosperity4-du-trading.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md). [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [HumzahM](../sources/uchicago-2025-case2-humzah.md).
