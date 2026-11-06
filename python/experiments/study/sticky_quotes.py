"""Sticky quotes where every order costs a fee: keep a resting quote that is near where the plan wants it.

usage (from the repo root):
  uv run python -m experiments.study.sticky_quotes portal                       # the 2026-11-03 rehearsal's own portal
  uv run python -m experiments.study.sticky_quotes grid [--template PATH] 1 --data p3 --resting --grid STICKY=0,1,2 [arena.grid's options]

The template cancels a resting quote whenever the plan wants a different price, and posts a new one: on
P3 round 1 with orders resting it places about 61,500 orders over three days, so a fee of 2 credits an
order turns +66.6k into −56.5k, and TOPUP_MIN (posting a partly filled quote's shortfall only from a
minimum) recovers only 18k of it (IDEAS.md, "Top-ups where every order costs a fee"). Here `execute` keeps a
resting order whose price is within STICKY of the plan's quote on the same side, as if it were at the
quote's price: the quote stands where it is, a little stale, instead of costing a cancel and an order.
STICKY is in the data's price units (the rehearsal's tick is 5 cents, Prosperity's 1 credit); 0 is as is.

`portal`: the rehearsal's bot (results/template.py, whose EXECUTION is the template's) patched and scored by
the rehearsal's portal (its own matching, the order fee, the 100-print VWAP mark), with and without
TOPUP_MIN 10. `grid`: python/bots/template.py patched and written to a temporary file, then arena.grid on
it (the Python engine: the variant has no Rust twin), so STICKY and TOPUP_MIN can be gridded under any
--scenario, e.g. ofee=0.5. Standard library only.
"""

from __future__ import annotations

import itertools
import sys
import tempfile
from pathlib import Path

from experiments.study import top_ups

TEMPLATE = Path("python/bots/template.py")
ANCHOR = "    cancels = []\n    for order_id, price, quantity in resting:  # oldest first, as the queue has them\n"
PATCH = """    if STICKY:  # a resting order near the plan's quote on its side stands for it, at its own price
        for order_id, price, quantity in resting:
            key = (quantity > 0, price)
            if key in wanted:
                continue
            near = [k for k in wanted if k[0] == key[0] and abs(k[1] - price) <= STICKY and abs(quantity) <= abs(wanted[k])]
            if near:
                nearest = min(near, key=lambda k: abs(k[1] - price))
                wanted[key] = wanted.pop(nearest)
"""


def variant(source: str, sticky: int, topup_min: int = 0) -> str:
    if source.count(ANCHOR) != 1:
        raise SystemExit("execute changed: the patch's anchor is not there exactly once")
    source = source.replace(ANCHOR, PATCH + ANCHOR)
    return source + f"\n\nSTICKY = {sticky!r}\nTOPUP_MIN = {topup_min!r}\n"


TOPUP_ANCHOR = "        else:\n            cancels.append(order_id)\n    flying = ["
TOPUP = """        else:
            cancels.append(order_id)
    if TOPUP_MIN:  # the template's own rule since 2026-11-06, added to the rehearsal's older copy
        working = {(quantity > 0, price) for order_id, price, quantity in resting if order_id not in cancels}
        for key in working:
            if key in wanted and abs(wanted[key]) < TOPUP_MIN:
                wanted[key] = 0
    flying = ["""


def portal() -> int:
    exchange = top_ups.portal()
    source = top_ups.BOT.read_text()
    if source.count(TOPUP_ANCHOR) != 1:
        raise SystemExit("the rehearsal bot's execute changed: the top-up anchor is not there exactly once")
    source = source.replace(TOPUP_ANCHOR, TOPUP)
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        for sticky, topup_min in itertools.product((0, 5, 10, 20), (0, 10)):
            path = Path(folder) / f"sticky_{sticky}_{topup_min}.py"
            path.write_text(variant(source, sticky, topup_min))
            scores = []
            for which in ("public", "hidden"):
                metrics, runs = exchange.evaluate(path, which)
                placed = sum(sum(1 for row in r["orders_log"] if row[5] == "new") for r in runs.values())
                scores.append((metrics["score"], metrics["tradedVolume"], placed))
            rows.append((sticky, topup_min, scores))
    print("| STICKY (cents) | TOPUP_MIN | public score | lots | orders placed | hidden score | lots | orders placed |")
    print("|---|---|---|---|---|---|---|---|")
    for sticky, topup_min, ((ps, pv, po), (hs, hv, ho)) in rows:
        print(f"| {sticky} | {topup_min} | {ps:,.2f} | {pv:,} | {po:,} | {hs:,.2f} | {hv:,} | {ho:,} |")
    print("\neuros; the rehearsal's tick is 5 cents; STICKY 0 with TOPUP_MIN 0 is the bot as uploaded (367.61 public, 208.77 hidden)")
    return 0


def grid(argv: list[str]) -> int:
    """--template PATH (default python/bots/template.py; on the day python/bots/qminers/template.py), then arena.grid's options."""
    from arena import grid as arena_grid

    template = TEMPLATE
    if argv[:1] == ["--template"]:
        template, argv = Path(argv[1]), argv[2:]
    with tempfile.TemporaryDirectory() as folder:
        bot = Path(folder) / "sticky_quotes.py"
        bot.write_text(variant(template.read_text(), 0))
        return arena_grid.main([str(bot), *argv])


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["portal"]:
        return portal()
    if argv[:1] == ["grid"]:
        return grid(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
