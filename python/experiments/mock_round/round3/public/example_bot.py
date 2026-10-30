"""Minimal example bot for the Kestrel Bourse: joins the best bid and the best ask with one lot.

It keeps at most one order a side per instrument, cancels it when the touch moves away from its
price, stops quoting a side whose fill would take the position past the limit, and never sends more
than max_actions actions a step. It is not meant
to make money; it shows the interface (rules.md, section 3).
"""


def setup(ctx):
    ctx.n = 0  # client ids: "ex1", "ex2", ...
    ctx.mine = {}  # cid -> [symbol, side, price, lots left], the orders we believe are working


def step(ctx, view):
    for e in view["executions"]:
        o = ctx.mine.get(e["cid"])
        if o is not None:
            o[3] -= e["size"]
            if o[3] <= 0:
                del ctx.mine[e["cid"]]
    actions = []
    for sym, book in sorted(view["book"].items()):
        pos = view["position"].get(sym, 0)
        limit = ctx.instruments[sym]["limit"]
        dec = ctx.instruments[sym]["decimals"]
        want = {}
        if book["bid"] and pos + 1 <= limit:
            want["BUY"] = book["bid"][0][0]
        if book["ask"] and pos - 1 >= -limit:
            want["SELL"] = book["ask"][0][0]
        for side in ("BUY", "SELL"):
            have = [cid for cid, o in ctx.mine.items() if o[0] == sym and o[1] == side]
            keep = [cid for cid in have if side in want and abs(ctx.mine[cid][2] - want[side]) < 1e-9]
            need = len(have) - len(keep[:1]) + (side in want and not keep)
            if len(actions) + need > ctx.max_actions:
                continue  # no room this step: try again next step
            for cid in have:
                if cid not in keep[:1]:
                    actions.append({"type": "cancel", "cid": cid})
                    del ctx.mine[cid]
            if side in want and not keep:
                ctx.n += 1
                cid = f"ex{ctx.n}"
                ctx.mine[cid] = [sym, side, want[side], 1]
                actions.append({"type": "limit", "cid": cid, "symbol": sym, "side": side,
                                "price": f"{want[side]:.{dec}f}", "size": 1, "tif": "GTC"})
    return actions
