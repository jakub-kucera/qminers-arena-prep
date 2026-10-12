---
title: Une Baguette Fromage (Prosperity 4, 4th)
type: source
repo: prosperity4-baguette-fromage
status: partly-read
updated: 2026-10-13
---

# Une Baguette Fromage (Prosperity 4, 4th of 18,803, their claim)

## What it is
The most detailed write-up of the newest edition: `README.md` (1,599 lines), `Strategies/Phase1.py` (522 lines, rounds 1–2), `Strategies/Phase2_Options.py` (928, rounds 3–4), `Strategies/Phase2_Final.py` (1,664, round 5), `Figures/`, `Scores/`. No licence file. Rounds 1–2 were a qualifier and the products changed completely for rounds 3–5. Their cumulative rank: R1 8th, R2 4th, R3 3rd, R4 11th, R5 4th.

## Layout and code map
README: tools `README.md:115`, **backtester limits** `README.md:232`, **wall mid** `README.md:257`, Osmium `README.md:316` (**empty book** `README.md:350`), Pepper Root `README.md:398` (DP model `README.md:433`), extra market access `README.md:500`, **recurring takers** `README.md:557`, Hydrogel `README.md:674`, Velvetfruit `README.md:709`, options `README.md:763`, Monte Carlo thresholds `README.md:806`, Marks `README.md:842`, **round 5** `README.md:854` (what survived `README.md:903`, 100-jump `README.md:1000`, Pebbles `README.md:1062`), manual rounds `README.md:1105-1485`, **FAQ** `README.md:1486` (AI use `README.md:1504`).

Round 1 (`Strategies/Phase1.py`):
- Osmium `Strategies/Phase1.py:368`: fixed 10,000, reservation price `10000 - position/12` (`Strategies/Phase1.py:240`), take beyond `reservation ± 1`, penny otherwise, and if the improved quote would cross the reservation quote **98 from the last wall mid** (`Strategies/Phase1.py:423-428`).
- Pepper Root `Strategies/Phase1.py:441`: `fv = start_fv + 0.001 * timestamp`, thresholds from a dynamic-programming table indexed by position; unit-by-unit taking (`Strategies/Phase1.py:332`).
- `bid()` (`Strategies/Phase1.py:254`) is the round 2 blind "extra market access" bid: a new method of the Prosperity 4 `Trader`.
- **Wall mid here = mid of the highest-volume bid and ask** (`Strategies/Phase1.py:274-291`).

Round 5 (`Strategies/Phase2_Final.py`): one `ProductTrader` per listing (`Strategies/Phase2_Final.py:282`); strategies add **intents** (`Strategies/Phase2_Final.py:275`, `Strategies/Phase2_Final.py:514`) that `get_orders` (`Strategies/Phase2_Final.py:518`) averages by weight and executes with `orders_to_reach_target` (`Strategies/Phase2_Final.py:454`); the default for any product is `mm_to_the_max` (`Strategies/Phase2_Final.py:540`): best bid +1 and best ask −1 with all the room. Classes: `EtfTrader` (`Strategies/Phase2_Final.py:551`), `JumpTrader` (`Strategies/Phase2_Final.py:668`, constants `Strategies/Phase2_Final.py:672-677`), `PebblesTrader` (`Strategies/Phase2_Final.py:883`), `_WallMidMMTrader` (`Strategies/Phase2_Final.py:1343`: reservation `wall_mid - 0.4 * position`), `UVTurnPointOverlay` (`Strategies/Phase2_Final.py:1429`), `Trader.run` (`Strategies/Phase2_Final.py:1605`). `Strategies/Phase2_Options.py`: Hydrogel `Strategies/Phase2_Options.py:332`, Black–Scholes helpers `Strategies/Phase2_Options.py:407-504`, `option_regime_orders` `Strategies/Phase2_Options.py:542`, `informed_signal` `Strategies/Phase2_Options.py:189` (not shipped).

## What carries over
Position limits (confirmed by [DTU](prosperity4-dtu-quant-lab.md)): Osmium 80 (`README.md:314`), Hydrogel 200, Velvetfruit 200, vouchers 300, round 5 products 10. Findings (their claims): hidden takers on empty sides ~8% of the time (`README.md:354`); takers repeat day to day (`README.md:557-668`); Velvetfruit as an Ornstein–Uhlenbeck process, buy below 5232 and sell above 5268 (`README.md:740-759`); in round 5 in-sample scanners found "unlimited alpha" and fitting on two days and testing on the third wiped it out (`README.md:885-901`).

## Checked in our engine (2026-10-13)
`Strategies/Phase1.py` on the P4 round 1 and 2 data, run with `uv run --with jsonpickle` (the file imports jsonpickle). Both engines give identical PnL per product per day: ours (`uv run python -m arena.backtest <file> <round> --data p4`, default per-tick mode) and the P4 backtester (`prosperity4btest cli <file> <round> --limit ASH_COATED_OSMIUM:80 --limit INTARIAN_PEPPER_ROOT:80`; see [prosperity4-backtester](prosperity4-backtester.md)).

| Data | Day | Osmium | Pepper Root | Total |
|---|---|---|---|---|
| Round 1 | −2 | 19,087 | 83,369 | 102,456 |
| Round 1 | −1 | 19,953 | 82,834 | 102,787 |
| Round 1 | 0 | 18,788 | 83,132 | 101,920 |
| Round 2 | −1 | 21,184 | 83,058 | 104,242 |
| Round 2 | 0 | 20,712 | 83,625 | 104,337 |
| Round 2 | 1 | 21,357 | 84,268 | 105,624 |

- **Claim tested:** "roughly 18.6k expected PnL for OSMIUM" a day from quoting about 100 away on an empty side (`README.md:365`). Our Osmium totals are 18.8–21.4k a day for their whole Osmium strategy, so the size is consistent; the empty-side part alone wasn't separated.
- **Their round 2 caveat** that the hard-coded 10,000 pinned Osmium at the limit (`README.md:527-539`) doesn't show on the round 2 data: Osmium sits at the limit on 0–5% of ticks. It happened on the live day, which we don't have.
- Our engine cancels a few ticks' Osmium orders for breaching the limit (1–28 ticks a day), as Prosperity would.
- `bid()` returns −10,000,000 (`Strategies/Phase1.py:254-255`), which the backtester reads as no bid for extra market access.

## Traps
- Imports `prosperity3bt.datamodel` with a fallback and `Phase1.py` uses `jsonpickle`: rewrite, don't paste (no licence).
- `POS_LIMIT = 10` is global in `Strategies/Phase2_Final.py:12`: right for round 5 only.
- Their own caveat: hard-coding Osmium at 10,000 left them pinned at max inventory in round 2 when the anchor drifted (`README.md:527-539`).

## Read depth
- **Read:** `README.md:232-1100` and `README.md:1486-1599`; `Strategies/Phase1.py:236-523`; `Strategies/Phase2_Final.py` lines 1–60, 272–560, 668–760, 1333–1430, 1600–1664.
- **Mapped:** `Strategies/Phase2_Options.py`, the rest of `Strategies/Phase2_Final.py`.
- **Unread:** `README.md:1-231` (tools, dashboard), the manual challenge `README.md:1105-1485`, bodies of the pebbles, ETF and UV classes.

## Cited by
[fair-value-and-wall-mid](../concepts/fair-value-and-wall-mid.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [jumps-and-snap-back](../concepts/jumps-and-snap-back.md), [many-products-architecture](../concepts/many-products-architecture.md), [options-and-vouchers](../concepts/options-and-vouchers.md), [validation-and-overfitting](../concepts/validation-and-overfitting.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [ai-assisted-work](../concepts/ai-assisted-work.md), [contradictions](../contradictions.md).
