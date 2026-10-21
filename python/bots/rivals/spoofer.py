"""A spoofer (Wang & Wellman's: a large order one tick behind the best, re-posted as it moves):
an adversarial --vs rival.

Run it under --resting: other bots only see its orders when orders rest.

    uv run python -m arena.backtest python/bots/template.py 1 --resting --vs python/bots/rivals/spoofer.py

Each product, each tick, after cancelling its resting orders:
  1. Spoof: a large order OFFSET ticks behind the best on one side, where it rarely trades. It
     is the largest level, so a fair value built on size (the template's wall_mid) moves toward
     it, and a reader of book imbalance sees pressure on that side. OFFSET 1 is Wang & Wellman's
     spoofer; a large OFFSET puts it beyond the walls, like the far 40-lot that moved the
     template's wall_mid on P4 Osmium.
  2. Exploit: it takes any order through its own fair, the mid of the market maker's walls
     (the outermost levels other than its own), and cuts inventory at fair.
The spoof flips side every PERIOD ticks.
"""

import json

from datamodel import Cancel, Order, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}
DEFAULT_LIMIT = 50
SPOOF = 40  # larger than the market maker's walls
OFFSET = 1  # ticks behind the best
PERIOD = 200  # ticks before the spoof changes side


class Trader:
    def run(self, state: TradingState):
        memory = json.loads(state.traderData) if state.traderData else {}
        tick = memory.get("tick", 0)
        result = {}
        for product, depth in state.order_depths.items():
            limit = LIMITS.get(product, DEFAULT_LIMIT)
            orders = [Cancel(o.id) for o in getattr(state, "open_orders", {}).get(product, [])]
            bids = sorted(depth.buy_orders.items(), reverse=True)
            asks = sorted((p, -v) for p, v in depth.sell_orders.items())
            if not bids or not asks:
                result[product] = orders
                continue
            fair = (bids[-1][0] + asks[-1][0]) / 2
            position = state.position.get(product, 0)
            buy_room, sell_room = limit - position, limit + position
            side = "bid" if (tick // PERIOD) % 2 == 0 else "ask"

            # Take through fair, and cut inventory at fair.
            for price, volume in bids:
                if sell_room <= 0 or not (price > fair or (price >= fair and position > 0)):
                    break
                q = min(volume, sell_room)
                orders.append(Order(product, price, -q, ioc=True))
                sell_room -= q
            for price, volume in asks:
                if buy_room <= 0 or not (price < fair or (price <= fair and position < 0)):
                    break
                q = min(volume, buy_room)
                orders.append(Order(product, price, q, ioc=True))
                buy_room -= q

            # Spoof OFFSET ticks behind the best.
            if side == "bid" and buy_room > 0:
                orders.append(Order(product, bids[0][0] - OFFSET, min(SPOOF, buy_room)))
            elif side == "ask" and sell_room > 0:
                orders.append(Order(product, asks[0][0] + OFFSET, -min(SPOOF, sell_room)))
            result[product] = orders
        memory["tick"] = tick + 1
        return result, 0, json.dumps(memory)
