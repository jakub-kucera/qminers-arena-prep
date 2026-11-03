"""A minimal Varde Exchange strategy: quote 3 lots a tick inside the best on both sides of every product,
replacing last step's quotes each step."""


class Strategy:
    def __init__(self, limits):
        self.limits = limits

    def on_tick(self, state):
        actions = [{"type": "cancel", "id": order["id"]} for order in state["orders"]]
        for sym, book in state["book"].items():
            if not book["bids"] or not book["asks"]:
                continue
            bid, ask = book["bids"][0][0] + 5, book["asks"][0][0] - 5
            if bid >= ask:
                continue
            position, limit = state["position"].get(sym, 0), self.limits[sym]
            if position + 3 <= limit:
                actions.append({"type": "limit", "sym": sym, "px": bid, "qty": 3})
            if position - 3 >= -limit:
                actions.append({"type": "limit", "sym": sym, "px": ask, "qty": -3})
        return actions[:10]
