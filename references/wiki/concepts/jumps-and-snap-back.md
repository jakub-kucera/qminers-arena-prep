---
title: Jumps that snap back (round-number discretisation)
type: concept
updated: 2026-10-13
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
The template's `jump` mode (`python/bots/template.py:583-630`), off by default. A move of the fair value of at least `jump_min` is a jump; once `jump_seen` of the day's jumps have followed another and `jump_share` of those reversed it, the target is the full limit against each jump, held until the next one (or `jump_hold` ticks), and `clear` crosses up to `jump_edge` toward it. Unlike DU's round-100 test, the gate doesn't assume a grid: it measures the reversal on the day, so the mode can be switched on for every product. *(checked: `python/experiments/p4_jumps.py`, 2026-10-13)*:
- **The teams' Robots PnL is one product-day.** ROBOT_DISHES on day 4 made 280k of DU's 309k and 437k of Baguette Fromage's 445k in our engine. That day its wall mid sits on a multiple of 100 on 88% of ticks and 87% of its 741 jumps reverse the one before. Baguette Fromage's README says the Robots lost 4.3k live (`prosperity4-baguette-fromage/README.md:1041`).
- **Both rules reproduce in the template:** holding until the next jump makes 432k on that day (Baguette Fromage 437k), holding 3 ticks and then crossing back 278k (DU 280k).
- **On all 50 products**, on top of plain market making: +501k over the three days, every day positive (+46k, +4k, +451k); also positive under `worse` fills and `--resting` taking only. Fading every jump without the gate lost 184k on day 3, on Pebbles and Microchips, whose jumps reverse about half the time.
- **Nowhere else in P2–P4:** no other round has a product with 20 jumps of 50 a day, and P3's jumps of 10 reverse 37–57%.
- **Practice data:** `arena.sim`'s `ROBOT_DISHES` preset copies the jumping day (jumps of 100 in bursts, 87% reversing the one before, `python/arena/sim.py:236`). In the market, the jump mode makes about 392k a day there against 2k for plain market making (`IDEAS.md`, "Fading jumps that snap back").

## How to test it here
`arena.diagnose` notes it first, in any format: `jumps of 6+ spreads snap back` on a day where 75% of 20 or more such moves reverse the one before (since 2026-10-26; only the four P4 round 5 product-days above pass in P2–P4), with the jumps' usual size, the share exactly that size, the grid (the wall mid's most common value modulo the size) and `jump_min` at half the size (since 2026-10-27: on ROBOT_DISHES day 4, size 100 on all 743, at 0 mod 100 on 89% of ticks). `uv run python -m experiments.p4_jumps` (part 1 scans any data with `--data`, `--days` and `--jump-min`; part 2 runs the template on P4 round 5). Results and the parameter sweep are in `IDEAS.md`, "Fading jumps that snap back". On the day: look for a grid in the Arena's prices before anything else; this is a property of one generator, and in P4 it came on one product-day in the data and on another live.

## Sources
[DU Trading](../sources/prosperity4-du-trading.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md). [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [HumzahM](../sources/uchicago-2025-case2-humzah.md).
