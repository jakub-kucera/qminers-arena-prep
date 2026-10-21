import json
import math
from typing import Dict, List

from datamodel import Order, OrderDepth, TradingState

LIMITS = {"RAINFOREST_RESIN": 50, "KELP": 50, "SQUID_INK": 50}

CFG = {
    # Stable product: fair = long rolling mean of the wall mid (prior 10000).
    "RAINFOREST_RESIN": {
        "mode": "mm", "window": 200, "prior": 10000.0, "use_mean": True,
        "take_edge": 1, "make_edge": 1, "skew": 0.0, "revert": 0.0,
    },
    # Wandering product: fair = current wall mid, nudged against the last move
    # (short-horizon mean reversion), plus inventory skew.
    "KELP": {
        "mode": "mm", "window": 20, "prior": None, "use_mean": False,
        "take_edge": 1, "make_edge": 1, "skew": 1.0, "revert": 0.2,
    },
    # Volatile product: rolling z-score stat-arb with hysteresis, plus light market making.
    "SQUID_INK": {
        "mode": "mr", "window": 150, "min_hist": 50, "entry": 2.2, "exit": 0.3,
        "min_std": 2.0, "mm_size": 8, "band": 15,
    },
}


def wall_mid(od: OrderDepth):
    bids = od.buy_orders
    asks = od.sell_orders
    if bids and asks:
        bw = max(bids.items(), key=lambda kv: (kv[1], -kv[0]))[0]
        aw = max(asks.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        if bw < aw:
            return (bw + aw) / 2.0
        return (max(bids) + min(asks)) / 2.0
    if bids:
        return float(max(bids))
    if asks:
        return float(min(asks))
    return None


def mean_std(xs: List[float]):
    n = len(xs)
    if n == 0:
        return None, None
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(v)


class OrderBuilder:
    def __init__(self, symbol: str, pos: int, limit: int):
        self.symbol = symbol
        self.pos = pos
        self.limit = limit
        self.buy_room = limit - pos
        self.sell_room = limit + pos
        self.bought = 0
        self.sold = 0
        self.orders: List[Order] = []

    @property
    def live(self):
        return self.pos + self.bought - self.sold

    def buy(self, price: int, qty: int):
        qty = min(int(qty), self.buy_room - self.bought)
        if qty > 0:
            self.orders.append(Order(self.symbol, int(price), qty))
            self.bought += qty
        return qty

    def sell(self, price: int, qty: int):
        qty = min(int(qty), self.sell_room - self.sold)
        if qty > 0:
            self.orders.append(Order(self.symbol, int(price), -qty))
            self.sold += qty
        return qty


def market_make(ob: OrderBuilder, od: OrderDepth, fair: float, cfg: dict):
    asks = sorted((p, -v) for p, v in od.sell_orders.items())
    bids = sorted(((p, v) for p, v in od.buy_orders.items()), reverse=True)
    te = cfg["take_edge"]
    me = cfg["make_edge"]

    # Take mispriced liquidity; trade at fair only to reduce inventory.
    for p, v in asks:
        if p <= fair - te:
            ob.buy(p, v)
        elif p <= fair and ob.live < 0:
            ob.buy(p, min(v, -ob.live))
        else:
            break
    for p, v in bids:
        if p >= fair + te:
            ob.sell(p, v)
        elif p >= fair and ob.live > 0:
            ob.sell(p, min(v, ob.live))
        else:
            break

    # Make: penny the best resting quotes that are still outside fair +/- edge.
    rfair = fair - cfg["skew"] * ob.live / ob.limit
    bid_cap = math.floor(rfair - me + 1e-9)
    ask_floor = math.ceil(rfair + me - 1e-9)
    bid_px = None
    for p, _ in bids:
        if p + 1 <= bid_cap:
            bid_px = p + 1
            break
    if bid_px is None:
        bid_px = bid_cap - 1
    ask_px = None
    for p, _ in asks:
        if p - 1 >= ask_floor:
            ask_px = p - 1
            break
    if ask_px is None:
        ask_px = ask_floor + 1
    bid_px = min(bid_px, bid_cap)
    ask_px = max(ask_px, ask_floor)
    if bid_px >= ask_px:
        return
    ob.buy(bid_px, ob.buy_room - ob.bought)
    ob.sell(ask_px, ob.sell_room - ob.sold)


def mean_reversion(ob: OrderBuilder, od: OrderDepth, wm: float, hist: List[float],
                   prev_target: int, cfg: dict) -> int:
    L = ob.limit
    target = prev_target
    if len(hist) >= cfg["min_hist"]:
        m, s = mean_std(hist[-cfg["window"]:])
        s = max(s, cfg["min_std"])
        z = (wm - m) / s
        if z >= cfg["entry"]:
            target = -L
        elif z <= -cfg["entry"]:
            target = L
        elif abs(z) <= cfg["exit"]:
            target = 0
        elif target > 0 and z >= 0:
            target = 0
        elif target < 0 and z <= 0:
            target = 0
    else:
        target = 0

    asks = sorted((p, -v) for p, v in od.sell_orders.items())
    bids = sorted(((p, v) for p, v in od.buy_orders.items()), reverse=True)

    # Move to target by taking liquidity.
    diff = target - ob.live
    if diff > 0:
        for p, v in asks:
            if diff <= 0:
                break
            diff -= ob.buy(p, min(v, diff))
    elif diff < 0:
        need = -diff
        for p, v in bids:
            if need <= 0:
                break
            need -= ob.sell(p, min(v, need))

    # Passive quotes around the wall mid, kept within a band of the target.
    if not bids or not asks:
        return target
    best_bid = bids[0][0]
    best_ask = asks[0][0]
    bid_px = min(best_bid + 1, math.floor(wm - 1 + 1e-9))
    ask_px = max(best_ask - 1, math.ceil(wm + 1 - 1e-9))
    if bid_px >= ask_px:
        return target
    live = ob.live
    band = cfg["band"]
    want_buy = max(0, target - live)
    want_sell = max(0, live - target)
    bq = want_buy + (cfg["mm_size"] if live < target + band else 0)
    sq = want_sell + (cfg["mm_size"] if live > target - band else 0)
    if bq > 0:
        ob.buy(bid_px, bq)
    if sq > 0:
        ob.sell(ask_px, sq)
    return target


class Trader:
    def run(self, state: TradingState):
        try:
            data = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            data = {}
        hists: Dict[str, List[float]] = data.get("h", {})
        targets: Dict[str, int] = data.get("t", {})
        prevs: Dict[str, float] = data.get("p", {})

        result: Dict[str, List[Order]] = {}
        for product, od in state.order_depths.items():
            if product not in CFG:
                continue
            cfg = CFG[product]
            limit = LIMITS.get(product, 20)
            pos = state.position.get(product, 0) if state.position else 0
            ob = OrderBuilder(product, pos, limit)
            try:
                wm = wall_mid(od)
                if wm is None:
                    result[product] = []
                    continue
                hist = hists.get(product, [])
                hist.append(round(wm, 1))
                if len(hist) > cfg["window"]:
                    hist = hist[-cfg["window"]:]
                hists[product] = hist

                if cfg["mode"] == "mm":
                    if cfg["use_mean"]:
                        if len(hist) >= 20:
                            m, _ = mean_std(hist)
                            fair = float(round(m))
                        else:
                            fair = cfg["prior"]
                    else:
                        prev = prevs.get(product, wm)
                        fair = wm - cfg["revert"] * (wm - prev)
                    prevs[product] = wm
                    market_make(ob, od, fair, cfg)
                else:
                    t = mean_reversion(ob, od, wm, hist, int(targets.get(product, 0)), cfg)
                    targets[product] = t
            except Exception:
                ob.orders = []
            result[product] = ob.orders

        trader_data = json.dumps({"h": hists, "t": targets, "p": prevs}, separators=(",", ":"))
        return result, 0, trader_data
