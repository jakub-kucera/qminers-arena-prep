---
title: Mascioli, Gu, Wang, Chakraborty & Wellman, "A financial market simulation environment for trading agents using deep RL" (2024)
type: source
repo: literature_md/pymarketsim
status: partly-read
updated: 2026-10-14
---

# Mascioli, Gu, Wang, Chakraborty & Wellman, "A financial market simulation environment for trading agents using deep reinforcement learning" (PyMarketSim, ICAIF 2024)

## What it is
The design of PyMarketSim, an agent-based market for training and evaluating trading agents (open source, github.com/umichsrg/pymarketsim, `pymarketsim.md:43` (p. 1)). Split from the local `ICAIF_2024_proceedings.pdf` (pp. 117–125 printed). `harder-rounds` A1 says to read it before writing our day generator.

## Main results (the spec)
- **A mean-reverting fundamental** (`pymarketsim.md:143` (p. 4)): `f_t` reverts to a mean `f̄` at rate `κ`, with Gaussian shocks of variance `σ_s²` *(unchecked)*; agents know the process, so they can estimate the final value, at which holdings are liquidated.
- **Private values** per unit of position, so background traders have their own reasons to buy or sell.
- **Zero-intelligence background traders** shade their valuation by a random surplus, and trade at once if the quote already offers enough of it (the threshold `η`).
- **Arrivals:** each agent's next arrival is drawn from a geometric distribution (`pymarketsim.md:87` (p. 3)), so most time steps are empty.
- Market makers quote ladders; learned "TRON" agents and equilibria by empirical game-theoretic analysis sit on top.

## Assumptions against the Arena
- A generic simulator; the Arena's own is unknown. **For A1** *(inferred)*: these components are the minimal set for a reactive day: a fundamental the bots chase, takers with private reasons to trade, and a market maker whose ladder sets liquidity. Calibrate them to the Arena's download with the Get Real checks ([lob-simulation-realism](lob-simulation-realism.md)).

## In our notation
| PyMarketSim | Ours |
|---|---|
| fundamental `f_t` | the hidden value a day generator would draw; `fixed_fair` or `level` in the template |
| market maker's ladder | the walls `wall_mid` reads |
| liquidation at the final fundamental | the Arena's end-of-round mark (`ON_THE_DAY.md`) |

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction, the market and agent specification (sections 3–4).
- **Skimmed:** the RL agents and the game-theoretic results.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md).
