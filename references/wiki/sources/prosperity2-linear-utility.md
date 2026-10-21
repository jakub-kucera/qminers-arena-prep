---
title: Linear Utility (Prosperity 2, 2nd)
type: source
repo: prosperity2-linear-utility
status: partly-read
updated: 2026-10-10
---

# Linear Utility (Prosperity 2, 2nd of 9,000+, their claim)

## What it is
A full dump of one team's campaign: `README.md` (296 lines) and one folder per round with their own backtester copy, research notebooks and **every version** of the trader. Final version = highest number; only round 1 is named in the README (`round1/round_1_v6.py`). By file name (my reading, not their statement): round 2 `round2/round_2_v3.py`, round 3 `round3/round3_v2.py`, round 4 `round4/round4_v4_roses.py`, round 5 `round5/round5_v1_r5_strings.py`. `dashboard/` is their Dash app. 419 MB, mostly data and logs. No licence file.

## Layout and code map
README: tools `README.md:72`, amethysts `README.md:93`, starfruit `README.md:98`, orchids `README.md:118`, baskets `README.md:139`, coconut coupon `README.md:162`, round 5 `README.md:172-275`.

`round1/round_1_v6.py` (411 lines) is the ancestor of our `python/bots/template.py`: `PARAMS` `round1/round_1_v6.py:14` (`take_width`, `clear_width`, `disregard_edge`, `join_edge`, `default_edge`, `soft_position_limit`, `adverse_volume`, `reversion_beta`), `take_best_orders` `round1/round_1_v6.py:46`, `clear_position_order` `round1/round_1_v6.py:114`, `make_orders` `round1/round_1_v6.py:250` (join a level within `join_edge` of fair, otherwise penny, ignore levels within `disregard_edge`), `market_make` `round1/round_1_v6.py:95`. **Starfruit fair value** (`round1/round_1_v6.py:160`): best ask and bid among levels of **size ≥ 15** (their market-maker bot), averaged, plus `fair = mm_mid + mm_mid * (-0.229 * last_return)`. Position limit 20.

## What carries over
- The website marks PnL to the market maker's mid, found by buying one lot and holding it (`README.md:109`).
- Clearing inventory with zero-EV trades added about 3% (`README.md:96`).
- Basket spread as a z-score with a hard-coded mean and a short rolling σ (`README.md:139-160`); live slippage against the backtest was large (111k) and the teams ahead had over-fitted more.
- Cut variance when ahead: a partial delta hedge on the coconut coupon cost them when they were already 2nd (`README.md:162-170`).
- Orchids arbitrage (a large local taker plus the foreign market's implied ask); a Discord leak made everyone find it and they fell to 17th (`README.md:118-137`).
- Round 5: the previous year's public data predicted this year's prices, and a dynamic program produced a perfect trade string (`README.md:172-275`). Not reusable here, but the lesson is to check whether organisers reuse generators or data.

## Traps
- Many near-duplicate versions per round with no changelog.
- The final traders import `jsonpickle` and `numpy` *(checked: rounds 1, 2, 3, 5)*; the Arena's allowed libraries are unknown.
- Their backtester is their own re-implementation, not jmerle's.

## Read depth
- **Read:** `README.md:54-296`; `round1/round_1_v6.py:9-310`; the imports of the final traders.
- **Mapped:** file lists per round.
- **Unread:** rounds 2–5 code, notebooks, dashboard, the dynamic-programming code beyond the README listing.

## Cited by
[market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [fair-value-and-wall-mid](../concepts/fair-value-and-wall-mid.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md), [cross-market-and-conversions](../concepts/cross-market-and-conversions.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [options-and-vouchers](../concepts/options-and-vouchers.md).
