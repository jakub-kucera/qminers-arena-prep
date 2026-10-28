"""Reference bot for the answer key (PRIVATE): tests/mm_bot.py on AURIC and BRISA; CORONA quoted
around its wall mid moved by AURIC + BRISA's change over the last 4 steps (the lead); VANTA as a
trend follower (all in once the wall mid has moved 16+ pips in 600 steps, out below 8)."""
from collections import deque


class Strategy:
    SIZE = 4

    def on_start(self, config):
        self.products = config["products"]
        self.ref = 0
        self.vhist = deque(maxlen=601)
        self.ab = deque(maxlen=5)

    def _fair(self, book):
        if not book["bid"] or not book["ask"]:
            return None
        bid = max(book["bid"], key=lambda l: l[1])[0]
        ask = max(book["ask"], key=lambda l: l[1])[0]
        return (bid + ask) / 2

    def _quote(self, sym, book, fair, pos, mine, actions, size):
        tick, lim = self.products[sym]["tick"], self.products[sym]["limit"]
        skew = pos / lim * 2 * tick
        best_bid, best_ask = book["bid"][0][0], book["ask"][0][0]
        bid = min(best_bid + tick, (int((fair - tick - skew) // tick)) * tick)
        ask = max(best_ask - tick, -(int(-(fair + tick - skew) // tick)) * tick)
        want = {}
        if pos + size <= lim and bid < best_ask:
            want[True] = (bid, size)
        if pos - size >= -lim and ask > best_bid:
            want[False] = (ask, -size)
        for side in (True, False):
            orders = mine.get((sym, side), [])
            if side in want and len(orders) == 1 and orders[0][1] == want[side][0]:
                continue
            for ref, _ in orders:
                actions.append(("pull", ref))
            if side in want:
                self.ref += 1
                actions.append(("post", sym, want[side][1], want[side][0], self.ref))

    def on_market(self, u):
        actions, mine = [], {}
        for ref, sym, qty, px in u["open"]:
            mine.setdefault((sym, qty > 0), []).append((ref, px))
        b = u["book"]
        fa, fb, fc = self._fair(b["AURIC"]), self._fair(b["BRISA"]), self._fair(b["CORONA"])
        for sym in ("AURIC", "BRISA"):
            f = self._fair(b[sym])
            if f is not None:
                self._quote(sym, b[sym], f, u["pos"].get(sym, 0), mine, actions, self.SIZE)
        if None not in (fa, fb, fc):
            self.ab.append(fa + fb)
            lead = self.ab[-1] - self.ab[0]
            self._quote("CORONA", b["CORONA"], fc + lead, u["pos"].get("CORONA", 0), mine, actions, self.SIZE)
        # VANTA: follow a trend once the wall mid has moved 16+ pips over 600 steps
        fv = self._fair(b["VANTA"])
        if fv is not None:
            self.vhist.append(fv)
            pos = u["pos"].get("VANTA", 0)
            target = 0
            if len(self.vhist) == self.vhist.maxlen:
                move = fv - self.vhist[0]
                target = 40 if move >= 16 else -40 if move <= -16 else (pos if abs(move) >= 8 else 0)
            for ref, _ in mine.get(("VANTA", True), []) + mine.get(("VANTA", False), []):
                actions.append(("pull", ref))
            if target != pos and b["VANTA"]["bid"] and b["VANTA"]["ask"]:
                q = max(-10, min(10, target - pos))
                px = b["VANTA"]["ask"][0][0] if q > 0 else b["VANTA"]["bid"][0][0]
                self.ref += 1
                actions.append(("take", "VANTA", q, px, self.ref))
        return actions[:10]
