"""Minimal example strategy for the Halden Exchange: joins the best bid and best ask with one lot.

It keeps at most one resting order a side per product, pulls it when the touch moves away from it,
and stops quoting a side whose fill would take the position past the limit. It is not meant to
make money; it shows the interface.
"""


class Strategy:
    def on_start(self, config):
        self.limits = {sym: p["limit"] for sym, p in config["products"].items()}
        self.next_ref = 0

    def on_market(self, update):
        actions = []
        mine = {}
        for ref, sym, qty, price in update["open"]:
            mine.setdefault((sym, qty > 0), []).append((ref, price))
        for sym, book in update["book"].items():
            pos = update["pos"].get(sym, 0)
            want = {}
            if book["bid"] and pos + 1 <= self.limits[sym]:
                want[True] = book["bid"][0][0]
            if book["ask"] and pos - 1 >= -self.limits[sym]:
                want[False] = book["ask"][0][0]
            for is_buy in (True, False):
                keep = False
                for ref, price in mine.get((sym, is_buy), []):
                    if not keep and want.get(is_buy) == price:
                        keep = True
                    else:
                        actions.append(("pull", ref))
                if is_buy in want and not keep:
                    self.next_ref += 1
                    actions.append(("post", sym, 1 if is_buy else -1, want[is_buy], self.next_ref))
        return actions[:10]
