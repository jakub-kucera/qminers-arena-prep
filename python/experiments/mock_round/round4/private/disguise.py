"""The Varde Exchange: raw simulated sessions (private/raw/, Prosperity layout) into the round's JSON-lines sessions.

    python3 private/disguise.py      # public/data/session_1..3.jsonl and private/hidden/session_4..5.jsonl

Products renamed, prices in cents on a 5-cent tick (a raw tick of 1 is 5 cents), each print given an aggressor side
from the book shown at its step. Standard library only.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
NAMES = {"KELP_FLOW": "LUMEN", "HYDROGEL_PACK": "QUILL", "SQUID_INK": "SORREL"}
CENTS = 5  # cents per raw tick
SESSIONS = {"s1": ROUND / "public/data/session_1.jsonl", "s2": ROUND / "public/data/session_2.jsonl",
            "s3": ROUND / "public/data/session_3.jsonl", "s4": HERE / "hidden/session_4.jsonl", "s5": HERE / "hidden/session_5.jsonl"}


def convert(raw: Path, out: Path) -> None:
    books = defaultdict(dict)  # step -> sym -> {"bids", "asks"}
    with open(raw / "round1/prices_round_1_day_0.csv") as f:
        for row in csv.DictReader(f, delimiter=";"):
            sym = NAMES[row["product"]]
            side = {"bids": [], "asks": []}
            for k in (1, 2, 3):
                for name, key in (("bid", "bids"), ("ask", "asks")):
                    price, volume = row[f"{name}_price_{k}"], row[f"{name}_volume_{k}"]
                    if price and volume:
                        side[key].append([int(float(price)) * CENTS, abs(int(float(volume)))])
            books[int(row["timestamp"]) // 100][sym] = side
    prints = defaultdict(list)
    with open(raw / "round1/trades_round_1_day_0.csv") as f:
        for row in csv.DictReader(f, delimiter=";"):
            step, sym = int(row["timestamp"]) // 100, NAMES[row["symbol"]]
            px, book = int(float(row["price"])) * CENTS, books[int(row["timestamp"]) // 100].get(sym, {"bids": [], "asks": []})
            bid = book["bids"][0][0] if book["bids"] else None
            ask = book["asks"][0][0] if book["asks"] else None
            if ask is not None and px >= ask:
                aggressor = "buy"
            elif bid is not None and px <= bid:
                aggressor = "sell"
            else:
                mid = ((bid or px) + (ask or px)) / 2
                aggressor = "buy" if px > mid else "sell"
            prints[step].append({"sym": sym, "px": px, "qty": int(row["quantity"]), "aggressor": aggressor})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for step in sorted(books):
            f.write(json.dumps({"t": step, "book": books[step], "prints": prints.get(step, [])}, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    for name, out in SESSIONS.items():
        convert(HERE / "raw" / name, out)
        print(out)
