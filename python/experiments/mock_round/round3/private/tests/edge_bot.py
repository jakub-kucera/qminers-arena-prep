"""Exercises the portal's edge cases; it scores 0 with no fills. Per session the log should show:
- REJECTED 9: 5 bad actions at step 1, the 7-action list's extra one at step 2, the slow step 4,
  the non-list at step 5, the cancel of an unknown cid at step 6; and 1 slow step;
- EXCHANGE: the exception at step 3; one resting-cap refusal (4 orders far from the market on TALC
  at step 2, only 3 may work: e7 is refused); 4 "cancel ignored": step 2's cancels of e4 and e5 reach
  the exchange with (not after) the orders they cancel, step 7's cancel of e9 likewise, and step 8's
  cancel of e7, which the exchange refused.
"""
import time


def setup(ctx):
    pass


def step(ctx, view):
    n = view["step"]
    if n == 1:
        return [
            {"type": "limit", "cid": "", "symbol": "TALC", "side": "BUY", "price": "100.00", "size": 1},
            {"type": "limit", "cid": "e1", "symbol": "TALC", "side": "BUY", "price": "100.01", "size": 1},
            {"type": "limit", "cid": "e2", "symbol": "NOPE", "side": "BUY", "price": "100.00", "size": 1},
            {"type": "limit", "cid": "e3", "symbol": "TALC", "side": "BUY", "price": "100.00", "size": 0},
            ("limit", "TALC"),
        ]
    if n == 2:
        far = [{"type": "limit", "cid": f"e{k}", "symbol": "TALC", "side": "BUY", "price": "50.00", "size": 1}
               for k in range(4, 8)]
        return far + [{"type": "cancel", "cid": "e4"}, {"type": "cancel", "cid": "e5"}, {"type": "cancel", "cid": "e6"}]
    if n == 3:
        raise RuntimeError("boom")
    if n == 4:
        time.sleep(0.15)
        return []
    if n == 5:
        return "not a list"
    if n == 6:
        return [{"type": "cancel", "cid": "zz"}]
    if n == 7:
        return [{"type": "limit", "cid": "e9", "symbol": "BRAM", "side": "BUY", "price": "10.0", "size": 1},
                {"type": "cancel", "cid": "e9"}]
    if n == 8:
        return [{"type": "cancel", "cid": c} for c in ("e4", "e5", "e6", "e7", "e9")]
    return []
