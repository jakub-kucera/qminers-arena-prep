"""Do EXECUTION's top-ups pay where every order placed costs a fee? Two variants, scored by the Varde rehearsal's own portal.

usage (from the repo root; the round's sessions rebuilt first if missing, python/experiments/mock_round/round4/README.md):
  uv run python -m experiments.study.top_ups

The template keeps a resting quote while the plan still wants at least its size and posts only the
difference, so each partial fill adds another small order at the same price: on the 2026-11-03
rehearsal up to 22 orders worked one product, and its portal charged 0.5 cents for every order placed,
28% of the bot's gross (TODO.md, "EXECUTION's top-ups multiply orders"). Two variants of `execute`,
patched into the rehearsal's own bot (results/template.py, whose EXECUTION is the template's) at run time:
  - TOPUP_MIN: a top-up goes out only once the shortfall at a price reaches this many lots (0: as is);
  - PARTS_MAX: once more than this many orders work one side at one price, cancel them all and post the
    whole size afresh, losing their places in the queue (None: as is).
Each variant is scored by the round's portal (private/portal.py), which is not our engine: its own
matching (half of each print for resting orders), its order fee, its 100-print VWAP mark. Public: the
three sessions a team sees; hidden: the two it is scored on. Standard library only.
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
import tempfile
from pathlib import Path

ROUND = Path("python/experiments/mock_round/round4")
BOT = ROUND / "results/template.py"
ANCHOR = """    for order_id, price, quantity in resting:  # oldest first, as the queue has them
        key = (quantity > 0, price)
        if abs(quantity) <= abs(wanted.get(key, 0)):
            wanted[key] -= quantity
        else:
            cancels.append(order_id)
"""
VARIANT = """    parts: dict[tuple[bool, int], list[tuple[int, int]]] = {}
    for order_id, price, quantity in resting:
        parts.setdefault((quantity > 0, price), []).append((order_id, quantity))
    for key, held in parts.items():  # PARTS_MAX: past it, the whole size afresh (the old orders cancelled below)
        if PARTS_MAX is not None and len(held) > PARTS_MAX and key in wanted:
            cancels_all = {order_id for order_id, _ in held}
            resting = [r for r in resting if r[0] not in cancels_all]
            cancels_fresh.extend(sorted(cancels_all))
""" + ANCHOR + """    working = {(q > 0, p) for order_id, p, q in resting if order_id not in cancels}
    for key in list(wanted):  # TOPUP_MIN: a shortfall smaller than this, where an order already works at the price, waits
        if TOPUP_MIN and key in working and abs(wanted[key]) < TOPUP_MIN:
            wanted[key] = 0
"""


def variant(topup_min: int, parts_max: int | None) -> str:
    source = BOT.read_text()
    anchors = (ANCHOR, "    cancels = []\n", "    return cancels, orders + posts\n")
    if any(source.count(anchor) != 1 for anchor in anchors):
        raise SystemExit("the bot's execute changed: the patch's anchors are not there exactly once")
    source = source.replace("    cancels = []\n", "    cancels = []\n    cancels_fresh: list[int] = []\n").replace(ANCHOR, VARIANT)
    source = source.replace("    return cancels, orders + posts\n", "    return cancels + cancels_fresh, orders + posts\n")
    return source + f"\n\nTOPUP_MIN = {topup_min!r}\nPARTS_MAX = {parts_max!r}\n"


def portal():
    if not list((ROUND / "public/data").glob("session_*.jsonl")):
        raise SystemExit("the round's sessions are missing: rebuild them as python/experiments/mock_round/round4/README.md says")
    spec = importlib.util.spec_from_file_location("varde_portal", ROUND / "private/portal.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    exchange = portal()
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        for topup_min, parts_max in itertools.product((0, 2, 5, 10), (None, 1, 2, 4)):
            path = Path(folder) / f"top_ups_{topup_min}_{parts_max}.py"
            path.write_text(variant(topup_min, parts_max))
            scores = []
            for which in ("public", "hidden"):
                metrics, runs = exchange.evaluate(path, which)
                placed = sum(sum(1 for row in r["orders_log"] if row[5] == "new") for r in runs.values())
                scores.append((metrics["score"], metrics["tradedVolume"], placed))
            rows.append((topup_min, parts_max, scores))
    print("| TOPUP_MIN | PARTS_MAX | public score | lots | orders placed | hidden score | lots | orders placed |")
    print("|---|---|---|---|---|---|---|---|")
    for topup_min, parts_max, ((ps, pv, po), (hs, hv, ho)) in rows:
        print(f"| {topup_min} | {parts_max} | {ps:,.2f} | {pv:,} | {po:,} | {hs:,.2f} | {hv:,} | {ho:,} |")
    print("\neuros; the bot as is is TOPUP_MIN 0, PARTS_MAX None (its public score 367.61, hidden 208.77)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
