---
title: Byrd, Hybinette & Balch, "ABIDES: towards high-fidelity market simulation for AI research" (2019)
type: source
repo: literature_md/abides-simulator
status: read
updated: 2026-10-14
---

# Byrd, Hybinette & Balch, "ABIDES: towards high-fidelity market simulation for AI research" (arXiv:1904.12066, 2019)

## What it is
A 13-page description of ABIDES, an open-source discrete-event market simulator: a kernel, an exchange agent with a price-time order book, and trading agents that talk to it only through messages. It is the standard open template for "a realistic exchange simulation", so it is our best guess at the kind of machine the Arena runs ([harder-rounds](../concepts/harder-rounds.md), A1).

`references/SEARCH_LOG.md` skipped it on 2026-10-10 as "heavier than the question needs". The question changed with the harder-rounds research, and it was added on 2026-10-14.

## Main results
- **Each agent has a computation delay.** It is added to the agent's clock after each action and to the send time of each message it sends (`abides-simulator.md:69` (p. 4)). Its stated purpose is the trade-off between "simpler, faster predictors and slower, more powerful predictors": "heavier thinkers will take longer to deliver a resulting order ... and will be unable to act as frequently" (`abides-simulator.md:52` (p. 3)). Latency is a configured pairwise matrix plus noise (`abides-simulator.md:70` (p. 4)).
- **Deterministic but random.** One master seed generates one random generator per agent, so a run repeats exactly, and changing one agent doesn't shift the other agents' random draws (`abides-simulator.md:71` (p. 4)). That is the property an organiser needs to rerun a team's bot and get the same score.
- **The book:** best price first, then the oldest order at that price. Partial fills leave the rest of the resting order in the book (`abides-simulator.md:129` (p. 6)). There is no slippage model: slippage comes from other agents trading while an order is in flight (`abides-simulator.md:134` (p. 6)).
- **Background agents** mix a prior belief with a noisy observation of a historical trade. They trade toward that value against the last simulated trade, and cancel their open orders on each wake-up (`abides-simulator.md:182` (p. 9)). The mean-reverting fundamental used by later configurations comes from [Wang & Wellman](spoofing-abm.md), which the paper credits.
- **Impact persists.** One market buy for a share ("greed") of the visible liquidity moves the simulated price for a long time after, in spite of the background agents pulling toward historical levels (`abides-simulator.md:209` (p. 11), `abides-simulator.md:221` (p. 12)).
  - The impact trader's profit grew with its size, from $2,633 at greed 0.3 to $12,502 at greed 1.9.
  - Its profit per share fell, from $2.14 to $1.60.

## Assumptions against the Arena
- **Nanosecond event time, not ticks.** If the Arena is built this way, our per-tick `step` becomes an event callback, which needs engine work (`ON_THE_DAY.md`, "How is the bot called?").
- **The computation delay is configured, not measured.** It doesn't come from the agent's real CPU time, which keeps runs reproducible. So even in ABIDES, speed matters only through a delay the organiser chooses ([harder-rounds](../concepts/harder-rounds.md), E2) *(checked: line 69 describes a stored value)*.
- **The paper's agent populations are not the ones in the current code.** RMSC04's noise, value, momentum and adaptive market-maker agents (summarised in [online-articles](online-articles.md)) come from the later JPMorgan release, not from this paper.

## In our notation
- The engine's `run_market` already does what ABIDES's kernel does in one tick: everyone sees the same state, then actions are processed in a seeded shuffle. A day generator would add the background agents as participants with their own seeded generators, which is the property on line 71.
- "Greed" is our take size over the visible depth (A2 in [harder-rounds](../concepts/harder-rounds.md)).

## Traps
- **The impact numbers are one stock and one day** (IBM, 30 Sep 2008), with 100 background agents. They are a demonstration, not a calibration.
- **The validation is visual**, simulated trades against historical ones (Figure 4). The realism checks are in [lob-simulation-realism](lob-simulation-realism.md).

## Read depth
- **Read:** the whole paper.
- **Not read:** the code (`abides-sim/abides`, the JPMorgan fork). The RMSC04 config was read online only.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [lob-simulation-realism](lob-simulation-realism.md), [spoofing-abm](spoofing-abm.md).
