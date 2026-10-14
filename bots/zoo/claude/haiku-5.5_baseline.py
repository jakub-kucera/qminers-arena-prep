import json
import math
from typing import Dict, List, Optional

from datamodel import Order, OrderDepth, TradingState

POSITION_LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}

SETTINGS = {
    # Stable value: trade around a fixed fair value of 10000.
    "RAINFOREST_RESIN": {
        "mode": "fixed",
        "fair": 10000.0,
        "take_edge": 1,
        "make_edge": 2,
        "quote_size": 15,
        "skew": 0.04,
    },
    # Random-walk-like: fair value is the current book mid.
    "KELP": {
        "mode": "mid",
        "take_edge": 1,
        "make_edge": 2,
        "quote_size": 12,
        "skew": 0.04,
    },
    # Volatile with possible mean reversion: fair value is a slow EMA of the mid.
    "SQUID_INK": {
        "mode": "ema",
        "alpha": 0.02,
        "take_edge": 2,
        "make_edge": 2,
        "quote_size": 8,
        "skew": 0.04,
    },
}


def _load(raw: str) -> Dict:
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _best_bid(depth: OrderDepth) -> Optional[int]:
    return max(depth.buy_orders) if depth.buy_orders else None


def _best_ask(depth: OrderDepth) -> Optional[int]:
    return min(depth.sell_orders) if depth.sell_orders else None


def _mid(depth: OrderDepth) -> Optional[float]:
    bb, ba = _best_bid(depth), _best_ask(depth)
    if bb is None or ba is None:
        return None
    return (bb + ba) / 2.0


def _fair(product: str, depth: OrderDepth, store: Dict, cfg: Dict) -> Optional[float]:
    mode = cfg["mode"]
    if mode == "fixed":
        return cfg["fair"]
    mid = _mid(depth)
    if mode == "mid":
        return mid if mid is not None else store.get(product)
    # ema
    if mid is not None:
        prev = store.get(product)
        fair = mid if prev is None else prev + cfg["alpha"] * (mid - prev)
        store[product] = fair
        return fair
    return store.get(product)


def _plan(product: str, depth: OrderDepth, pos: int, store: Dict, cfg: Dict) -> List[Order]:
    limit = POSITION_LIMITS[product]
    fair = _fair(product, depth, store, cfg)
    if fair is None:
        return []

    bb, ba = _best_bid(depth), _best_ask(depth)
    # Room to buy / sell, tracked so that all buys (and all sells) together stay within limits.
    buy_room = limit - pos
    sell_room = limit + pos
    orders: List[Order] = []

    # Take mispriced resting orders.
    if ba is not None:
        for ask in sorted(depth.sell_orders):
            if ask > fair - cfg["take_edge"] or buy_room <= 0:
                break
            q = min(-depth.sell_orders[ask], buy_room)
            if q > 0:
                orders.append(Order(product, ask, q))
                buy_room -= q
    if bb is not None:
        for bid in sorted(depth.buy_orders, reverse=True):
            if bid < fair + cfg["take_edge"] or sell_room <= 0:
                break
            q = min(depth.buy_orders[bid], sell_room)
            if q > 0:
                orders.append(Order(product, bid, -q))
                sell_room -= q

    # Make: quote around fair value, shifted against our inventory.
    skew = pos * cfg["skew"]
    bid_px = math.floor(fair - cfg["make_edge"] - skew)
    ask_px = math.ceil(fair + cfg["make_edge"] - skew)
    if ba is not None:
        bid_px = min(bid_px, ba - 1)
    if bb is not None:
        ask_px = max(ask_px, bb + 1)

    if bid_px < ask_px:
        qb = min(buy_room, cfg["quote_size"])
        if qb > 0:
            orders.append(Order(product, int(bid_px), qb))
        qs = min(sell_room, cfg["quote_size"])
        if qs > 0:
            orders.append(Order(product, int(ask_px), -qs))
    return orders


class Trader:
    def run(self, state: TradingState):
        store = _load(state.traderData)
        result: Dict[str, List[Order]] = {}
        for product, cfg in SETTINGS.items():
            try:
                depth = state.order_depths.get(product)
                if depth is None:
                    result[product] = []
                    continue
                pos = state.position.get(product, 0)
                result[product] = _plan(product, depth, pos, store, cfg)
            except Exception:
                result[product] = []
        conversions = 0
        traderData = json.dumps(store)
        return result, conversions, traderData
