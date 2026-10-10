---
title: Ryan Challman (Prosperity 4, 57th)
type: source
repo: prosperity4-ryan-challman
status: partly-read
updated: 2026-10-10
---

# Team Ryan Challman (Prosperity 4, 57th of 18,803, final 713,119, their claim)

## What it is
A write-up (`README.md`, 300 lines) and the shipped traders for rounds 3–5 (`src/round3.py` 576 lines, `src/round4.py` 380, `src/round5.py` 354). No data, no round 1–2 code, no licence file.

## Layout and code map
README: approach `README.md:13`, tools and iteration discipline `README.md:19-27`, rounds `README.md:31-145` (round 4 "validation and rollback" `README.md:73`, `ROBOT_DISHES` `README.md:115`), manual track `README.md:147-256`, **Notes** `README.md:258-282`.

`src/round3.py` is a library of **execution primitives**: `_take_and_make` `src/round3.py:31`, `_asym_trade` `src/round3.py:54`, `_layered_trade` `src/round3.py:77`, `_ladder_step` `src/round3.py:106`, `_smart_make` `src/round3.py:162`, `_throttled` `src/round3.py:202`, and three trader classes dispatched per product by `Trader` (`src/round3.py:557`). `src/round5.py:138` is a compact `Trader`.

## What carries over
- A long-window cumulative mean blended with a short EWMA as fair value, tuned per product; a Black–Scholes-anchored voucher fair lost ~64,000 per strike because the lag they took for a flaw was the alpha (`README.md:266`).
- **Leave-one-day-out validation** (`README.md:75`): the named-trader copy-trade signal did not generalise; switching it off recovered ~$15.8k (`README.md:89-91`).
- Sizing a one-day signal down (`ROBOT_DISHES`, `README.md:115-141`): autocorrelation −0.001, −0.004, **−0.290** on the three days, PnL $389k on one day versus $11k and $4k; weight set to 0.06 on purpose.
- Re-sweep the whole grid after every baseline change (`README.md:27`); single-tick tightenings lost $3k–$34k each (`README.md:270`).
- Their regret (`README.md:280`): they opened the new day's data too early.

## Traps
No limits or data in the repo; the final constants are the end of "hundreds" of ships with no record of the sweeps.

## Read depth
- **Read:** `README.md:1-146` and `README.md:256-300`.
- **Mapped:** `src/round3.py`, `src/round5.py` by function names.
- **Unread:** the manual track `README.md:147-255`, all trader bodies, plots.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md), [informed-counterparties](../concepts/informed-counterparties.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md), [options-and-vouchers](../concepts/options-and-vouchers.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [ai-assisted-work](../concepts/ai-assisted-work.md), [contradictions](../contradictions.md).
