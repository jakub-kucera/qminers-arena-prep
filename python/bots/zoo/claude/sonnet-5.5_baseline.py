import json
import math
from typing import List

from datamodel import OrderDepth, TradingState, Order

LIMITS = {
    "RAINFOREST_RESIN": 50,
    "KELP": 50,
    "SQUID_INK": 50,
}

PARAMS = {
    "RAINFOREST_RESIN": {
        "fixed": 10000,
        "beta": 0.0,
        "take_edge": 1.0,       # take when price is at least this far inside fair
        "min_edge": 1.0,        # never quote closer than this to fair
        "disregard": 1.0,       # ignore book levels this close to fair when pennying
        "join": 2.0,            # join (not penny) a level this close to fair
        "default_edge": 4.0,    # quote distance when no level to follow
        "clear_thresh": 0,      # clear inventory at fair when |pos| above this
        "max_pos": 50,
    },
    "KELP": {
        "fixed": None,
        "beta": -0.2,
        "take_edge": 1.0,
        "min_edge": 1.0,
        "disregard": 1.0,
        "join": 0.0,
        "default_edge": 2.0,
        "clear_thresh": 20,
        "max_pos": 50,
    },
    "SQUID_INK": {
        "fixed": None,
        "beta": -0.15,
        "take_edge": 1.5,
        "min_edge": 1.5,
        "disregard": 1.0,
        "join": 0.0,
        "default_edge": 2.5,
        "clear_thresh": 15,
        "max_pos": 35,
    },
}

BIG = 15  # volume that marks a "wall" level


def wall_mid(depth: OrderDepth):
    bids = depth.buy_orders
    asks = depth.sell_orders
    if not bids or not asks:
        return None
    bb = [p for p, v in bids.items() if v >= BIG]
    aa = [p for p, v in asks.items() if -v >= BIG]
    bid = max(bb) if bb else max(bids)
    ask = min(aa) if aa else min(asks)
    return (bid + ask) / 2.0


def trade_product(sym: str, depth: OrderDepth, pos: int, prm: dict, mem: dict) -> List[Order]:
    limit = LIMITS[sym]
    max_pos = prm["max_pos"]

    # ---- fair value ----
    wm = wall_mid(depth)
    key = sym + "_wm"
    prev = mem.get(key)
    if wm is not None:
        mem[key] = wm
    if prm["fixed"] is not None:
        fair = float(prm["fixed"])
    else:
        if wm is None:
            wm = prev
            if wm is None:
                return []
            prev = None
        fair = wm
        if prev is not None and prm["beta"] != 0.0:
            adj = prm["beta"] * (wm - prev)
            adj = max(-2.0, min(2.0, adj))
            fair = wm + adj

    bids = dict(depth.buy_orders)
    asks = {p: -v for p, v in depth.sell_orders.items()}
    bids_rem = dict(bids)
    asks_rem = dict(asks)

    buy_cap = limit - pos
    sell_cap = limit + pos
    pos_eff = pos
    orders: List[Order] = []

    te = prm["take_edge"]

    # ---- take ----
    for p in sorted(asks_rem):
        if fair - p >= te and buy_cap > 0 and pos_eff < max_pos:
            q = min(asks_rem[p], buy_cap, max(0, max_pos - pos_eff))
            if q > 0:
                orders.append(Order(sym, p, q))
                asks_rem[p] -= q
                buy_cap -= q
                pos_eff += q
        else:
            break
    for p in sorted(bids_rem, reverse=True):
        if p - fair >= te and sell_cap > 0 and pos_eff > -max_pos:
            q = min(bids_rem[p], sell_cap, max(0, pos_eff + max_pos))
            if q > 0:
                orders.append(Order(sym, p, -q))
                bids_rem[p] -= q
                sell_cap -= q
                pos_eff -= q
        else:
            break

    # ---- clear at (or better than) fair ----
    ct = prm["clear_thresh"]
    if pos_eff > ct:
        for p in sorted(bids_rem, reverse=True):
            if p >= fair and bids_rem[p] > 0:
                q = min(bids_rem[p], pos_eff - ct, sell_cap)
                if q > 0:
                    orders.append(Order(sym, p, -q))
                    bids_rem[p] -= q
                    sell_cap -= q
                    pos_eff -= q
            if pos_eff <= ct:
                break
    elif pos_eff < -ct:
        for p in sorted(asks_rem):
            if p <= fair and asks_rem[p] > 0:
                q = min(asks_rem[p], -ct - pos_eff, buy_cap)
                if q > 0:
                    orders.append(Order(sym, p, q))
                    asks_rem[p] -= q
                    buy_cap -= q
                    pos_eff += q
            if pos_eff >= -ct:
                break

    # ---- make ----
    me = prm["min_edge"]
    bid_cap = math.floor(fair - me + 1e-9)
    ask_floor = math.ceil(fair + me - 1e-9)

    below = [p for p in bids if p < fair - prm["disregard"]]
    above = [p for p in asks if p > fair + prm["disregard"]]

    if below:
        bbbf = max(below)
        bid = bbbf if (fair - bbbf) <= prm["join"] else bbbf + 1
    else:
        bid = math.floor(fair - prm["default_edge"])
    if above:
        baaf = min(above)
        ask = baaf if (baaf - fair) <= prm["join"] else baaf - 1
    else:
        ask = math.ceil(fair + prm["default_edge"])
    bid = min(bid, bid_cap)
    ask = max(ask, ask_floor)

    # inventory skew
    frac = pos_eff / float(max_pos)
    shift = 0
    if abs(frac) > 0.8:
        shift = 2
    elif abs(frac) > 0.4:
        shift = 1
    if pos_eff > 0 and shift:
        bid -= shift
        ask = max(ask - shift, math.ceil(fair))
    elif pos_eff < 0 and shift:
        ask += shift
        bid = min(bid + shift, math.floor(fair))
    if bid >= ask:
        bid = ask - 1

    buy_room = min(buy_cap, max(0, max_pos - pos_eff))
    sell_room = min(sell_cap, max(0, pos_eff + max_pos))
    if buy_room > 0:
        orders.append(Order(sym, int(bid), int(buy_room)))
    if sell_room > 0:
        orders.append(Order(sym, int(ask), -int(sell_room)))

    return orders


class Trader:
    def run(self, state: TradingState):
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
            if not isinstance(mem, dict):
                mem = {}
        except Exception:
            mem = {}

        result = {}
        for sym, depth in state.order_depths.items():
            if sym not in PARAMS:
                continue
            pos = state.position.get(sym, 0) if state.position else 0
            try:
                result[sym] = trade_product(sym, depth, pos, PARAMS[sym], mem)
            except Exception:
                result[sym] = []

        conversions = 0
        return result, conversions, json.dumps(mem)
