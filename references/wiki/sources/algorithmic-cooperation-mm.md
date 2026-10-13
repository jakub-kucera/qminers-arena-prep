---
title: Han, "Can maker-taker fees prevent algorithmic cooperation in market making?" (2022)
type: source
repo: literature_md/algorithmic-cooperation-mm
status: read
updated: 2026-10-13
---

# Han, "Can maker-taker fees prevent algorithmic cooperation in market making?" (arXiv:2211.00496, ICAIF 2022)

## What it is
An 8-page simulation study: N market makers, each an independent Q-learner choosing a spread level on a discrete tick grid, quote in a "semi-realistic" market for many rounds. Market orders fill the tightest quotes first, and the level that runs out is split pro-rata among the makers there (`algorithmic-cooperation-mm.md:92` (p. 3)): price priority, unlike [competing-dealers](competing-dealers.md). The question is whether the makers learn to keep spreads wide without communicating, and whether exchange fees break that. Found in the arXiv sweep of 2026-10-13.

## Main results
- **Learned cooperation:** independent Q-learners often settle on spreads above the competitive one (the one-tick undercut is the Nash equilibrium of the one-round game), with no communication (`algorithmic-cooperation-mm.md:13` (p. 1)). The companion paper (arXiv:2206.05410) finds the same as a repeated stag-hunt game, and that more makers do not necessarily remove it.
- **What sustains it** (`algorithmic-cooperation-mm.md:63` (p. 2)): high mid-price volatility helps the makers keep spreads wide; more inventory-averse makers need larger rebates to narrow them; with enough makers on a venue, fees mostly raise investors' costs.
- **Discrete ticks matter:** a small rebate may not be worth undercutting by a whole tick (`algorithmic-cooperation-mm.md:59` (p. 2)).

## Assumptions against the Arena
- **Learning agents over many rounds.** In the Arena a team's bot is fixed within a round, and teams adapt only between rounds (four of them), so tacit cooperation would have to emerge across teams' redesigns *(inferred)*. Exchange-run bots, if they set the spread, do not learn.
- **It matters only if the market is shared** (`ON_THE_DAY.md`, "Is the market shared with the other teams?").

## In our notation
- The one-round game is what `--vs` plays: our template against copies split Osmium's spread, and undercutting by a tick takes the flow ([shared market](../concepts/shared-market-and-adversaries.md)).
- A rival that keeps a wide spread leaves room for a one-tick-inside quote: the template's `make` already steps one tick inside the best (`bots/template.py:488-493`).

## Traps
- The market is "semi-realistic": no order book beyond the makers' own quote levels, and a stylised investor demand.

## Read depth
- **Read:** the abstract, introduction and section 2 (the market and the game); the results' summary in the introduction.
- **Skimmed:** the experiments (section 3).

## Cited by
[shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md).
