import json
import math
from typing import Dict, List

from datamodel import Order, OrderDepth, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}

# fixed:      fixed fair value (None -> estimate from the book)
# take_edge:  take book orders at least this far through fair
# disregard:  ignore book levels within this distance of fair when choosing quote prices
# join:       join a level within this distance of fair instead of pennying it
# default:    quote distance when the other side of the book is empty
# soft:       above |position| soft, skew quotes one tick toward reducing inventory
# reversion:  fair = wall_mid - reversion * (last change of wall_mid)
# quote_size: max size per quote side
PARAMS = {
    "RAINFOREST_RESIN": dict(fixed=10000, take_edge=1, disregard=1, join=2, default=4,
                             soft=25, reversion=0.0, quote_size=50),
    "KELP": dict(fixed=None, take_edge=1, disregard=1, join=0, default=2,
                 soft=25, reversion=0.0, quote_size=50),
    "SQUID_INK": dict(fixed=None, take_edge=1, disregard=1, join=0, default=2,
                      soft=15, reversion=0.15, quote_size=20),
}


def wall_mid(depth: OrderDepth):
    """Mid of the largest-volume level on each side (the resident market maker's quotes)."""
    if not depth.buy_orders or not depth.sell_orders:
        return None
    bid_wall = max(depth.buy_orders.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    ask_wall = max(depth.sell_orders.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    if bid_wall >= ask_wall:
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0
    return (bid_wall + ask_wall) / 2.0


class Trader:
    def run(self, state: TradingState):
        try:
            memory = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            memory = {}
        last_wm: Dict[str, float] = memory.get("wm", {})

        result: Dict[str, List[Order]] = {}
        for product, depth in state.order_depths.items():
            if product not in PARAMS:
                continue
            try:
                orders = self.trade(product, depth, state.position.get(product, 0), last_wm)
            except Exception:
                orders = []
            result[product] = orders

        return result, 0, json.dumps({"wm": last_wm})

    def trade(self, product: str, depth: OrderDepth, position: int, last_wm: Dict[str, float]) -> List[Order]:
        p = PARAMS[product]
        limit = LIMITS[product]

        # ---- fair value ----
        if p["fixed"] is not None:
            fair = float(p["fixed"])
        else:
            wm = wall_mid(depth)
            prev = last_wm.get(product)
            if wm is None:
                if prev is None:
                    return []
                wm = prev
                fair = wm
            else:
                fair = wm
                if prev is not None and p["reversion"]:
                    fair = wm - p["reversion"] * (wm - prev)
            last_wm[product] = wm

        orders: List[Order] = []
        buy_room = limit - position   # total we may still buy this iteration
        sell_room = limit + position  # total we may still sell this iteration
        pos = position                # position if every take fills

        sells = sorted(depth.sell_orders.items())                  # ask price ascending
        buys = sorted(depth.buy_orders.items(), reverse=True)      # bid price descending

        # ---- take mispriced orders (and reduce inventory at fair) ----
        for price, vol in sells:
            vol = -vol
            if buy_room <= 0:
                break
            if price <= fair - p["take_edge"] or (price <= fair and pos < 0):
                q = min(vol, buy_room)
                if price >= fair:
                    q = min(q, -pos)  # at fair: only flatten
                if q > 0:
                    orders.append(Order(product, int(price), q))
                    buy_room -= q
                    pos += q
            else:
                break
        for price, vol in buys:
            if sell_room <= 0:
                break
            if price >= fair + p["take_edge"] or (price >= fair and pos > 0):
                q = min(vol, sell_room)
                if price <= fair:
                    q = min(q, pos)
                if q > 0:
                    orders.append(Order(product, int(price), -q))
                    sell_room -= q
                    pos -= q
            else:
                break

        # ---- make: penny or join the book outside fair ----
        asks_out = [pr for pr in depth.sell_orders if pr > fair + p["disregard"]]
        bids_out = [pr for pr in depth.buy_orders if pr < fair - p["disregard"]]

        if asks_out:
            best = min(asks_out)
            ask = best if best - fair <= p["join"] else best - 1
        else:
            ask = math.ceil(fair + p["default"])
        if bids_out:
            best = max(bids_out)
            bid = best if fair - best <= p["join"] else best + 1
        else:
            bid = math.floor(fair - p["default"])

        # never quote through fair, except to unload inventory
        min_ask = math.floor(fair) + 1
        max_bid = math.ceil(fair) - 1
        if pos > p["soft"]:
            ask -= 1
            bid -= 1
            min_ask = math.ceil(fair)
        elif pos < -p["soft"]:
            ask += 1
            bid += 1
            max_bid = math.floor(fair)
        ask = max(int(ask), min_ask)
        bid = min(int(bid), max_bid)
        if bid >= ask:
            bid = ask - 1

        bq = min(buy_room, p["quote_size"])
        sq = min(sell_room, p["quote_size"])
        if bq > 0:
            orders.append(Order(product, int(bid), int(bq)))
        if sq > 0:
            orders.append(Order(product, int(ask), -int(sq)))
        return orders
