"""A quote-matching trapper (Harris, Trading and Exchanges, p. 263): an adversarial --vs rival.

Run it under --resting: other bots only see its orders when orders rest.

    uv run python -m arena.backtest bots/template.py 1 --resting --vs bots/rivals/trapper.py

Each product, each tick, after cancelling its resting orders:
  1. Bait: a large order one tick inside the best on one side (never through its fair), so it is
     the best quote and the largest level. A quote matcher steps one tick in front of it, and a
     fair value built on size (the template's wall_mid) moves toward it.
  2. Spring: if someone quotes one tick in front of the bait, sell into that bid (or buy that
     ask) at once, and drop the bait for COOLDOWN ticks: the matcher is left holding a position
     with no large order behind it to sell back to.
  3. Take anything through its own fair, the mid of the outermost levels (the market maker's
     walls, which inside quotes don't move), and cut inventory at fair.
The bait side flips every PERIOD ticks, and leans to the side that unwinds its position.
"""

import json
import math

from datamodel import Cancel, Order, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}
DEFAULT_LIMIT = 50
BAIT = 40  # the bait's size: larger than the market maker's walls
PERIOD = 200  # ticks before the bait changes side
COOLDOWN = 20  # ticks without bait after springing the trap


class Trader:
    def run(self, state: TradingState):
        memory = json.loads(state.traderData) if state.traderData else {}
        tick = memory.get("tick", 0)
        cooldown = memory.get("cooldown", {})
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
            bait_side = "bid" if (tick // PERIOD) % 2 == 0 else "ask"
            if position > limit // 2:
                bait_side = "ask"
            elif position < -limit // 2:
                bait_side = "bid"
            last_bait = memory.get("bait", {}).get(product)

            # Spring: someone stepped in front of last tick's bait.
            sprung = False
            if last_bait:
                side, price = last_bait
                if side == "bid" and bids[0][0] == price + 1 and sell_room > 0:
                    q = min(bids[0][1], sell_room)
                    orders.append(Order(product, bids[0][0], -q, ioc=True))
                    sell_room -= q
                    sprung = True
                elif side == "ask" and asks[0][0] == price - 1 and buy_room > 0:
                    q = min(asks[0][1], buy_room)
                    orders.append(Order(product, asks[0][0], q, ioc=True))
                    buy_room -= q
                    sprung = True
            if sprung:
                cooldown[product] = COOLDOWN

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

            # Bait.
            bait = None
            if cooldown.get(product, 0) > 0:
                cooldown[product] -= 1
            elif bait_side == "bid" and buy_room > 0:
                price = min(bids[0][0] + 1, math.floor(fair - 0.5))
                if price < asks[0][0]:
                    orders.append(Order(product, price, min(BAIT, buy_room)))
                    bait = ("bid", price)
            elif bait_side == "ask" and sell_room > 0:
                price = max(asks[0][0] - 1, math.ceil(fair + 0.5))
                if price > bids[0][0]:
                    orders.append(Order(product, price, -min(BAIT, sell_room)))
                    bait = ("ask", price)
            memory.setdefault("bait", {})[product] = bait
            result[product] = orders
        memory.update(tick=tick + 1, cooldown=cooldown)
        return result, 0, json.dumps(memory)
