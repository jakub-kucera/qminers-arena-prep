"""Meridian round bot. Standard library only; all state in `memory`.

CALDERA: its mid moves only in jumps, which mostly reverse; hold the full limit against the last
         jump once the day's jumps have shown they reverse.
LUMEN:   mean-reverts to a level (100); quote inside the spread, leaning the position against the
         distance from the level.
OBERON:  noise around a slow fair value; fair = EMA of the mid; quote inside, take mispricings.
Every product: per-product try/except, orders sized so the limit check can never fail.
"""
import math

PARAMS = {
    "CALDERA": {
        "mode": "jump",
        "jump_min": 1.0,        # a mid move at least this big is a jump (CR; data: always 6.0, spread 0.6)
        "gate_n": 8,            # jumps seen before holding against them
        "gate_share": 0.6,      # share of jumps that reversed (with a 2/2 prior) needed
        "window": 0.06,         # >0: the share is an EMA over jumps with this weight, not the day's count
        "momentum": 1,          # 1: hold with the jumps when the share is below 1 - gate_share
        "stop": 2000.0,         # loss from the peak that stops the product for the day (0 = off)
    },
    "LUMEN": {
        "mode": "level",
        "level": 100.0,
        "guard": 1.0,           # if the day's mean wall mid is further than this from the level, use it (0 = off)
        "warm": 1000,           # steps before the guard may act
        "beta": 0.6,            # share of the distance to the level added to the fair
        "skew": 0.0,            # fair moves this many ticks against a full-limit position
        "wall": 10,             # levels at least this big define the fair (wall mid)
        "edge": 2,              # quotes stay at least this many ticks from the fair
        "size": 30,             # quote size per side
        "take_edge": 4,         # take when the touch is this many ticks through the fair (0 = off)
        "stop": 1000.0,
    },
    "OBERON": {
        "mode": "mm",
        "alpha": 0.1,           # EMA weight of the newest mid
        "edge": 1,              # quote at least this many ticks from the fair
        "take_edge": 1,         # take when the touch is this many ticks through the fair
        "size": 60,
        "skew": 1.0,            # fair moves this many ticks against a full-limit position
        "stop": 30.0,
    },
}
EPS = 1e-9


def init(session):
    return {"n": 0, "lim": {s: v["position_limit"] for s, v in session["instruments"].items()},
            "tick": {s: v["tick_size"] for s, v in session["instruments"].items()}, "p": {}}


def _px(x, tick):
    return round(round(x / tick) * tick, 6)


def _floor(x, tick):
    return round(math.floor(x / tick + 1e-6) * tick, 6)


def _ceil(x, tick):
    return round(math.ceil(x / tick - 1e-6) * tick, 6)


def _mid(book):
    return (book["bids"][0][0] + book["asks"][0][0]) / 2


def _wall_mid(book, wall):
    bids = [p for p, q in book["bids"] if q >= wall]
    asks = [p for p, q in book["asks"] if q >= wall]
    if bids and asks:
        return (bids[0] + asks[0]) / 2
    return _mid(book)


class Plan:
    """Orders for one product, kept within the limit counting buys and sells separately."""

    def __init__(self, pos, limit):
        self.pos, self.limit = pos, limit
        self.takes = []      # (side, price, size), sent IOC
        self.quotes = []     # (side, price, size), sent GTC
        self.buy_room = limit - pos
        self.sell_room = limit + pos

    def add(self, kind, side, price, size):
        room = self.buy_room if side == "BUY" else self.sell_room
        size = int(min(size, room))
        if size <= 0:
            return 0
        if side == "BUY":
            self.buy_room -= size
        else:
            self.sell_room -= size
        (self.takes if kind == "take" else self.quotes).append((side, price, size))
        return size


def _caldera(sym, book, pos, limit, tick, P, st, plan):
    mid = _mid(book)
    last = st.get("mid")
    st["mid"] = mid
    if last is not None and abs(mid - last) >= P["jump_min"]:
        sign = 1 if mid > last else -1
        prev = st.get("sign", 0)
        if prev:
            rev = 1.0 if sign != prev else 0.0
            st["jumps"] = st.get("jumps", 0) + 1
            st["rev"] = st.get("rev", 0) + rev
            w = max(P["window"], 1.0 / st["jumps"])
            st["ema"] = st.get("ema", 0.5) * (1 - w) + w * rev
        st["sign"] = sign
    share = (st.get("rev", 0) + 2.0) / (st.get("jumps", 0) + 4.0)
    if P["window"]:   # both the day's share and the recent one must agree
        lo, hi = min(share, st.get("ema", 0.5)), max(share, st.get("ema", 0.5))
    else:
        lo = hi = share
    target = 0
    if st.get("jumps", 0) >= P["gate_n"] and st.get("sign"):
        if lo >= P["gate_share"]:
            target = -st["sign"] * limit
        elif P["momentum"] and hi <= 1 - P["gate_share"]:
            target = st["sign"] * limit
    want = target - pos
    if want > 0:
        for price, size in book["asks"]:
            want -= plan.add("take", "BUY", price, min(size, want))
            if want <= 0:
                break
    elif want < 0:
        want = -want
        for price, size in book["bids"]:
            want -= plan.add("take", "SELL", price, min(size, want))
            if want <= 0:
                break


def _quote_around(book, fair, tick, P, plan, buy_size, sell_size):
    bb, ba = book["bids"][0][0], book["asks"][0][0]
    take_edge = P.get("take_edge", 0)
    if take_edge:
        for price, size in book["asks"]:
            if price <= fair - take_edge * tick + EPS:
                buy_size -= plan.add("take", "BUY", price, size)
        for price, size in book["bids"]:
            if price >= fair + take_edge * tick - EPS:
                sell_size -= plan.add("take", "SELL", price, size)
    bid = min(bb + tick, _floor(fair - P["edge"] * tick, tick))
    ask = max(ba - tick, _ceil(fair + P["edge"] * tick, tick))
    if bid >= ba - EPS:
        bid = ba - tick
    if ask <= bb + EPS:
        ask = bb + tick
    if buy_size > 0:
        plan.add("quote", "BUY", _px(bid, tick), buy_size)
    if sell_size > 0:
        plan.add("quote", "SELL", _px(ask, tick), sell_size)


def _lumen(sym, book, pos, limit, tick, P, st, plan):
    wm = _wall_mid(book, P["wall"])
    st["sum"] = st.get("sum", 0.0) + wm
    st["cnt"] = st.get("cnt", 0) + 1
    level = P["level"]
    if P["guard"] and st["cnt"] >= P["warm"]:
        anchor = st["sum"] / st["cnt"]
        if abs(anchor - level) > P["guard"]:
            level = anchor
    fair = wm + P["beta"] * (level - wm) - P["skew"] * tick * pos / limit
    _quote_around(book, fair, tick, P, plan, P["size"], P["size"])


def _oberon(sym, book, pos, limit, tick, P, st, plan):
    mid = _mid(book)
    ema = st.get("ema")
    ema = mid if ema is None else P["alpha"] * mid + (1 - P["alpha"]) * ema
    st["ema"] = ema
    fair = ema - P["skew"] * tick * pos / limit
    _quote_around(book, fair, tick, P, plan, P["size"], P["size"])


HANDLERS = {"jump": _caldera, "level": _lumen, "mm": _oberon}


def _account(memory, fills):
    """Cash per product from our fills, and the position those fills imply (to spot lost fills)."""
    moved = {}
    for f in fills:
        st = memory["p"].setdefault(f["symbol"], {})
        sgn = 1 if f["side"] == "BUY" else -1
        st["cash"] = st.get("cash", 0.0) - sgn * f["size"] * f["price"]
        moved[f["symbol"]] = moved.get(f["symbol"], 0) + sgn * f["size"]
    return moved


def trade(snapshot, memory):
    if "lim" not in memory:   # init missing or failed
        memory.update({"n": 0, "lim": {}, "tick": {}, "p": {}})
    moved = _account(memory, snapshot.get("fills", []))
    resting = {}
    for o in snapshot.get("orders", []):
        resting.setdefault(o["symbol"], []).append(o)
    actions = []
    for sym, P in PARAMS.items():
        mine = resting.get(sym, [])
        try:
            book = snapshot["books"].get(sym)
            if not book or not book["bids"] or not book["asks"]:
                continue   # keep resting orders; nothing new
            limit = memory["lim"].get(sym) or {"CALDERA": 15, "LUMEN": 120, "OBERON": 60}[sym]
            tick = memory["tick"].get(sym) or {"CALDERA": 0.1, "LUMEN": 0.05, "OBERON": 0.02}[sym]
            pos = snapshot["positions"].get(sym, 0)
            st = memory["p"].setdefault(sym, {})
            # mark-to-mid PnL and the stop; fills lost with a failed call make the cash
            # unknown, and then the stop is switched off rather than trusted
            if st.get("pos", 0) + moved.get(sym, 0) != pos:
                st["bad"] = 1
            st["pos"] = pos
            pnl = st.get("cash", 0.0) + pos * _mid(book)
            st["peak"] = max(st.get("peak", 0.0), pnl)
            if P.get("stop") and not st.get("bad") and st["peak"] - pnl > P["stop"]:
                st["stopped"] = 1
            plan = Plan(pos, limit)
            if st.get("stopped"):
                if pos > 0:
                    plan.add("take", "SELL", book["bids"][0][0], min(pos, book["bids"][0][1]))
                elif pos < 0:
                    plan.add("take", "BUY", book["asks"][0][0], min(-pos, book["asks"][0][1]))
            else:
                HANDLERS[P["mode"]](sym, book, pos, limit, tick, P, st, plan)
            actions.extend(_execute(sym, plan, mine, memory))
        except Exception:
            if PARAMS.get("_strict"):
                raise
            actions.extend({"action": "cancel", "id": o["id"]} for o in mine)
    return actions[:50]


def _execute(sym, plan, resting, memory):
    """Cancel resting orders the plan doesn't want, send the rest; never exceeds the limit."""
    out = []
    keep_buy = keep_sell = 0
    wanted = list(plan.quotes)
    for o in resting:
        match = None
        for i, (side, price, size) in enumerate(wanted):
            if side == o["side"] and abs(price - o["price"]) < EPS and o["remaining"] <= size:
                match = i
                break
        if match is None:
            out.append({"action": "cancel", "id": o["id"]})
        else:
            side, price, size = wanted[match]
            if o["remaining"] == size:
                wanted.pop(match)
            else:
                wanted[match] = (side, price, size - o["remaining"])
            if side == "BUY":
                keep_buy += o["remaining"]
            else:
                keep_sell += o["remaining"]
    # the plan's room already counts every quote; kept orders are part of those quotes
    for side, price, size in plan.takes:
        memory["n"] += 1
        out.append({"action": "new", "symbol": sym, "side": side, "price": price, "size": size,
                    "tif": "IOC", "id": "o%d" % memory["n"]})
    for side, price, size in wanted:
        memory["n"] += 1
        out.append({"action": "new", "symbol": sym, "side": side, "price": price, "size": size,
                    "tif": "GTC", "id": "o%d" % memory["n"]})
    return out
