"""Turns the simulator's raw sessions (private/raw/<name>/, Prosperity layout) into the Kestrel
Bourse's download format.

    uv run python private/disguise.py          (from the qminers_arena repo root: arena must import)

Writes public/data/ (3 sessions) and private/hidden_data/ (2 sessions), each laid out as

    instruments.csv                     symbol,description,tick,decimals,limit
    <YYYY-MM-DD>/book.csv               clock,symbol,side,level,price,size
        level-by-level updates: a row only where (symbol, side, level) changed since the previous
        step; size 0 with an empty price = that level is now empty. The first step lists every level.
    <YYYY-MM-DD>/prints.csv             clock,symbol,price,size,aggressor
        the trades between other participants after the book of that clock was published and
        before the next step; aggressor BUY, SELL or empty (unknown).

Clock: "HH:MM:SS.mmm", the session opens at 10:00:00.000 and steps every 250 ms (6,000 steps).
Prices: decimal strings in points (TALC 2 decimals on a 0.05 grid, OPHIR 2 on 0.01, BRAM 1 on 0.5).

Price mapping (hundredths of a point, the portal's engine unit), per product:
    TALC   = (raw - 9995 + 2480 + LEVEL_SHIFT[session]) * 5      tick 0.05, level 124.00 + shift
    OPHIR  = raw - 2030 + 4180                                    tick 0.01
    BRAM   = (raw - 1000 + 300) * 50                              tick 0.50
Finally it reloads every written session with portal.load_session and checks it against the raw.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

from arena.formats import prosperity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

STEP_MS = 250
OPEN_MS = 10 * 3600 * 1000
RAW = {"TALC": "HYDROGEL_PACK", "OPHIR": "KELP", "BRAM": "LARGE_TICK"}
INSTRUMENTS = {  # symbol: description, tick (points), decimals
    "BRAM": ("barley malt, front month", "0.5", 1),
    "OPHIR": ("silver-copper spread note", "0.01", 2),
    "TALC": ("talc ore, warehouse lot", "0.05", 2),
}
# TALC's level in raw ticks moves by this much per session (0.05 points a raw tick): public 124.00,
# hidden 124.60 and 123.55, so a bot that hard-codes the public level is off on hidden days.
LEVEL_SHIFT = {"pub1": 0, "pub2": 0, "pub3": 0, "hid1": 12, "hid2": -9}
PUBLIC = {"pub1": "2026-09-14", "pub2": "2026-09-15", "pub3": "2026-09-16"}
HIDDEN = {"hid1": "2026-09-21", "hid2": "2026-09-22"}


def clock(n: int) -> str:
    ms = OPEN_MS + n * STEP_MS
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def mapper(symbol: str, session: str):
    if symbol == "TALC":
        return lambda p: (int(round(p)) - 9995 + 2480 + LEVEL_SHIFT[session]) * 5
    if symbol == "OPHIR":
        return lambda p: int(round(p)) - 2030 + 4180
    return lambda p: (int(round(p)) - 1000 + 300) * 50


def text(hundredths: int, decimals: int) -> str:
    return f"{hundredths / 100:.{decimals}f}"


def aggressor(book, px: float) -> str:
    if book is None:
        return ""
    if book.asks and px >= book.asks[0][0]:
        return "BUY"
    if book.bids and px <= book.bids[0][0]:
        return "SELL"
    mid = book.mid
    return "" if mid is None else ("BUY" if px > mid else "SELL" if px < mid else "")


def raw_day(name: str):
    (day,) = prosperity.load_days(prosperity.resolve_data_dir(str(HERE / "raw" / name)), ["1"])
    return day


def convert(sessions: dict[str, str], out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    limits = None
    for name, date in sessions.items():
        day = raw_day(name)
        limits = limits or {sym: day.limits[raw] for sym, raw in RAW.items()}
        maps = {sym: mapper(sym, name) for sym in RAW}
        folder = out / date
        folder.mkdir()
        prev: dict[tuple[str, str, int], tuple[int, int]] = {}
        with (folder / "book.csv").open("w", newline="") as fb, (folder / "prints.csv").open("w", newline="") as ft:
            wb, wt = csv.writer(fb), csv.writer(ft)
            wb.writerow(["clock", "symbol", "side", "level", "price", "size"])
            wt.writerow(["clock", "symbol", "price", "size", "aggressor"])
            for n, tick in enumerate(day.ticks):
                assert tick.timestamp == n * 100, (tick.timestamp, n)
                for sym in sorted(RAW):
                    book = tick.books.get(RAW[sym])
                    dec = INSTRUMENTS[sym][2]
                    for side, levels in (("bid", book.bids if book else ()), ("ask", book.asks if book else ())):
                        for k in range(3):
                            now = (maps[sym](levels[k][0]), int(levels[k][1])) if k < len(levels) else None
                            key = (sym, side, k + 1)
                            if prev.get(key) != now:
                                if now is None:
                                    wb.writerow([clock(n), sym, side, k + 1, "", 0])
                                else:
                                    wb.writerow([clock(n), sym, side, k + 1, text(now[0], dec), now[1]])
                                prev[key] = now
                for sym in sorted(RAW):
                    book = tick.books.get(RAW[sym])
                    dec = INSTRUMENTS[sym][2]
                    for tr in tick.trades.get(RAW[sym], []):
                        wt.writerow([clock(n), sym, text(maps[sym](tr.price), dec), tr.quantity, aggressor(book, tr.price)])
    with (out / "instruments.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "description", "tick", "decimals", "limit"])
        for sym, (desc, tick, dec) in sorted(INSTRUMENTS.items()):
            w.writerow([sym, desc, tick, dec, limits[sym]])


def check(sessions: dict[str, str], out: Path) -> None:
    """Every written session reloads (as the portal reads it) to the raw books and trades, mapped."""
    import portal

    for name, date in sessions.items():
        day = raw_day(name)
        got = portal.load_session(out, date)
        maps = {sym: mapper(sym, name) for sym in RAW}
        assert len(got.ticks) == len(day.ticks)
        for a, b in zip(got.ticks, day.ticks):
            for sym, raw in RAW.items():
                book = b.books.get(raw)
                want_b = tuple((maps[sym](p), v) for p, v in (book.bids if book else ()))
                want_a = tuple((maps[sym](p), v) for p, v in (book.asks if book else ()))
                assert a.books[sym].bids == want_b and a.books[sym].asks == want_a, (date, a.timestamp, sym)
                want_t = [(maps[sym](t.price), t.quantity) for t in b.trades.get(raw, [])]
                assert [(t.price, t.quantity) for t in a.trades.get(sym, [])] == want_t, (date, a.timestamp, sym)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(HERE))
    convert(PUBLIC, ROOT / "public" / "data")
    convert(HIDDEN, HERE / "hidden_data")
    check(PUBLIC, ROOT / "public" / "data")
    check(HIDDEN, HERE / "hidden_data")
    print("written and checked:", ROOT / "public" / "data", HERE / "hidden_data")
