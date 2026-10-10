---
title: Frankfurt Hedgehogs (Prosperity 3, 2nd)
type: source
repo: prosperity3-frankfurt-hedgehogs
status: partly-read
updated: 2026-10-10
---

# Frankfurt Hedgehogs (Prosperity 3, 2nd of 12,000+, their claim)

## What it is
Two files: a long write-up (`README.md`, 992 lines) and their final trader `FrankfurtHedgehogs_polished.py` (925 lines, uses `numpy`). No licence file. Origin of the "wall mid" idea that Baguette Fromage and DU Trading both build on.

## Layout and code map
README: dashboard `README.md:86-163`, Resin `README.md:169`, Kelp `README.md:206`, Squid Ink `README.md:266`, baskets `README.md:327` (final `README.md:374`), options `README.md:428` (IV scalping `README.md:436`, mean reversion `README.md:571`, final `README.md:603`), macarons `README.md:622`, trader IDs `README.md:751`, manual-round maths `README.md:786-876`, **FAQ** `README.md:877-992` (wall mid `README.md:879`, backtesting `README.md:889`, hardcoding `README.md:967`).

Code (`FrankfurtHedgehogs_polished.py`):

| Lines | What |
|---|---|
| `101-270` | `ProductTrader` base: `get_walls` (`FrankfurtHedgehogs_polished.py:153`) takes `bid_wall = min(bid prices)` and `ask_wall = max(ask prices)`, the **outermost** levels; `bid()`/`ask()` clamp to the room under the limit (`FrankfurtHedgehogs_polished.py:199-211`); `check_for_informed` (`FrankfurtHedgehogs_polished.py:225`) keeps the last informed buy/sell timestamps in `traderData` |
| `275-331` | `StaticTrader` (Resin = 10,000): take at `wall_mid ± 1`, flatten at `wall_mid`, quote `bid_wall + 1` / `ask_wall - 1` and overbid inside the wall (`FrankfurtHedgehogs_polished.py:306-324`). Full room on both sides, no skew |
| `335-377` | `DynamicTrader` (Kelp): same at the wall; cross to the far wall up to ±40 for 500 timestamps after an informed trade |
| `382-405` | `InkTrader`: go to ±limit with the informed trader, no market making |
| `409-556` | `EtfTrader`: basket wall mid minus weighted constituents minus a running mean premium (initial 5 and 53); thresholds 80 and 50, shifted ±90 when informed; hedge at 0.5 |
| `559-771` | `OptionTrader`: Black–Scholes with a quadratic smile in `ln(K/S)/√TTE` (`FrankfurtHedgehogs_polished.py:585`), EMA window 20, IV scalping when the mean absolute deviation ≥ 0.7, mean reversion on the 9500 voucher and the underlying |
| `775-878` | `CommodityTrader` (Macarons): conversion arbitrage, 0.58 of the edge as the cut-off |
| `881-925` | `Trader.run`: product → trader dict, each in `try/except: pass`; one JSON `print` per tick |

## What carries over
- Resin and Kelp are the take / clear / make pattern around `wall_mid` that `bots/template.py` already has.
- Keep a running mean in `traderData` as `[mean, n]` (`FrankfurtHedgehogs_polished.py:444-450`).
- Their reading of the simulator: orders live one tick, the order of play within a tick (`README.md:173`), PnL marked to the market maker's mid (`README.md:882`).

## Traps
- **The published file is not what they ran** *(checked: ran it through our engine)*. `FrankfurtHedgehogs_polished.py:435` calls `list.sort()` and iterates the `None` it returns, so the basket spread is always `None` and the ETF code never trades; `FrankfurtHedgehogs_polished.py:670-678` read `self.new_switch_mean` and `self.vegas`, which are never assigned, so the option class raises and the bare `except` swallows it. On Prosperity 3 round 2 day 0 our engine gave Resin 40,582 and Kelp 5,320 (README claims about 39,000 and 5,000 per round) and no basket fills; round 3 day 0 gave no voucher fills.
- Squid Ink needs trader names, which the Prosperity 3 data has only in round 5 *(checked)*.
- Use the README for parameters and ideas, the code only for structure.

## Read depth
- **Read:** all the code; `README.md:60-340` and `README.md:877-992`.
- **Mapped:** the README table of contents.
- **Unread:** `README.md:325-876` (baskets, options, macarons, trader-ID narrative and the manual challenge).

## Cited by
[fair-value-and-wall-mid](../concepts/fair-value-and-wall-mid.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [informed-counterparties](../concepts/informed-counterparties.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [options-and-vouchers](../concepts/options-and-vouchers.md), [cross-market-and-conversions](../concepts/cross-market-and-conversions.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [contradictions](../contradictions.md).
