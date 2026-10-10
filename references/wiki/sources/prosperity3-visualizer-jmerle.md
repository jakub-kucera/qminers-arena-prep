---
title: jmerle's Prosperity 3 visualizer (log format)
type: source
repo: prosperity3-visualizer-jmerle
status: mapped
updated: 2026-10-10
---

# jmerle's Prosperity 3 visualizer (MIT, React/TypeScript)

## What it is
The source of the hosted visualizer (`jmerle.github.io/imc-prosperity-3-visualizer/`). It reads a backtest or website log and shows PnL, positions, the book and orders per timestamp. Use the hosted version; read the source only for the log format.

## Layout and code map
- `src/utils/algorithm.tsx` (315 lines) defines the log format: per-tick `sandboxLog` and `lambdaLog` entries (`src/utils/algorithm.tsx:203-225`) and an `Activities log:` CSV block (`src/utils/algorithm.tsx:47`: `day;timestamp;product;` then 3 bid and 3 ask price/volume pairs and the mid, columns 0–15). Each tick's `lambdaLog` carries the **compressed state that the trader's own `Logger.flush(...)` printed** (listings, order depths, trades, observations, orders, conversions, `traderData`, the trader's log text). That is why every Prosperity 3/4 trader in the clones starts with ~110 lines of `Logger` boilerplate (for example `prosperity4-baguette-fromage/Strategies/Phase1.py:36-170`).
- `src/pages/visualizer/` holds the panels (24 files); `src/models.ts` the types.

## What carries over
If our engine should write a visualizer-compatible log (it writes CSVs today, `arena/report.py`), this file is the specification.

## Traps
Needs the trader to print the `Logger` format; a trader without it shows prices and PnL only.

## Read depth
- **Read:** `src/utils/algorithm.tsx:36-70` and `grep` hits.
- **Unread:** the React components.

## Cited by
[backtesting-and-tooling](../concepts/backtesting-and-tooling.md).
