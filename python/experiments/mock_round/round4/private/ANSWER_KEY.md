# The Varde Exchange: answer key (rehearsal 4, 2026-11-03)

Made to test `experiments.day.calibrate` against an exchange that is **not** `arena.engine` (the audit's round 8, R1
and its "Aim"): `private/portal.py` matches and scores in its own code, standard library only, importing nothing
from the repo.

## Products (private/generate.sh; arena.sim presets, renamed by private/disguise.py)
| name | from | what it is | limit |
|---|---|---|---|
| LUMEN | KELP_FLOW, sd 0.15, walls 4 apart | a slow random walk whose takers buy 35% of the time, larger than the sells | 40 |
| QUILL | HYDROGEL_PACK, reversion 0.002, sd 1.4, walls 12 apart | back to one level (half-life ~350 steps), the same on the hidden sessions | 60 |
| SORREL | SQUID_INK, sd 0.9, momentum takers 0.05 | a fast walk with momentum | 30 |

Prices: a raw tick of 1 is 5 cents; results in euros. Sessions of 5,000 steps: seeds 41117, 41229, 41383 public,
58801, 58933 hidden.

## The exchange's rules
Stated in `public/rules.md`: orders rest; a new order trades with the shown book first at the book's prices, then
the step's prints fill resting orders at the order's price, best price then oldest first, a sell print filling bids
at or above its price; the per-product limit check rejects all of a step's new orders for the product; 10 actions a
step; 50 ms a call; fees of 0.1 cent a lot and 0.5 cent an order; cancels before new orders.

**Not stated, and outside what `EngineConfig` expresses:**
1. Only half of each print, rounded down, is there for resting orders (`PRINT_SHARE` 0.5): the rest went to
   orders the book doesn't show. `--fill-ratio 0.5` is near it but is a random draw on all liquidity.
2. Open positions are valued at the VWAP of the product's last 100 prints of the session (`SETTLE_PRINTS`), not the
   mid, the touch or the last price.
3. The fee per order placed (stated) has no engine field: `fee` is per lot.

So no setting in calibrate's grid reproduces this portal exactly. The test is whether it says so (refusing above
5% on the worst figure) or fits within it with a setting whose errors it names, and what the session does next.

The example bot (`public/example_bot.py`) on the hidden sessions: +80.10 euros.
