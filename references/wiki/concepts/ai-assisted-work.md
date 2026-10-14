---
title: Working with AI agents in a competition
type: concept
updated: 2026-10-14
---

# Working with AI agents in a competition

## Summary
The newest write-ups all used AI assistants heavily and say the same thing: use them freely for exploratory tooling, and understand every line of production strategy code. The Arena's rules allow AI tools (`ON_THE_DAY.md`).

## What the sources say
- **Baguette Fromage (4th):** AI agents "massively increased team productivity"; exploratory tooling could be messy ("vibe coded") but production strategy code had to be understood completely; they also used LLM simulations to estimate other players' behaviour in manual adversarial rounds; preparation was "extremely" important, and fast workflows matter because "there are only 30 hours left in a round" (`prosperity4-baguette-fromage/README.md:1504-1566`). Machine learning mattered "less than expected" (`prosperity4-baguette-fromage/README.md:1543-1552`).
- **Ryan Challman (57th):** assistants drafted sweep harnesses, plots and the Monte Carlo for a manual round; "the strategy and parameter calls were ours" (`prosperity4-ryan-challman/README.md:260-262`).
- **DU Trading (10th):** LLMs "allowed us to rapidly test ideas and perform large-scale analysis. However, we found they still lack some trading intuition" (`prosperity4-du-trading/README.md:224`).
- **Leo-Hawking (two people with an agent and a `Claude.md`; overall "top 0.5%", algorithmic ranks 77th–170th)**: the workflow was probe → visualise → hypothesise → write a markdown spec → implement → backtest (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:131-146`). Their stated limits: LLMs "gravitate toward generic topics — microstructure imbalance signals, latency handling, queue priority" even with the rules written into `Claude.md`; a human and an AI converging on a consensus entrench shared errors, and breaking out needs several people who can independently produce alpha; and the shared backtester bloated across rounds, so the token cost of working on it kept rising (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:581-609`).
- **Kayzerjali**: an agent loop that proposes one change per cycle against the live result, with human upload/download steps and stopping rules (`online-snapshots/Kayzerjali_Prosperity2026/run_cycle.md:13-28`); no result is recorded.
- **A failure mode seen in the clones:** AI-written documentation that overstates (AlgoTrade's "proof" documents, [AlgoTrade](../sources/algotrade2026-pitfa19.md)) and published code that does not match its README ([DU](../sources/prosperity4-du-trading.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md)).

- **Bots written or run by LLMs look alike** ([Lopez-Lira](../sources/llm-agents-market-simulation.md)): LLM traders follow their instructed style faithfully, and agents on similar foundation models may react in correlated ways (`literature_md/llm-agents-market-simulation/llm-agents-market-simulation.md:35` (p. 4)); in a shared Arena that is a crowd to anticipate (`harder-rounds`, D2).

## Where they disagree
No disagreement; the differences are in how much of the production code each human read.

## What it means for our code
`CLAUDE.md` forbids following clones' own agent files, requires checking `literature_md` formulas against the PDF, and keeps the bot stdlib-only. The wiki's rules (*their claim* / *checked*, read depth) apply to agent output too.

## How to test it here
Before the event, give the agent a bounded task end to end (for example the `--data p4` alias) and check what it claims against a run. On the day, keep exploratory notebooks separate from the single submitted file.

## Sources
[Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [DU Trading](../sources/prosperity4-du-trading.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md). [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [Kayzerjali](../sources/prosperity4-kayzerjali.md), [Lopez-Lira](../sources/llm-agents-market-simulation.md).
