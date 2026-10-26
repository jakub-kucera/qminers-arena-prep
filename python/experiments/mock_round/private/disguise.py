"""Turns the simulator's raw days (Prosperity layout) into the mock exchange's download format.

    uv run python disguise.py

Reads private/raw_public and private/raw_hidden (made by generate.sh), writes public/data and
private/hidden_data, in the same layout:

    instruments.csv            symbol,tick_size,position_limit,currency
    <YYYY-MM-DD>/depth.csv     seq,time,symbol,side,level,price,size   (one row per visible level)
    <YYYY-MM-DD>/prints.csv    seq,time,symbol,price,size,aggressor    (trades after snapshot seq)

A raw price p (whole simulator ticks) becomes (p + SHIFT) * TICK, per instrument.
"""

from __future__ import annotations

import csv
import shutil
from decimal import Decimal
from pathlib import Path

from arena.formats import prosperity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# raw preset name -> (public symbol, tick size, shift in raw ticks)
MAPPING = {
    "HYDROGEL_PACK": ("LUMEN", Decimal("0.05"), -8240),
    "ROBOT_DISHES": ("CALDERA", Decimal("0.10"), -5000),
    "KELP_NOISY": ("OBERON", Decimal("0.02"), 1020),
}
CURRENCY = "CR"
OPEN_MS = 9 * 3600 * 1000  # 09:00:00.000
STEP_MS = 400  # one snapshot every 400 ms
PUBLIC_DATES = ["2026-03-03", "2026-03-04", "2026-03-05"]
HIDDEN_DATES = ["2026-03-06", "2026-03-09"]


def clock(seq: int) -> str:
    ms = OPEN_MS + seq * STEP_MS
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def price(product: str, raw: float) -> str:
    _, tick, shift = MAPPING[product]
    value = (Decimal(int(round(raw))) + shift) * tick
    assert value > 0, (product, raw)
    return str(value.quantize(tick))


def write_instruments(out: Path, limits: dict[str, int]) -> None:
    with (out / "instruments.csv").open("w", newline="") as file:
        w = csv.writer(file)
        w.writerow(["symbol", "tick_size", "position_limit", "currency"])
        for product in sorted(MAPPING, key=lambda p: MAPPING[p][0]):
            symbol, tick, _ = MAPPING[product]
            w.writerow([symbol, str(tick), limits[product], CURRENCY])


def aggressor(book, trade_price: float) -> str:
    if book.asks and trade_price >= book.asks[0][0]:
        return "BUY"
    if book.bids and trade_price <= book.bids[0][0]:
        return "SELL"
    mid = book.mid
    if mid is None:
        return ""
    return "BUY" if trade_price >= mid else "SELL"


def convert(raw_dir: Path, out: Path, dates: list[str]) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    days = prosperity.load_days(prosperity.resolve_data_dir(str(raw_dir)), ["1"])
    assert len(days) == len(dates), (len(days), dates)
    write_instruments(out, days[0].limits)
    order = sorted(MAPPING, key=lambda p: MAPPING[p][0])
    for day, date in zip(days, dates):
        folder = out / date
        folder.mkdir()
        with (folder / "depth.csv").open("w", newline="") as dfile, (folder / "prints.csv").open("w", newline="") as pfile:
            dw, pw = csv.writer(dfile), csv.writer(pfile)
            dw.writerow(["seq", "time", "symbol", "side", "level", "price", "size"])
            pw.writerow(["seq", "time", "symbol", "price", "size", "aggressor"])
            for seq, tick in enumerate(day.ticks):
                assert tick.timestamp == seq * 100, (tick.timestamp, seq)
                t = clock(seq)
                for product in order:
                    symbol = MAPPING[product][0]
                    book = tick.books.get(product)
                    if book is not None:
                        for side, levels in (("BID", book.bids), ("ASK", book.asks)):
                            for k, (px, vol) in enumerate(levels, 1):
                                dw.writerow([seq, t, symbol, side, k, price(product, px), vol])
                    for trade in tick.trades.get(product, []):
                        pw.writerow([seq, t, symbol, price(product, trade.price), trade.quantity, aggressor(book, trade.price)])


if __name__ == "__main__":
    convert(HERE / "raw_public", ROOT / "public" / "data", PUBLIC_DATES)
    convert(HERE / "raw_hidden", HERE / "hidden_data", HIDDEN_DATES)
    print("written", ROOT / "public" / "data", HERE / "hidden_data")
