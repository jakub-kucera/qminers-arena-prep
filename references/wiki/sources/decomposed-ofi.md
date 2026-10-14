---
title: Sitaru, Calinescu & Cucuringu, "Order flow decomposition for price impact analysis in equity limit order books" (2023)
type: source
repo: literature_md/decomposed-ofi
status: partly-read
updated: 2026-10-14
---

# Sitaru, Calinescu & Cucuringu, "Order flow decomposition for price impact analysis in equity limit order books" (ICAIF 2023)

## What it is
Order-flow imbalance (OFI, Cont, Kukanov & Stoikov) split by event type: the imbalance from **adds**, from **cancels** and from **trades**, computed from market-by-order data for 100 Nasdaq stocks over three years (LOBSTER, `decomposed-ofi.md:11` (p. 1), `decomposed-ofi.md:122` (p. 6)), and regressed on the same interval's and the next intervals' returns. The user's copy is a 21-page extended version of the 9-page ICAIF paper, same authors and title.

## Main results
- **Same interval: no gain.** The decomposed OFI explains the contemporaneous move on par with the standard OFI (`decomposed-ofi.md:33` (p. 2)).
- **Next intervals: a gain.** In forecasting, models with the decomposed OFI earn "significantly higher economical gains (even five times higher than previous studies, in terms of PnL per dollar traded)" (`decomposed-ofi.md:33` (p. 2); *their claim*). Lasso selects the add-order imbalance most often, then cancels, then trades.

## Assumptions against the Arena
- **Event types need market-by-order data.** From snapshots we see trades (`Tick.trades`) and the change in each level; the rest of a level's change is net adds minus cancels at that price, not the two separately *(inferred)*. So only a trade OFI and a net "book" OFI are computable here.
- Equities at seconds-to-minutes horizons.

## In our notation
OFI from consecutive `Book` snapshots as in [price-impact-of-book-events](price-impact-of-book-events.md); the trade part from `Tick.trades`.

## Traps
- The extended version's section numbers differ from the ICAIF paper's.

## Read depth
- **Read:** the abstract, introduction and contributions, section 4's definitions.
- **Skimmed:** sections 5–6 (the regressions and trading results).

## Cited by
[book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md), [price-impact](../concepts/price-impact.md).
