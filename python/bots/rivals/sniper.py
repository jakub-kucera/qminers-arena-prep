"""A sniper (Harris's timing option, p. 320): an adversarial --vs rival that picks off stale quotes.

Run it under --resting: other bots only see its orders when orders rest, and stale quotes exist
only when orders outlive their tick.

    uv run python -m arena.backtest python/bots/template.py 1 --resting --vs python/bots/rivals/sniper.py

It never rests an order. Each product, each tick, it takes every visible order priced at least
EDGE through its fair, the mid of the outermost levels (the market maker's walls, which have
already moved when a resting quote goes stale), and cuts its inventory at fair.
"""

from datamodel import Cancel, Order, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}
DEFAULT_LIMIT = 50
EDGE = 1


class Trader:
    def run(self, state: TradingState):
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
            for price, volume in bids:
                if sell_room <= 0 or not (price >= fair + EDGE or (price >= fair and position > 0)):
                    break
                q = min(volume, sell_room if price >= fair + EDGE else min(sell_room, position))
                orders.append(Order(product, price, -q, ioc=True))
                sell_room -= q
            for price, volume in asks:
                if buy_room <= 0 or not (price <= fair - EDGE or (price <= fair and position < 0)):
                    break
                q = min(volume, buy_room if price <= fair - EDGE else min(buy_room, -position))
                orders.append(Order(product, price, q, ioc=True))
                buy_room -= q
            result[product] = orders
        return result, 0, ""
