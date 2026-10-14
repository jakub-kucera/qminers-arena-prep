"""Trend-following trader.

For every product it tracks a "wall mid" (the mid between the deepest bid and
ask levels, which is far less noisy than the best-bid/best-ask mid), a fast and a
slow exponential moving average of it, and an EMA estimate of the per-tick
volatility.  The crossover gap (fast - slow) is normalised by the gap a pure
random walk would produce, giving a z-score:

    z = (ema_fast - ema_slow) / (sigma * sqrt((slow - fast) / 2))

Regimes, with hysteresis so noise does not churn the position:
  * flat  -> long  when z >  entry and price is above the slow EMA
  * flat  -> short when z < -entry and price is below the slow EMA
  * long/short -> flat when |z| fades below `exit`, the crossover flips, or a
    trailing stop (measured from the best price since entry) is hit.
After a stop, that direction is blocked until z falls back below `exit`, so the
bot does not jump straight back into a trend that has just failed.

In a trend the target is the full position limit.  Execution takes book
liquidity up to the wall price (never paying through the deep level) and posts
the remainder one tick inside the spread to catch other participants' trades.
All state lives in traderData (JSON).
"""

import json
import math
from typing import Dict, List

from datamodel import Order, OrderDepth, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}

PARAMS = {
    # Stable product: the wall mid barely moves, so z stays near zero and the
    # trend logic stays out unless a genuine, sustained move appears.
    "RAINFOREST_RESIN": dict(fast=50, slow=300, vol_span=1000, sigma0=0.5,
                             sigma_floor=0.5, entry=3.0, exit=0.5, stop=1.5,
                             warmup=300),
    "KELP": dict(fast=100, slow=500, vol_span=1000, sigma0=0.4,
                 sigma_floor=0.15, entry=2.0, exit=0.5, stop=1.5,
                 warmup=300),
    "SQUID_INK": dict(fast=100, slow=500, vol_span=1000, sigma0=1.5,
                      sigma_floor=0.3, entry=2.0, exit=0.5, stop=1.5,
                      warmup=300),
}
DEFAULT_PARAMS = dict(fast=100, slow=500, vol_span=1000, sigma0=1.0,
                      sigma_floor=0.3, entry=2.0, exit=0.5, stop=1.5, warmup=300)
DEFAULT_LIMIT = 20


def wall_prices(depth: OrderDepth):
    """Best bid/ask and the bid/ask levels with the largest volume."""
    bids = depth.buy_orders or {}
    asks = depth.sell_orders or {}
    best_bid = max(bids) if bids else None
    best_ask = min(asks) if asks else None
    wall_bid = max(bids, key=lambda p: (bids[p], -p)) if bids else None
    wall_ask = max(asks, key=lambda p: (-asks[p], p)) if asks else None
    return best_bid, best_ask, wall_bid, wall_ask


class Trader:
    def run(self, state: TradingState):
        try:
            memory = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            memory = {}

        result: Dict[str, List[Order]] = {}
        for product, depth in state.order_depths.items():
            params = PARAMS.get(product, DEFAULT_PARAMS)
            limit = LIMITS.get(product, DEFAULT_LIMIT)
            position = state.position.get(product, 0) if state.position else 0
            try:
                mem = memory.get(product, {})
                orders, mem = self.trade(product, depth, position, limit, params, mem)
                memory[product] = mem
            except Exception:
                orders = []
            result[product] = orders

        return result, 0, json.dumps(memory, separators=(",", ":"))

    # ------------------------------------------------------------------ signal
    def update_signal(self, price: float, params: dict, mem: dict) -> float:
        if "ef" not in mem:
            mem.update(ef=price, es=price, var=params["sigma0"] ** 2,
                       last=price, n=0, reg=0, peak=price, blk=0)
        a_f = 2.0 / (params["fast"] + 1)
        a_s = 2.0 / (params["slow"] + 1)
        a_v = 2.0 / (params["vol_span"] + 1)
        ret = price - mem["last"]
        mem["var"] += a_v * (ret * ret - mem["var"])
        mem["ef"] += a_f * (price - mem["ef"])
        mem["es"] += a_s * (price - mem["es"])
        mem["last"] = price
        mem["n"] += 1

        sigma = max(math.sqrt(max(mem["var"], 0.0)), params["sigma_floor"])
        scale = sigma * math.sqrt(max(params["slow"] - params["fast"], 1) / 2.0)
        return (mem["ef"] - mem["es"]) / scale, scale

    def update_regime(self, price: float, z: float, scale: float,
                      params: dict, mem: dict) -> int:
        reg = mem["reg"]
        entry, exit_ = params["entry"], params["exit"]

        # A blocked direction is released once its signal has faded.
        if mem["blk"] == 1 and z < exit_:
            mem["blk"] = 0
        if mem["blk"] == -1 and z > -exit_:
            mem["blk"] = 0

        if mem["n"] < params["warmup"]:
            mem["reg"] = 0
            return 0

        stop_dist = params["stop"] * scale
        if reg == 1:
            mem["peak"] = max(mem["peak"], price)
            if price < mem["peak"] - stop_dist:
                reg, mem["blk"] = 0, 1
            elif z < exit_:
                reg = 0
        elif reg == -1:
            mem["peak"] = min(mem["peak"], price)
            if price > mem["peak"] + stop_dist:
                reg, mem["blk"] = 0, -1
            elif z > -exit_:
                reg = 0

        if reg == 0:
            if z > entry and price > mem["es"] and mem["blk"] != 1:
                reg, mem["peak"] = 1, price
            elif z < -entry and price < mem["es"] and mem["blk"] != -1:
                reg, mem["peak"] = -1, price

        mem["reg"] = reg
        return reg

    # --------------------------------------------------------------- trading
    def trade(self, product, depth, position, limit, params, mem):
        best_bid, best_ask, wall_bid, wall_ask = wall_prices(depth)
        if wall_bid is not None and wall_ask is not None:
            price = (wall_bid + wall_ask) / 2.0
        elif best_bid is not None and best_ask is not None:
            price = (best_bid + best_ask) / 2.0
        elif "last" in mem:
            price = mem["last"]
        else:
            return [], mem

        z, scale = self.update_signal(price, params, mem)
        reg = self.update_regime(price, z, scale, params, mem)

        target = reg * limit
        delta = max(-limit - position, min(limit - position, target - position))
        orders: List[Order] = []
        if delta == 0:
            return orders, self.compact(mem)

        if delta > 0:
            remaining = delta
            cap = wall_ask if wall_ask is not None else best_ask
            for ask in sorted(depth.sell_orders):
                if remaining <= 0 or cap is None or ask > cap:
                    break
                qty = min(remaining, -depth.sell_orders[ask])
                if qty > 0:
                    orders.append(Order(product, ask, qty))
                    remaining -= qty
            if remaining > 0 and best_bid is not None:
                passive = best_bid + 1
                if best_ask is not None and passive >= best_ask:
                    passive = best_bid
                orders.append(Order(product, passive, remaining))
        else:
            remaining = -delta
            cap = wall_bid if wall_bid is not None else best_bid
            for bid in sorted(depth.buy_orders, reverse=True):
                if remaining <= 0 or cap is None or bid < cap:
                    break
                qty = min(remaining, depth.buy_orders[bid])
                if qty > 0:
                    orders.append(Order(product, bid, -qty))
                    remaining -= qty
            if remaining > 0 and best_ask is not None:
                passive = best_ask - 1
                if best_bid is not None and passive <= best_bid:
                    passive = best_ask
                orders.append(Order(product, passive, -remaining))

        return orders, self.compact(mem)

    @staticmethod
    def compact(mem: dict) -> dict:
        for key in ("ef", "es", "var", "last", "peak"):
            mem[key] = round(mem[key], 5)
        return mem
