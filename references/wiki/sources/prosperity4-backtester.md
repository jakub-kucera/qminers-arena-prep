---
title: prosperity4btest (the only copy of the Prosperity 4 data)
type: source
repo: prosperity4-backtester
status: partly-read
updated: 2026-10-10
---

# `prosperity4btest` (nabayansaha, PyPI, MIT; a fork of jmerle's Prosperity 3 backtester)

## What it is
The Prosperity 4 port (`prosperity4bt/`, 1,681 lines) **with the Prosperity 4 data, rounds 0 to 5**. Copyright line is jmerle's (a fork).

## Layout and code map
- Data: `prosperity4bt/resources/round0` (tutorial: `EMERALDS`, `TOMATOES`) to `round5`. Days: R1 −2, −1, 0; R2 −1, 0, 1; R3 0, 1, 2; R4 1, 2, 3; R5 2, 3, 4 *(checked)*. 10,000 ticks per day, timestamps `0 … 999,900` in steps of 100. Only round 4's trade files carry `Mark XX` names *(checked)*. R3/R4 products: Hydrogel, Velvetfruit and ten `VEV_*`; Osmium and Pepper Root exist only in R1/R2.
- `prosperity4bt/data.py`: `LIMITS` lists only the 50 round 5 products (10 each) and `DEFAULT_POSITION_LIMIT = 50` applies to everything else (`prosperity4bt/data.py:8`, `prosperity4bt/data.py:67`): **a wrong limit is silent**.
- Differences from the Prosperity 3 runner *(checked: diff)*: matching clamps each fill to the remaining room (`volume = min(order, book, max_buy)` and skip if ≤ 0); `--limit PRODUCT:LIMIT` override; `--round2-access unknown|accepted|rejected` for the blind `Trader.bid()`; `--counterparty-info/--no-counterparty-info`; `prosperity4bt/metrics.py` (drawdown, Sharpe, Sortino, Calmar); an `invest` sub-command for round 2's manual puzzle (`prosperity4bt/__main__.py:382`).

## What carries over
The P4 data for our `--data p4` (TODO). Position limits for P4 products come from the teams' code (see [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md)).

## Traps
Default limit 50 for unlisted products; no conversions; tutorial products' limits unknown.

## Read depth
- **Read:** README head, `prosperity4bt/__main__.py` options, runner diff against Prosperity 3, data listings and `LIMITS`.
- **Mapped:** `prosperity4bt/metrics.py` by `grep`.
- **Unread:** the rest.

## Cited by
[backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [informed-counterparties](../concepts/informed-counterparties.md).
