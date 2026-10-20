"""A plain Kelp market maker, the Python half of experiments/rust_bench.py (src/main.rs is the other).

Fair is the wall mid (the largest level each side, ties nearer the touch). It takes every level at
least `take_edge` through fair, then quotes the rest of its room one tick inside the best, but no
closer to fair than `make_edge`. Keep it equal to `strategy` in src/main.rs: the benchmark checks
that both make the same PnL and fills on every cell.
"""

import math

from datamodel import Order

PRODUCT, LIMIT = "KELP", 50
PARAMS = {PRODUCT: {"make_edge": 1, "take_edge": 1}}


def wall(levels):
    best = levels[0]
    for level in levels[1:]:
        if level[1] > best[1]:
            best = level
    return best[0]


class Trader:
    def run(self, state):
        depth = state.order_depths.get(PRODUCT)
        if not depth or not depth.buy_orders or not depth.sell_orders:
            return {}, 0, ""
        bids = sorted(depth.buy_orders.items(), reverse=True)
        asks = sorted((price, -volume) for price, volume in depth.sell_orders.items())
        fair = (wall(bids) + wall(asks)) / 2
        position = state.position.get(PRODUCT, 0)
        buy_room, sell_room = LIMIT - position, LIMIT + position
        orders = []
        for price, volume in asks:
            if price > fair - PARAMS[PRODUCT]["take_edge"] or buy_room == 0:
                break
            quantity = min(volume, buy_room)
            orders.append(Order(PRODUCT, price, quantity))
            buy_room -= quantity
        for price, volume in bids:
            if price < fair + PARAMS[PRODUCT]["take_edge"] or sell_room == 0:
                break
            quantity = min(volume, sell_room)
            orders.append(Order(PRODUCT, price, -quantity))
            sell_room -= quantity
        bid = min(bids[0][0] + 1, math.floor(fair - PARAMS[PRODUCT]["make_edge"]))
        ask = max(asks[0][0] - 1, math.ceil(fair + PARAMS[PRODUCT]["make_edge"]))
        if buy_room > 0:
            orders.append(Order(PRODUCT, bid, buy_room))
        if sell_room > 0:
            orders.append(Order(PRODUCT, ask, -sell_room))
        return {PRODUCT: orders}, 0, ""
