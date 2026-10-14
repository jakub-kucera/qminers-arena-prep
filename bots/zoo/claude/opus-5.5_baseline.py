import json
import math
from typing import Dict, List

from datamodel import Order, OrderDepth, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}

PARAMS = {
    "RAINFOREST_RESIN": {"take_edge": 1, "make_edge": 1, "soft": 50, "skew_at": 0.5},
    "KELP": {"take_edge": 1, "make_edge": 1, "soft": 50, "skew_at": 0.5},
    "SQUID_INK": {"take_edge": 2, "make_edge": 1, "soft": 30, "skew_at": 0.4,
                  "reversion": 0.2},
}


def wall_mid(depth: OrderDepth):
    """Mid between the largest-volume level on each side (the resident market maker)."""
    if not depth.buy_orders or not depth.sell_orders:
        return None
    bid_wall = max(depth.buy_orders.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    ask_wall = max(depth.sell_orders.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    if bid_wall >= ask_wall:
        bid_wall = max(depth.buy_orders)
        ask_wall = min(depth.sell_orders)
    return (bid_wall + ask_wall) / 2.0


def trade_product(product: str, depth: OrderDepth, pos: int, fair: float,
                  p: dict) -> List[Order]:
    limit = LIMITS[product]
    orders: List[Order] = []
    buy_cap = limit - pos   # max total buy quantity this iteration
    sell_cap = limit + pos  # max total sell quantity this iteration
    proj = pos

    asks = sorted(depth.sell_orders.items())                  # ascending
    bids = sorted(depth.buy_orders.items(), reverse=True)     # descending

    # 1. Take mispriced liquidity.
    for price, vol in asks:
        if buy_cap <= 0 or price > fair - p["take_edge"]:
            break
        q = min(-vol, buy_cap)
        if q > 0:
            orders.append(Order(product, price, q))
            buy_cap -= q
            proj += q
    for price, vol in bids:
        if sell_cap <= 0 or price < fair + p["take_edge"]:
            break
        q = min(vol, sell_cap)
        if q > 0:
            orders.append(Order(product, price, -q))
            sell_cap -= q
            proj -= q

    # 2. Clear inventory at fair value (zero edge) when the book allows it.
    if proj > 0:
        for price, vol in bids:
            if proj <= 0 or sell_cap <= 0 or price < fair:
                break
            if price < fair + p["take_edge"]:  # not already taken above
                q = min(vol, proj, sell_cap)
                if q > 0:
                    orders.append(Order(product, price, -q))
                    sell_cap -= q
                    proj -= q
    elif proj < 0:
        for price, vol in asks:
            if proj >= 0 or buy_cap <= 0 or price > fair:
                break
            if price > fair - p["take_edge"]:
                q = min(-vol, -proj, buy_cap)
                if q > 0:
                    orders.append(Order(product, price, q))
                    buy_cap -= q
                    proj += q

    # 3. Make: penny the best quotes, never inside fair -/+ make_edge.
    bid_limit = math.floor(fair - p["make_edge"])
    ask_limit = math.ceil(fair + p["make_edge"])
    bid_px = min(bid_limit, max(depth.buy_orders) + 1) if depth.buy_orders else bid_limit - 1
    ask_px = max(ask_limit, min(depth.sell_orders) - 1) if depth.sell_orders else ask_limit + 1

    skew_level = p["skew_at"] * limit
    if proj > skew_level:
        ask_px = max(ask_px - 1, math.ceil(fair))
        bid_px -= 1
    elif proj < -skew_level:
        bid_px = min(bid_px + 1, math.floor(fair))
        ask_px += 1
    if bid_px >= ask_px:
        bid_px = ask_px - 1

    soft = p["soft"]
    buy_q = min(buy_cap, max(0, soft - proj))
    sell_q = min(sell_cap, max(0, soft + proj))
    if buy_q > 0:
        orders.append(Order(product, int(bid_px), int(buy_q)))
    if sell_q > 0:
        orders.append(Order(product, int(ask_px), -int(sell_q)))
    return orders


class Trader:
    def run(self, state: TradingState):
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}
        result: Dict[str, List[Order]] = {}

        for product, depth in state.order_depths.items():
            if product not in PARAMS:
                continue
            p = PARAMS[product]
            pos = state.position.get(product, 0)
            try:
                if product == "RAINFOREST_RESIN":
                    fair = 10000.0
                else:
                    wm = wall_mid(depth)
                    last = mem.get(product + "_wm")
                    if wm is None:
                        if last is None:
                            continue
                        wm = last
                    fair = wm
                    rev = p.get("reversion", 0.0)
                    if rev and last is not None:
                        # short-horizon mean reversion: lean against the last move
                        fair = wm - rev * (wm - last)
                    mem[product + "_wm"] = wm
                result[product] = trade_product(product, depth, pos, fair, p)
            except Exception:
                result[product] = []

        return result, 0, json.dumps(mem)
