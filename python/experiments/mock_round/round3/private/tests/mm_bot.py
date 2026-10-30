"""A simple sane market maker, to check that the portal rewards quoting around a fair price.

Per instrument: fair = the mid of the largest bid and ask levels (the walls). It quotes 3 lots a side
one tick inside the walls (never through fair +- 1 tick), skewed by inventory, and re-quotes a side
only when its wanted price changes. It tracks its own orders by client id (so a slow acknowledgement
doesn't make it double-post) and keeps within 6 actions a step, rotating which instrument goes first.
It knows nothing about TALC's level, OPHIR's informed flow or the hidden matching rules.
"""

SIZE = 3


def setup(ctx):
    ctx.n = 0
    ctx.mine = {}  # cid -> [symbol, side, price (hundredths), lots left]
    ctx.turn = 0


def _wall(levels):
    return max(levels, key=lambda l: l[1])[0]


def step(ctx, view):
    for e in view["executions"]:
        o = ctx.mine.get(e["cid"])
        if o is not None:
            o[3] -= e["size"]
            if o[3] <= 0:
                del ctx.mine[e["cid"]]
    syms = sorted(view["book"])
    ctx.turn = (ctx.turn + 1) % len(syms)
    actions = []
    for sym in syms[ctx.turn:] + syms[: ctx.turn]:
        book = view["book"][sym]
        if not book["bid"] or not book["ask"]:
            continue
        inst = ctx.instruments[sym]
        tick, lim, dec = round(inst["tick"] * 100), inst["limit"], inst["decimals"]
        fair = (round(_wall(book["bid"]) * 100) + round(_wall(book["ask"]) * 100)) / 2
        best_bid, best_ask = round(book["bid"][0][0] * 100), round(book["ask"][0][0] * 100)
        pos = view["position"].get(sym, 0)
        skew = pos / lim * 2 * tick
        bid = min(best_bid + tick, int((fair - tick - skew) // tick) * tick)
        ask = max(best_ask - tick, -int(-(fair + tick - skew) // tick) * tick)
        want = {}
        if pos + SIZE <= lim and bid < best_ask:
            want["BUY"] = bid
        if pos - SIZE >= -lim and ask > best_bid:
            want["SELL"] = ask
        for side in ("BUY", "SELL"):
            have = [cid for cid, o in ctx.mine.items() if o[0] == sym and o[1] == side]
            if side in want and len(have) == 1 and ctx.mine[have[0]][2] == want[side]:
                continue
            need = len(have) + (side in want)
            if len(actions) + need > ctx.max_actions:
                continue
            for cid in have:
                actions.append({"type": "cancel", "cid": cid})
                del ctx.mine[cid]
            if side in want:
                ctx.n += 1
                cid = f"m{ctx.n}"
                ctx.mine[cid] = [sym, side, want[side], SIZE]
                actions.append({"type": "limit", "cid": cid, "symbol": sym, "side": side,
                                "price": f"{want[side] / 100:.{dec}f}", "size": SIZE})
    return actions
