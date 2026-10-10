---
title: jmerle's Prosperity 3 backtester (the one our engine is pinned to)
type: source
repo: prosperity3-backtester-jmerle
status: partly-read
updated: 2026-10-10
---

# jmerle's Prosperity 3 backtester (MIT)

## What it is
`pip install prosperity3bt`; `prosperity3bt <trader.py> <round>[-<day>] [--vis] [--merge-pnl] [--match-trades all|worse|none] [--data DIR] [--print]`. Output is a log in the official submission format, readable by [the visualizer](prosperity3-visualizer-jmerle.md). **Our engine matches it fill for fill** (`tests/test_parity.py`); the Prosperity 2 backtester has the same layout ([page](prosperity2-backtester-jmerle.md)), the Prosperity 4 one is a fork ([page](prosperity4-backtester.md)).

## Layout and code map (`prosperity3bt/`, 1,327 lines)
- `runner.py` (380): `prepare_state` `prosperity3bt/runner.py:30`, `type_check_orders` `prosperity3bt/runner.py:65`, **`enforce_limits`** `prosperity3bt/runner.py:123` (cancel all of a product's orders if the totals could breach), **`match_buy_order`** `prosperity3bt/runner.py:145` and **`match_sell_order`** `prosperity3bt/runner.py:201` (book first, then market trades at the order's own price), `match_orders` `prosperity3bt/runner.py:270`, `run_backtest` `prosperity3bt/runner.py:310`.
- `data.py` (167): `LIMITS` `prosperity3bt/data.py:7` (15 products), CSV readers. `models.py`, `datamodel.py` (the classes a trader imports).
- `parse_submission_logs.py` (`prosperity3bt/parse_submission_logs.py:8-81`): **converts an official submission log (its "Activities log" and "Trade History" blocks) into `prices_<round>_<day>.csv` and `trades_<round>_<day>.csv`**, usage `python -m prosperity3bt.parse_submission_logs <log> <round> <day>`. It is how a submission run becomes backtest data, and what you would do with any log downloaded from the Arena portal.
- README: order matching `README.md:59`, **data files** `README.md:70-83` (rounds 0–8; rounds 6–8 are the data actually used in submission and end-of-round runs), "Conversions are not supported", environment variables that exist only in the backtester `README.md:85`.

## What carries over
The matching rules in 380 lines; the data format (`;`-separated, 3 levels per side); the P3 data (rounds 1–5). Convention: it reports final PnL before the last tick's fills (see `CLAUDE.md` for how our parity test converts).

## Traps
No conversions (macarons, orchids); `--match-trades` changes results a lot, so state which one a number used.

## Read depth
- **Read:** `README.md:59-97`; `prosperity3bt/parse_submission_logs.py:1-48`; behaviour via our parity test and the Frankfurt runs.
- **Mapped:** `prosperity3bt/runner.py` by `grep`.
- **Unread:** `__main__.py`, `models.py`.

## Cited by
[backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [queue-position-and-fills](../concepts/queue-position-and-fills.md).
