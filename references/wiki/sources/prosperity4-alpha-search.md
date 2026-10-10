---
title: Alpha Search Team (Prosperity 4, README only)
type: source
repo: prosperity4-alpha-search
status: partly-read
updated: 2026-10-10
---

# Alpha Search Team (Prosperity 4; "4th in round 4", 23rd and 27th in algorithmic rounds 3 and 2, their claim)

## What it is
`README.md` (638 lines) and 8 pictures. **No code** (`README.md:630`). No licence file.

## Layout and code map
Tooling and the PnL decomposition `README.md:41-44`; Osmium `README.md:47`; Pepper Root `README.md:63` (three phases); rounds 3–4 `README.md:90` (options `README.md:101`, informed traders `README.md:113`); **round 5** `README.md:119-179`; manual challenges `README.md:181-628`.

## What carries over
- **PnL decomposition** (`README.md:44`): directional carry `position × Δmid` plus market-making capture `Σ Δq × (mid at fill − fill price)`, summing exactly to PnL.
- **Basket discovery is a multiple-testing problem** (`README.md:124-141`): accepting a basket that passes in any one of three folds has ~14% false positives under no edge; weights restricted to small integers in [−3, 3] inside one product family; baskets ranked by `(σ / cost) × (1 / half-life)` instead of by p-value.
- **Hard product ownership** between strategies (`README.md:174`).
- Check every lead-lag finding with a second implementation (`README.md:162`); microchip lead-lag at lags 50/100/150/200 survived.
- Pepper Root (`README.md:63-81`): accumulate to the limit without overpaying, mean-revert around the future mid, quote below the best ask near the end; they missed the empty-side wide fill (`README.md:81`).
- Informed traders (`README.md:113-117`): only Mark 67 had an edge, too small after costs.

## Traps
Everything is their claim; there is no code to check it against.

## Read depth
- **Read:** `README.md:1-185`.
- **Unread:** the manual challenges `README.md:181-638`, pictures.

## Cited by
[baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [validation-and-overfitting](../concepts/validation-and-overfitting.md), [many-products-architecture](../concepts/many-products-architecture.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [informed-counterparties](../concepts/informed-counterparties.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [options-and-vouchers](../concepts/options-and-vouchers.md).
