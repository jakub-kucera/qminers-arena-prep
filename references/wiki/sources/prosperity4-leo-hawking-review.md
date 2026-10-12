---
title: Leo-Hawking's Prosperity 4 retrospective (top 0.5%, human plus AI agent)
type: source
repo: online-snapshots
status: partly-read
updated: 2026-10-11
---

# Leo-Hawking, "IMC Prosperity 4 Algorithmic Trading Retrospective" (their claim: top 0.5%, two people with an AI agent)

## What it is
A GitHub repo (201 files, 245 MB, 121 code files, no licence) with a 618-line README that doubles as a retrospective. Read online and saved as `references/online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md`; the code was not cloned. Algorithmic ranks by round (their numbers): R1 170th, R2 77th, R3 95th, R4 132nd, R5 96th (`Leo-Hawking_IMC-Prosperity-4-Review.README.md:91-100`). The authors say outright that the repo "preserves the competition-time artifacts" and some scripts may not run (`Leo-Hawking_IMC-Prosperity-4-Review.README.md:107-113`).

## Layout and code map
- Workflow loop `Leo-Hawking_IMC-Prosperity-4-Review.README.md:131-146`: **probe → visualize → hypothesize → spec doc → implement → backtest and retrospect**. At the start of each round they submit empty strategies and mechanical grid-quoting probes to map the matching mechanics; they write each strategy as a markdown spec (every branch and parameter source) before coding it.
- Round 0 probe results (`Leo-Hawking_IMC-Prosperity-4-Review.README.md:198-214`): **no queueing** (orders at the best price are processed regardless of arrival time), **bots only hit the best price**, no two trade prices at one timestamp, active takes can cross several levels. Corollary: quoting one unit better than the best intercepts all favourable bot-initiated trades.
- Round 4 (`Leo-Hawking_IMC-Prosperity-4-Review.README.md:408-446`): holding PnL of every bot is a random walk; bucketing each bot's trade price by its deviation from an EMA identified **Mark 14 and Mark 55** as informed; following them gave stable execution improvement but "limited alpha gain" and the rank fell from 95th to 132nd, which they attribute to "strategy-migration inertia plus risk stacking" (the same mean-reversion logic on correlated assets builds positions in the same direction at once).
- Overall retrospective (`Leo-Hawking_IMC-Prosperity-4-Review.README.md:581-609`): LLMs "gravitate toward generic topics — microstructure imbalance signals, latency handling, queue priority" even with the rules in a `Claude.md`; a human and an AI converging on a consensus **entrench errors** (they believed the round-100 jumps had no alpha and the AI agreed); the shared backtester bloated across five different markets, so they would write a light ad-hoc backtester per round and keep only the matching mechanics generic; recheck cross-round assumptions every round; "the gap between top players is precisely the cumulative effect of these sub-obvious alphas".

## What carries over
Probing at the start of a round, specs before code, per-round throwaway backtesters on a stable core, and an explicit habit of asking "what environment parameters does this belief depend on, and do they still hold?". See [probing-the-environment](../concepts/probing-the-environment.md), [ai-assisted-work](../concepts/ai-assisted-work.md), [informed-counterparties](../concepts/informed-counterparties.md).

## Traps
- The algorithmic ranks (77th to 170th) are far from the "top 0.5%" headline, which presumably comes from the overall total including the manual track (our inference). Treat the reflections as an honest account of a good-not-great run.
- The round 4 informed-bot finding disagrees with DU, DTU, Ryan Challman and Baguette Fromage on which Mark matters (see [contradictions](../contradictions.md), row 3).

## Read depth
- **Read:** `Leo-Hawking_IMC-Prosperity-4-Review.README.md` lines 91–150, 198–214, 408–446, 581–618.
- **Mapped:** the round-by-round headings.
- **Unread:** rounds 1, 2, 3 and 5 narratives, the Chinese README, all code.

## Cited by
[probing-the-environment](../concepts/probing-the-environment.md), [ai-assisted-work](../concepts/ai-assisted-work.md), [informed-counterparties](../concepts/informed-counterparties.md), [queue-position-and-fills](../concepts/queue-position-and-fills.md), [jumps-and-snap-back](../concepts/jumps-and-snap-back.md), [risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md), [validation-and-overfitting](../concepts/validation-and-overfitting.md).
