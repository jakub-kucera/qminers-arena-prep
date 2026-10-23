"""A taker: a --vs rival that trades at the touch, on momentum and at random, the flow a field of
other teams' bots sends at our quotes.

    uv run python -m arena.backtest python/bots/template.py 1 --vs python/bots/rivals/taker.py

Each product, each tick, two uniform draws u and v (draw: a hash of SEED, the timestamp, the
product and the draw's number, so a day gives the same draws whatever the other bots do, and the
Rust twin the same to the bit):
  1. with u < RATE it follows the mid's last move: buys SIZE at the best ask after a rise, sells at
     the best bid after a fall (a side by v when the mid didn't move);
  2. with RATE <= u < RATE + NOISE it takes SIZE on a side by v alone;
  3. at HOLD or more either way it only unwinds, SIZE at a time at the touch, whatever u says.
It never rests an order, and keeps the last mid per product in traderData.
"""

import json

from datamodel import Cancel, Order, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}
DEFAULT_LIMIT = 50
RATE = 0.05  # the share of ticks it follows the last move
NOISE = 0.05  # the share of ticks it takes a random side
SIZE = 5
HOLD = 30
SEED = 0

_MASK = (1 << 64) - 1


def draw(timestamp: int, product: str, k: int) -> float:
    """A uniform draw in [0, 1): FNV-1a of the product's name, mixed with SEED, the timestamp and k
    through splitmix64's finalizer, in 64-bit arithmetic (rust/src/bots/rivals/taker.rs `draw`)."""
    h = 0xCBF29CE484222325
    for byte in product.encode():
        h = ((h ^ byte) * 0x100000001B3) & _MASK
    x = (h ^ ((SEED & _MASK) * 0x9E3779B97F4A7C15) ^ ((timestamp & _MASK) * 0xBF58476D1CE4E5B9) ^ k) & _MASK
    x = (x + 0x9E3779B97F4A7C15) & _MASK
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & _MASK
    x ^= x >> 31
    return (x >> 11) / 9007199254740992.0


class Trader:
    def run(self, state: TradingState):
        memory = json.loads(state.traderData) if state.traderData else {}
        result = {}
        for product, depth in state.order_depths.items():
            orders = [Cancel(o.id) for o in getattr(state, "open_orders", {}).get(product, [])]
            result[product] = orders
            if not depth.buy_orders or not depth.sell_orders:
                continue
            limit = LIMITS.get(product, DEFAULT_LIMIT)
            bid, ask = max(depth.buy_orders), min(depth.sell_orders)
            mid = (bid + ask) / 2
            last = memory.get(product)
            memory[product] = mid
            u, v = draw(state.timestamp, product, 0), draw(state.timestamp, product, 1)
            position = state.position.get(product, 0)
            side = 0
            if position >= HOLD:
                side = -1
            elif position <= -HOLD:
                side = 1
            elif u < RATE:
                move = 0 if last is None else mid - last
                side = 1 if move > 0 or (move == 0 and v < 0.5) else -1
            elif u < RATE + NOISE:
                side = 1 if v < 0.5 else -1
            if side > 0:
                q = min(SIZE, -depth.sell_orders[ask], limit - position)
                if q > 0:
                    orders.append(Order(product, ask, q, ioc=True))
            elif side < 0:
                q = min(SIZE, depth.buy_orders[bid], limit + position)
                if q > 0:
                    orders.append(Order(product, bid, -q, ioc=True))
        return result, 0, json.dumps(memory)
