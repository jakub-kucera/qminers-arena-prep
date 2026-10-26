"""Minimal example bot: joins the best bid and best ask with one lot on every instrument.

It keeps at most one resting order per side, moves it when the best price moves, and stops
quoting a side once the position would reach the limit. It is not meant to make money.
"""


def init(session):
    return {"limits": {s: v["position_limit"] for s, v in session["instruments"].items()}, "next": 0}


def trade(snapshot, memory):
    actions = []
    resting = {}
    for order in snapshot["orders"]:
        resting.setdefault((order["symbol"], order["side"]), []).append(order)

    for symbol, book in snapshot["books"].items():
        limit = memory["limits"][symbol]
        position = snapshot["positions"].get(symbol, 0)
        wanted = {}
        if book["bids"] and position + 1 <= limit:
            wanted["BUY"] = book["bids"][0][0]
        if book["asks"] and position - 1 >= -limit:
            wanted["SELL"] = book["asks"][0][0]

        for side in ("BUY", "SELL"):
            keep = False
            for order in resting.get((symbol, side), []):
                if not keep and side in wanted and abs(order["price"] - wanted[side]) < 1e-9:
                    keep = True
                else:
                    actions.append({"action": "cancel", "id": order["id"]})
            if side in wanted and not keep:
                memory["next"] += 1
                actions.append({
                    "action": "new", "symbol": symbol, "side": side,
                    "price": wanted[side], "size": 1, "id": f"ex{memory['next']}",
                })
    return actions
