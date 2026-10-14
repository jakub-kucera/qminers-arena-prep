---
title: Lopez-Lira, "Can large language models trade? Testing financial theories with LLM agents in market simulations" (2025)
type: source
repo: literature_md/llm-agents-market-simulation
status: partly-read
updated: 2026-10-14
---

# Lopez-Lira, "Can large language models trade? Testing financial theories with LLM agents in market simulations" (arXiv:2504.10789, 2025)

## What it is
An open-source simulated stock market (persistent book, market and limit orders, partial fills, dividends) whose traders are LLM agents with assigned strategies, information and endowments, answering in structured outputs with their reasoning (`llm-agents-market-simulation.md:7` (p. 1)). For the LLM zoo, `harder-rounds` D2; fetched from arXiv.

## Main results
- **LLMs follow their brief:** they act consistently as value investors, momentum traders or market makers as instructed (`llm-agents-market-simulation.md:7` (p. 1)).
- **The market they make** shows price discovery, bubbles, under-reaction and strategic liquidity provision.
- **The risk the paper names** (`llm-agents-market-simulation.md:35` (p. 4)): agents built on similar foundation models may respond in correlated ways, a systemic risk.

## Assumptions against the Arena
- Its agents are asked once per round for a decision; Arena bots are code that runs every tick. The zoo would use LLMs to *write* bots from the same docs, not to trade live *(inferred)*; the paper's archetype prompts are the templates.

## In our notation
The archetypes (value, momentum, market maker, contrarian, sentiment-biased) map to the zoo's rival bots for `--vs`.

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction, the agent types and their prompts.
- **Skimmed:** the experiments and the decision analysis.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [ai-assisted-work](../concepts/ai-assisted-work.md).
