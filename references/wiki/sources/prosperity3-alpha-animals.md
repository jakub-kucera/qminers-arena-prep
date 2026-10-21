---
title: Alpha Animals (Prosperity 3, 9th)
type: source
repo: prosperity3-alpha-animals
status: partly-read
updated: 2026-10-10
---

# Alpha Animals (Prosperity 3, 9th of 13,500+, 2nd after rounds 3 and 4, their claim)

## What it is
`README.md` (202 lines), one `trader.py` (1,810 lines) for all rounds, `datamodel.py`, `data/round-{1..5}-island-data-bottle/` and `python/notebooks/` (`baskets_and_spreads`, `smile`, `kalman`, `counterparty_edge`, `round5_analysis`, `conversions.py`). No licence file.

## Layout and code map
`trader.py`: `Trader` `trader.py:116`; market-maker fair value `trader.py:267`; `product_orders` `trader.py:315`; Squid Ink spike mean reversion `trader.py:456`; baskets `trader.py:542-692`; hand-written Black–Scholes and implied volatility `trader.py:712-771`; `find_arbitrage_opportunities` `trader.py:803`; macarons `trader.py:1148-1460` (regime from the sunlight index `trader.py:1801`); `process_insider_trades` `trader.py:1461`; `copy_olivia_trades` `trader.py:1488`; `run` `trader.py:1547`.

## What carries over
- Their luck is documented: a round 2 bug (orders over the limit, so the engine cancelled them) killed the basket strategy (`README.md:119`), and in round 3 a bug left them short the underlying at the limit all day, which paid (`README.md:135`). The README says so; treat the rank as partly luck.
- The backtester did not support conversions and they lost money on conversion costs (`README.md:88`).
- `python/notebooks/counterparty_edge.ipynb` tags a trade informed when it happens at a rolling-window price extreme (functions `add_price_extremes`, `tag_informed_trades`, `find_informed_traders`, window 50, threshold 0.001) and flags names above the 95th percentile.

## Traps
- **State is split between `self` and `traderData`**: `Trader.__init__` (`trader.py:117-140`) holds price lists, `insider_regimes`, `insider_last_trades` and more on the instance, while `run` (`trader.py:1547`) restores only part of it from `traderData`. If the Arena does not keep the object between calls, state on `self` is lost.
- The whole of `run` is one `try:` (`trader.py:1548`).
- Imports `jsonpickle`; 197 MB, nearly all data duplicated in the jmerle backtester.

## Read depth
- **Read:** `README.md:68-202`; `trader.py:116-140` and `trader.py:1547-1580`; the function names of the counterparty notebook.
- **Mapped:** the rest of `trader.py` by `grep`.
- **Unread:** the other notebooks and the strategy bodies.

## Cited by
[informed-counterparties](../concepts/informed-counterparties.md), [options-and-vouchers](../concepts/options-and-vouchers.md), [cross-market-and-conversions](../concepts/cross-market-and-conversions.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [validation-and-overfitting](../concepts/validation-and-overfitting.md).
