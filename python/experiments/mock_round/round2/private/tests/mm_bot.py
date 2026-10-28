"""A simple sane market maker, to check that evaluate.py rewards quoting around a fair price.

Per product: fair = the mid of the largest bid and ask levels (the walls). It posts 4 lots a side
one tick inside the walls (never through fair +- 1 tick), skewed by inventory, and re-posts only
when the wanted price changes. It knows nothing about CORONA's basket or VANTA's trend.
"""


class Strategy:
    SIZE = 4

    def on_start(self, config):
        self.products = config["products"]
        self.ref = 0

    def _fair(self, book):
        if not book["bid"] or not book["ask"]:
            return None
        bid = max(book["bid"], key=lambda l: l[1])[0]
        ask = max(book["ask"], key=lambda l: l[1])[0]
        return (bid + ask) / 2

    def on_market(self, u):
        actions, mine = [], {}
        for ref, sym, qty, px in u["open"]:
            mine.setdefault((sym, qty > 0), []).append((ref, px))
        for sym, book in u["book"].items():
            fair = self._fair(book)
            if fair is None:
                continue
            tick, lim = self.products[sym]["tick"], self.products[sym]["limit"]
            pos = u["pos"].get(sym, 0)
            skew = pos / lim * 2 * tick
            best_bid, best_ask = book["bid"][0][0], book["ask"][0][0]
            bid = min(best_bid + tick, (int((fair - tick - skew) // tick)) * tick)
            ask = max(best_ask - tick, -(int(-(fair + tick - skew) // tick)) * tick)
            want = {}
            if pos + self.SIZE <= lim and bid < best_ask:
                want[True] = (bid, self.SIZE)
            if pos - self.SIZE >= -lim and ask > best_bid:
                want[False] = (ask, -self.SIZE)
            for side in (True, False):
                orders = mine.get((sym, side), [])
                if side in want and len(orders) == 1 and orders[0][1] == want[side][0]:
                    continue
                for ref, _ in orders:
                    actions.append(("pull", ref))
                if side in want:
                    self.ref += 1
                    actions.append(("post", sym, want[side][1], want[side][0], self.ref))
        return actions[:10]
