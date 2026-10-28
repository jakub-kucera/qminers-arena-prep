"""Turns the simulator's raw sessions (private/raw/<name>/, Prosperity layout) into the Halden
Exchange's download format.

    uv run python private/disguise.py          (run from the repo root, or anywhere with arena importable)

Writes public/data/ (3 sessions) and private/hidden_data/ (2 sessions), each laid out as

    products.json                       pip value, currency, and per product: tick (pips), limit, blurb
    sessions/<YYYY-MM-DD>.jsonl.gz      one JSON object per line, one line per step:
        {"n": 17, "ts": "2026-05-11T13:30:08.500Z",
         "book": {"AURIC": {"bid": [[3179, 21], ...], "ask": [[3182, 18], ...]}, ...},
         "tape": [["AURIC", 3182, 2, "B"], ...]}
    Prices are integer pips. "tape" lists the trades that printed since the previous line (the
    simulator's trades of raw tick n-1), with the aggressor "B", "S" or "?".

Price mapping (pips), per product:
    AURIC   = raw + 1180
    BRISA   = raw - 830
    VANTA   = (raw + 312) * 4                      (tick 4 pips)
    CORONA  = raw_X - 10000 + 24 + round(fA + 1180 + fB - 830)
              raw_X is the premium product's price, fA / fB the components' fundamentals (raw)
              LAG steps earlier, so CORONA's book is the premium book carried on top of AURIC +
              BRISA's true value as it was 2 s (4 steps) before.
"""

from __future__ import annotations

import csv
import gzip
import json
import shutil
from collections import defaultdict
from pathlib import Path

from arena.formats import prosperity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

PIP_VALUE = 0.25  # credits a pip
CURRENCY = "credits"
STEP_MS = 500
OPEN = (13, 30)  # 13:30:00.000 UTC
SHIFT = {"AURIC": 1180, "BRISA": -830}
PREMIUM = 24  # CORONA's mean premium over AURIC + BRISA, pips
LAG = 4  # steps CORONA's book trails its components' value
X_LEVEL = 10000
VANTA_SHIFT, VANTA_TICK = 312, 4
RAW = {"AURIC": "SQUID_INK", "BRISA": "KELP_FLOW", "CORONA": "RAINFOREST_RESIN", "VANTA": "LARGE_TICK"}
PRODUCTS = {
    "AURIC": {"tick": 1, "blurb": "spot metal"},
    "BRISA": {"tick": 1, "blurb": "spot metal"},
    "CORONA": {"tick": 1, "blurb": "index certificate on a metals basket"},
    "VANTA": {"tick": VANTA_TICK, "blurb": "front-month energy future"},
}
PUBLIC = {"pub1": "2026-05-11", "pub2": "2026-05-12", "pub3": "2026-05-13"}
HIDDEN = {"hid1": "2026-05-18", "hid2": "2026-05-19"}


def iso(date: str, n: int) -> str:
    ms = (OPEN[0] * 3600 + OPEN[1] * 60) * 1000 + n * STEP_MS
    return f"{date}T{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}Z"


def fundamentals(raw_dir: Path) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = defaultdict(dict)
    with (raw_dir / "round1" / "fundamental_round_1_day_0.csv").open() as file:
        for row in csv.DictReader(file, delimiter=";"):
            out[int(row["timestamp"])][row["product"]] = float(row["value"])
    return out


def aggressor(book, px: float) -> str:
    if book is None:
        return "?"
    if book.asks and px >= book.asks[0][0]:
        return "B"
    if book.bids and px <= book.bids[0][0]:
        return "S"
    mid = book.mid
    return "?" if mid is None else ("B" if px > mid else "S" if px < mid else "?")


def mapper(symbol: str, fund: dict[str, float]):
    if symbol in SHIFT:
        return lambda p: int(round(p)) + SHIFT[symbol]
    if symbol == "VANTA":
        return lambda p: (int(round(p)) + VANTA_SHIFT) * VANTA_TICK
    offset = round(fund["SQUID_INK"] + SHIFT["AURIC"] + fund["KELP_FLOW"] + SHIFT["BRISA"]) + PREMIUM - X_LEVEL
    return lambda p: int(round(p)) + offset


def convert(sessions: dict[str, str], out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / "sessions").mkdir(parents=True)
    limits = None
    for name, date in sessions.items():
        raw_dir = HERE / "raw" / name
        (day,) = prosperity.load_days(prosperity.resolve_data_dir(str(raw_dir)), ["1"])
        limits = limits or {sym: day.limits[raw] for sym, raw in RAW.items()}
        fund = fundamentals(raw_dir)
        lines = []
        tape: list = []  # trades of the previous raw tick, printed with this line
        for n, tick in enumerate(day.ticks):
            assert tick.timestamp == n * 100, (tick.timestamp, n)
            book_out = {}
            maps = {sym: mapper(sym, fund[max(0, n - LAG) * 100]) for sym in RAW}
            for sym, raw in RAW.items():
                book = tick.books.get(raw)
                f = maps[sym]
                book_out[sym] = {
                    "bid": [[f(p), v] for p, v in book.bids] if book else [],
                    "ask": [[f(p), v] for p, v in book.asks] if book else [],
                }
            lines.append(json.dumps({"n": n, "ts": iso(date, n), "book": book_out, "tape": tape}, separators=(",", ":")))
            tape = []
            for sym, raw in RAW.items():
                book = tick.books.get(raw)
                for tr in tick.trades.get(raw, []):
                    tape.append([sym, maps[sym](tr.price), tr.quantity, aggressor(book, tr.price)])
        # the last tick's trades happen after the final snapshot: not published (nothing can trade on them)
        with gzip.open(out / "sessions" / f"{date}.jsonl.gz", "wt", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")
    meta = {
        "exchange": "Halden Exchange",
        "currency": CURRENCY,
        "pip_value": PIP_VALUE,
        "step_ms": STEP_MS,
        "products": {sym: {"tick": PRODUCTS[sym]["tick"], "limit": limits[sym], "blurb": PRODUCTS[sym]["blurb"]} for sym in sorted(PRODUCTS)},
    }
    (out / "products.json").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    convert(PUBLIC, ROOT / "public" / "data")
    convert(HIDDEN, HERE / "hidden_data")
    print("written", ROOT / "public" / "data", HERE / "hidden_data")
