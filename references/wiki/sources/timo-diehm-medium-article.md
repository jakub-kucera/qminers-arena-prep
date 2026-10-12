---
title: Timo Diehm's essay "How to (almost) win in Competitive Environments"
type: source
repo: literature_md/how-to-almost-win
status: read
updated: 2026-10-11
---

# Timo Diehm, "How to (almost) win in Competitive Environments" (Medium, 28 Apr 2025)

## What it is
A 7-minute essay by a member of Frankfurt Hedgehogs (Arne Witt, Marvin Schuster, Timo Diehm). Their claims: 3rd of 3,000+ in Optiver's Ready Trader Go 2023, 5th of 9,000+ in Prosperity 2 and 2nd of 12,000+ in Prosperity 3 (`how-to-almost-win.md:22`). It is a **mindset essay with no tactics**: the authors say "our focus is not on specific tactics" and give no strategy details for Ready Trader Go. The PDF is a browser print of the page in `literature_raw/`; the converted text is `literature_md/how-to-almost-win/how-to-almost-win.md` (decorative images removed).

## Layout and code map
Three principles:
1. **Question your assumptions** (`how-to-almost-win.md:32-46`). In Ready Trader Go the task was framed as "making markets"; they realised the true objective was to maximise profit and found a way to outperform "that had very little to do with traditional market making". In Prosperity they found some products' price changes were generated almost randomly, so forecasting was pointless and the edge was in liquidity dynamics and fills.
2. **Understand the problem at a deeper level than anyone else** (`how-to-almost-win.md:48-86`). In Ready Trader Go they "studied the source code of the simulation in detail" and parsed every rule on matching, delays and other teams' likely behaviour. In Prosperity they "designed numerous controlled algorithm tests — not to optimize trading performance, but to test the behavior of the environment itself": how prices are generated, how matching works, whether some bots are predictable; plus custom dashboards.
3. **Go the extra mile** (`how-to-almost-win.md:87-106`): preparation started weeks or months before each event (dashboards, backtesters, study of past competitions and old GitHub repositories), close teamwork, and 12-hour-plus days near deadlines.

## What carries over
- If the Arena hands out its simulator or evaluator source (Qminers did in 2025: `qminers-hackathon-2025/src/environment.py`), **read it before designing anything**.
- Spend the first hours on controlled experiments that probe the environment, not on strategies: see [probing-the-environment](../concepts/probing-the-environment.md).
- Preparation is a stated edge; the repo's `TODO.md` and `ON_THE_DAY.md` are the same idea.

## Traps
It is advice, not evidence: no numbers, and written by a team whose method (mapping the generator) is also visible in their README and code ([Frankfurt](prosperity3-frankfurt-hedgehogs.md)). The article's own claim that Ready Trader Go could be beaten without market making is unsupported here; no winning Ready Trader Go bot is public.

## Read depth
- **Read:** the whole article (`how-to-almost-win.md:1-142`).
- **Unread:** nothing; but it has no technical content to read.

## Cited by
[probing-the-environment](../concepts/probing-the-environment.md), [overview](../overview.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md).
