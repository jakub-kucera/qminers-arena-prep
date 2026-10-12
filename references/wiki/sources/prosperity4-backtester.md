---
title: prosperity4btest (the only copy of the Prosperity 4 data)
type: source
repo: prosperity4-backtester
status: partly-read
updated: 2026-10-13
---

# `prosperity4btest` (nabayansaha, PyPI, MIT; a fork of jmerle's Prosperity 3 backtester)

## What it is
The Prosperity 4 port (`prosperity4bt/`, 1,681 lines) **with the Prosperity 4 data, rounds 0 to 5**. Copyright line is jmerle's (a fork).

## Layout and code map
- Data: `prosperity4bt/resources/round0` (tutorial: `EMERALDS`, `TOMATOES`) to `round5`. Days: R1 −2, −1, 0; R2 −1, 0, 1; R3 0, 1, 2; R4 1, 2, 3; R5 2, 3, 4 *(checked)*. 10,000 ticks per day, timestamps `0 … 999,900` in steps of 100. Only round 4's trade files carry `Mark XX` names *(checked)*. R3/R4 products: Hydrogel, Velvetfruit and ten `VEV_*`; Osmium and Pepper Root exist only in R1/R2.
- `prosperity4bt/data.py`: `LIMITS` lists only the 50 round 5 products (10 each) and `DEFAULT_POSITION_LIMIT = 50` applies to everything else (`prosperity4bt/data.py:8`, `prosperity4bt/data.py:67`): **a wrong limit is silent**.
- Differences from the Prosperity 3 runner *(checked: diff)*: matching clamps each fill to the remaining room (`volume = min(order, book, max_buy)` and skip if ≤ 0). That clamp acts only on top of `enforce_limits`, which still cancels every order for a product whose buys or sells could breach the limit (`prosperity4bt/runner.py:124-145`), as Prosperity and our engine do; `--limit PRODUCT:LIMIT` override; `--round2-access unknown|accepted|rejected` for the blind `Trader.bid()`; `--counterparty-info/--no-counterparty-info`; `prosperity4bt/metrics.py` (drawdown, Sharpe, Sortino, Calmar); an `invest` sub-command for round 2's manual puzzle (`prosperity4bt/__main__.py:382`).

## What carries over
The P4 data, which our `--data p4` loads (2026-10-12). Position limits for P4 products come from IMC's round pages and the teams' code (see [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md)).

## Checked against our engine (2026-10-13)
Four published traders on P4 rounds 1 and 2 (Baguette Fromage's `Phase1.py`, DTU's round 1 and round 2 traders, DU's `round2.py`; 24 trader-days) give **identical PnL per product per day** here and in our engine. The numbers are on [Baguette Fromage](prosperity4-baguette-fromage.md), [DTU](prosperity4-dtu-quant-lab.md) and [DU](prosperity4-du-trading.md). Run it with the `cli` subcommand, which the README's examples omit: `uv tool run --from ./references/prosperity4-backtester --with numpy prosperity4btest cli <trader> <round> --data references/prosperity4-backtester/prosperity4bt/resources --limit ASH_COATED_OSMIUM:80 --limit INTARIAN_PEPPER_ROOT:80 --no-out`. Its drawdown includes the empty-book `mid_price` 0.0 rows: 1,127,712 for DTU's round 1 trader, against about 1,300 once those rows are skipped.

## Traps
Default limit 50 for unlisted products; no conversions. The tutorial products' limits are 80 each: the README's own example passes `--limit EMERALDS:80 --limit TOMATOES:80` (`prosperity4-backtester/README.md:146`). An empty book has `mid_price` 0.0 in the price files *(checked: 203 rows across the six rounds)*; marked at face value, a held position shows a fake loss for that tick.

## Read depth
- **Read:** README head, `prosperity4bt/__main__.py` options, runner diff against Prosperity 3, data listings and `LIMITS`.
- **Mapped:** `prosperity4bt/metrics.py` by `grep`.
- **Unread:** the rest.

## Cited by
[backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [informed-counterparties](../concepts/informed-counterparties.md).
