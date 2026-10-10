---
title: DU Trading (Prosperity 4, 10th)
type: source
repo: prosperity4-du-trading
status: partly-read
updated: 2026-10-10
---

# DU Trading (Prosperity 4, 10th globally and 1st in the UK, their claim)

## What it is
A short write-up (`README.md`, 224 lines) and code for some rounds only: `round2.py` (585 lines; also the round 1 logic), `round4.py` (454; rounds 3–4), `round5.py` (1,469). No data, no licence file. Their ranks: R1 5th, R2 3rd, R3 47th, R4 89th, R5 10th. They state they build on [Frankfurt's write-up](prosperity3-frankfurt-hedgehogs.md) (`README.md:20`).

## Layout and code map
README: Osmium `README.md:37` (**wide fills** `README.md:53`), Pepper Root `README.md:63`, round 2 `README.md:75` (decision not to buy extra liquidity, predictable bot trades `README.md:79`), Hydrogel `README.md:98`, options `README.md:103` (deep-OTM 0/1 `README.md:112`), **Marks** `README.md:137-173`, round 5 `README.md:175` (**discretisation** `README.md:182`, pebbles `README.md:199`, snack packs `README.md:209`).

Code:
- Wide-fill thresholds: **98 for Osmium, 120 for Pepper Root** (`round2.py:557`, `round2.py:560`); `trade_osmium` `round2.py:206`, `trade_pepper_root` `round2.py:373`. Pepper Root fair `12000 + 0.1 * floor(t/100 + 0.5)` (`README.md:67`) with a deliberate long bias of +76 of 80 (`README.md:71`).
- Rounds 3–4 (`round4.py`): `HydrogelTrader` `round4.py:219` (fixed mean 9,990, take 10 away), `FruitTrader` `round4.py:240` (fade the underlying and every active voucher together beyond 8 from 5,250), `OtmVoucherTrader` `round4.py:280` (bid 0 on the 6000/6500 strikes), `SpikeTrader` `round4.py:312`.
- **Snap-back rule** (`round5.py:721-770`, `HOLD_TICKS = 3` at `round5.py:178`): "discrete" when the wall mid was a multiple of 100 for three ticks; on a move, take the full opposite position at the far wall and hold 3 ticks. Applied to every product. They say ~660,000 of round 5 came from it (`README.md:197`), payoff +1,000 if it reverts, −160 if not (`README.md:188`).

## What carries over
- The admins' statement that the data generator generated the bots' quotes and then **randomly removed 20% of orders** (`README.md:77`): the origin of the empty book sides.
- The three-line snap-back rule; pebbles sold/bought as a five-leg basket around 49,990/50,010 (`README.md:201`).
- Their classification of the `Mark XX` names (`README.md:141-149`): Mark 67 was the informed buyer in velvetfruit.

## Traps
- **The published code does not match the README on counterparties** *(checked: grep)*: `round4.py` never reads `buyer`/`seller`, so the Mark 67 and Mark 22 logic is not in it. `SpikeTrader._detect_spike_side` (`round4.py:319`) says "levels below wall mid" in its docstring but counts every ask level.
- `round5.py` is one large class; the snap-back and pair logic are interleaved in `trade_combined` (`round5.py:1269`).

## Read depth
- **Read:** the whole README; `round4.py:1-50`, `round4.py:219-280`, `round4.py:312-400`; `round5.py:177-250`, `round5.py:717-810`.
- **Mapped:** `round2.py`, the rest of `round5.py`.
- **Unread:** most of `round5.py` (pairs, combined trader) and the bodies of `round2.py`.

## Cited by
[hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [jumps-and-snap-back](../concepts/jumps-and-snap-back.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [informed-counterparties](../concepts/informed-counterparties.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [options-and-vouchers](../concepts/options-and-vouchers.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [ai-assisted-work](../concepts/ai-assisted-work.md), [contradictions](../contradictions.md).
