---
title: Working with AI agents in a competition
type: concept
updated: 2026-10-10
---

# Working with AI agents in a competition

## Summary
The newest write-ups all used AI assistants heavily and say the same thing: use them freely for exploratory tooling, and understand every line of production strategy code. The Arena's rules allow AI tools (`ON_THE_DAY.md`).

## What the sources say
- **Baguette Fromage (4th):** AI agents "massively increased team productivity"; exploratory tooling could be messy ("vibe coded") but production strategy code had to be understood completely; they also used LLM simulations to estimate other players' behaviour in manual adversarial rounds; preparation was "extremely" important, and fast workflows matter because "there are only 30 hours left in a round" (`prosperity4-baguette-fromage/README.md:1504-1566`). Machine learning mattered "less than expected" (`prosperity4-baguette-fromage/README.md:1543-1552`).
- **Ryan Challman (57th):** assistants drafted sweep harnesses, plots and the Monte Carlo for a manual round; "the strategy and parameter calls were ours" (`prosperity4-ryan-challman/README.md:260-262`).
- **DU Trading (10th):** LLMs "allowed us to rapidly test ideas and perform large-scale analysis. However, we found they still lack some trading intuition" (`prosperity4-du-trading/README.md:224`).
- **Leo-Hawking (top 0.5%, two people with an agent and a `Claude.md`)**, read online only: LLMs drifted toward generic microstructure ideas (imbalance, latency, queue priority) instead of local alpha, and a human and an agent agreeing entrenched a wrong belief (`references/README.md`, "Read online, not cloned"; not read in full by us).
- **A failure mode seen in the clones:** AI-written documentation that overstates (AlgoTrade's "proof" documents, [AlgoTrade](../sources/algotrade2026-pitfa19.md)) and published code that does not match its README ([DU](../sources/prosperity4-du-trading.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md)).

## Where they disagree
No disagreement; the differences are in how much of the production code each human read.

## What it means for our code
`CLAUDE.md` forbids following clones' own agent files, requires checking `literature_md` formulas against the PDF, and keeps the bot stdlib-only. The wiki's rules (*their claim* / *checked*, read depth) apply to agent output too.

## How to test it here
Before the event, give the agent a bounded task end to end (for example the `--data p4` alias) and check what it claims against a run. On the day, keep exploratory notebooks separate from the single submitted file.

## Sources
[Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [DU Trading](../sources/prosperity4-du-trading.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md).
