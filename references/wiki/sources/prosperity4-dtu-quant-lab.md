---
title: DTU Quant Lab (Prosperity 4, 28th)
type: source
repo: prosperity4-dtu-quant-lab
status: partly-read
updated: 2026-10-13
---

# DTU Quant Lab (Prosperity 4, 28th of 18,803, first-time team, their claim)

## What it is
A team repo with traders for all five rounds, data, and two documents that matter more than the code: `docs/literature_review.md` (94 lines: which references shipped, which were killed and why) and `docs/journey.md` (49 lines). MIT licence (`LICENSE`, checked). Traders: R1 456 lines, R2 525, R3 2,074, R4 2,277, R5 2,998. "Capsule" = the historical data handed out for a round, "live" = the round itself.

## Layout and code map
- `README.md`: campaign table `README.md:47`, rounds `README.md:81-191`, the round 5 PnL attribution `README.md:193-202`, methodology and the worst-day rule `README.md:254-264`, FAQ `README.md:325`.
- R1/R2 (`round_1/algorithmic/trader.py`): `trade_osmium` `round_1/algorithmic/trader.py:169`, `trade_pepper` `round_1/algorithmic/trader.py:330`, plain functions and a `PARAMS` dict.
- R3/R4 (R4 is R3 plus sweep-confirmed constants): `LIMITS` `round_4/algorithmic/trader.py:244`; Hydrogel dispatches between Frankfurt's pegged quoter, an Avellaneda–Stoikov quoter and a trend handler by a **regime detector** (`PARAMS_HP_REGIME` `round_4/algorithmic/trader.py:287`: PINNED / TRENDING / NOISY from the rolling σ of mid changes, drift detector EMA 50 vs 500, end-of-day flatten); `CounterpartyTracker` `round_4/algorithmic/trader.py:149`.
- **Option helpers in plain `math` + `NormalDist`**: `bs_call_price` `round_3/algorithmic/trader.py:416`, delta, vega, `implied_vol` (`round_3/algorithmic/trader.py:416-466`), `_fit_smile` `round_3/algorithmic/trader.py:1464` (a 3×3 normal-equation solve: a parabola of implied vol in moneyness), `voucher_mr_overlay` `round_3/algorithmic/trader.py:1725`, `_vev_5300_gate_check` `round_3/algorithmic/trader.py:1796`.
- R5 (`round_5/algorithmic/trader.py`): `ClusterStrategy` ABC `round_5/algorithmic/trader.py:510`, ten cluster classes (`PebblesBasketArb` `round_5/algorithmic/trader.py:678` … `SleepPodStrategy` `round_5/algorithmic/trader.py:2617`), `AStyleMMStrategy` `round_5/algorithmic/trader.py:555` (plain wall-mid market making with `skew = position / limit * skew_at_limit`), master `Trader` `round_5/algorithmic/trader.py:2833` with variant `HYBRID_VARIANT = "H5"` that replaces the elaborate strategies by the plain market maker on UV_VISOR, TRANSLATOR and OXYGEN_SHAKE (live evidence in the comment at `round_5/algorithmic/trader.py:560-562`).
- Safety nets in the master trader: `_clip_orders` `round_5/algorithmic/trader.py:2908`, `CLUSTER_TICK_VOL_CAP = 200` `round_5/algorithmic/trader.py:2829`, versioned `traderData` (`round_5/algorithmic/trader.py:2885-2895`), a `try/except` per cluster. `GLOBAL_DRAWDOWN_HALT` and `HALT_FLATTEN_TICKS` (`round_5/algorithmic/trader.py:2827`, `round_5/algorithmic/trader.py:2831`) are defined and **never used** *(checked: grep)*.

## What carries over
- Best stdlib-only option helpers in the clones; a master-trader skeleton with per-cluster state; the regime-detector idea.
- Their claims: worst-day rule killed ~80% of ideas (`README.md:260`, `README.md:334`); `OXYGEN_SHAKE_CHOCOLATE` made +587,831 of +702,835 in round 5 with plain inside-the-spread market making (`README.md:191-202`); pebbles sum to `[49982, 50016]` (`docs/journey.md:32`); Hydrogel drifted 70 ticks in one session in R3 and the fixed-anchor quoter kept buying (`docs/journey.md:16`).
- **The capsule misled them**: Hydrogel's handed-out days were ~99% pinned and the live day 100% noisy (`round_4/algorithmic/trader.py:261-296`).

## Checked in our engine (2026-10-13)
`round_1/algorithmic/trader.py` and `round_2/algorithmic/trader.py` on the P4 round 1 and 2 data. Both engines give identical PnL per product per day: ours (`uv run python -m arena.backtest <file> <round> --data p4`, default per-tick mode) and the P4 backtester (`prosperity4btest cli <file> <round> --limit ASH_COATED_OSMIUM:80 --limit INTARIAN_PEPPER_ROOT:80`; see [prosperity4-backtester](prosperity4-backtester.md)).

| Trader | Data | Days (−2/−1/0 or −1/0/1) | Osmium per day | Pepper Root per day |
|---|---|---|---|---|
| round 1 | Round 1 | 65,540 / 67,565 / 64,963 | 15,344–18,010 | 49,555–49,724 |
| round 1 | Round 2 | 68,732 / 66,663 / 68,240 | 17,078–19,156 | 49,526–49,585 |
| round 2 | Round 1 | 95,537 / 97,043 / 96,235 | 15,860–17,676 | 79,367–79,677 |
| round 2 | Round 2 | 98,306 / 98,650 / 97,394 | 18,025–19,030 | 79,369–79,620 |

- **Claims tested:** live algorithmic PnL of +67,585 in round 1 and +84,889 in round 2 (`README.md:51-52`). The round 1 trader's backtest days are within 4% of its live result. The round 2 trader's are 12–16% above its live result; the live day is not in our data, and the trader has no `bid()`, so no market-access fee explains it.
- **The round 1 trader caps both products at 50** (`round_1/algorithmic/trader.py:89`, `round_1/algorithmic/trader.py:92`), below the real limit of 80. Pepper Root's PnL is the drift on a held long of 50, about 1,000 a day per lot.
- **The round 2 trader sends more than its room on Osmium:** 124–347 ticks a day have every Osmium order cancelled for a possible limit breach, in both engines.
- **Rounds 3–5** (the round 3, 4 and 5 traders on their own rounds, 3-day totals): 135,842, 116,090 and 501,498. Their live single days were +3,686, +25,351 and +702,835 (`README.md:53-55`), so these backtests on the development days say little about live results. The comparison by product is in `IDEAS.md`, "Benchmark".

## Traps
- `_clip_orders` is stricter than the engine's limit rule and dropped orders the engine would accept; they bypass it for the plain market maker (`round_5/algorithmic/trader.py:2918-2921`).
- Headline killed-idea numbers (−16,593 for Avellaneda–Stoikov on Osmium, −26,497 for Ho–Stoll) are their own backtests, not reproduced.
- ~110 lines of visualizer `Logger` boilerplate in every file (`round_5/algorithmic/trader.py:18`). `round_5/algorithmic/data/` is 110 MB of the 212 MB.

## Read depth
- **Read:** `README.md:47-349`; `docs/journey.md`; `docs/literature_review.md`; R4 trader lines 128–365; R5 trader lines 505–680 and 2820–2999.
- **Mapped (grep only):** all five traders.
- **Unread:** R1–R3 bodies, the cluster strategy bodies, `tools/dashboard.py`, round and manual READMEs other than R4/R5 algorithmic.

## Cited by
[market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [options-and-vouchers](../concepts/options-and-vouchers.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [informed-counterparties](../concepts/informed-counterparties.md), [many-products-architecture](../concepts/many-products-architecture.md), [validation-and-overfitting](../concepts/validation-and-overfitting.md), [jumps-and-snap-back](../concepts/jumps-and-snap-back.md), [contradictions](../contradictions.md).
