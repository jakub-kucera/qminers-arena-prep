"""Does skewing on a product family's inventory, not only the product's own, pay? Guéant's Γ as a variant of the template, gridded.

usage (from the repo root): uv run python -m experiments.study.family_skew ROUND [arena.grid's options]
       uv run python -m experiments.study.family_skew 5 --data p4 --grid 'DEFAULTS.skew=0,2,5' \
           --grid 'DEFAULTS.family_weight=0,0.5,1' --modes all,worse --holdout last

Guéant's multi-asset market maker (references/wiki/concepts/many-products-architecture.md) moves each
product's quotes by Γ·q, the covariance of the products times the whole inventory vector, so a long
position in one member of a family skews the others' quotes too. The template skews on its own
position only (`skew`, `make` in STRATEGY). Here the target each product works toward is moved
against the rest of its family's positions: target − family_weight × Σ (the others' position over
their limit) × this product's limit, clamped to the limit. `skew` then quotes against it and `clear`
crosses toward it, so with family_weight 1 and equal limits, a member skews as if it held the
family's whole position.

Every product of the round is traded with the data's limit and DEFAULTS otherwise, as
`experiments.day.family_fills` does (the template as on products it wasn't tuned for); a family is the
products sharing the first word of their names. Its families on P4 round 5 build their inventories
together (fills cluster 4–6 times chance) but their prices move independently, or against each other
in two (IDEAS.md, "Fills arriving in several family members at once"), and `skew` on a product's own
inventory costs on Prosperity ("`skew` against Kelp's long position"), so this asks whether a
family's inventory is a risk worth giving up fills for.

The variant is python/bots/template.py with the family term patched in at run time and written to a
temporary file, so it follows the committed template and needs no Rust twin (the grid runs on the
Python engine). Results: IDEAS.md, "Skewing on correlated products' inventory too".
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from arena import grid
from arena.formats import FORMATS
from experiments.day.family_fills import families

TEMPLATE = Path("python/bots/template.py")
PATCHES = (  # (anchor in the template, the text to put after it)
    ('    "target": 0,  # position to hold: clear and skew work inventory toward it (e.g. long with a steady drift)\n',
     '    "family": None,  # the other members of this product\'s family (a list), for family_weight\n'
     '    "family_weight": 0.0,  # move target against the family\'s other positions, each over its limit, times this\n'),
    ('        p = {**p, "target": hedge_target(product, p, market)}\n',
     '    if p["family"] and p["family_weight"]:\n'
     '        held = getattr(market, "positions", {})\n'
     '        exposure = sum(held.get(other, 0) / PARAMS[other]["limit"] for other in p["family"] if other in PARAMS)\n'
     '        target = p["target"] - round(p["family_weight"] * exposure * p["limit"])\n'
     '        p = {**p, "target": max(-p["limit"], min(p["limit"], target))}\n'),
    ('        market = Market(books, read_trades(state), read_fills(state), state.timestamp)\n',
     '        market.positions = dict(state.position)\n'),
)


def variant(limits: dict[str, int]) -> str:
    """The template's source with the family term in it and every product in limits in PARAMS; fails if an anchor has moved."""
    source = TEMPLATE.read_text()
    for anchor, text in PATCHES:
        if source.count(anchor) != 1:
            raise SystemExit(f"the template changed: {anchor.strip()!r} is not there exactly once")
        source = source.replace(anchor, anchor + text)
    member_of = {product: members for members in families(sorted(limits)).values() for product in members}
    params = {product: {"limit": limit, "family": [m for m in member_of.get(product, []) if m != product]}
              for product, limit in sorted(limits.items())}
    return source + f"\n\nPARAMS.update({params!r})\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("round")
    parser.add_argument("--data", default="p4")
    parser.add_argument("--format", default="prosperity")
    known, _ = parser.parse_known_args(argv)
    fmt = FORMATS[known.format]
    days = fmt.load_days(fmt.resolve_data_dir(known.data), [known.round])
    limits = {product: limit for day in days for product, limit in day.limits.items()}
    with tempfile.TemporaryDirectory() as folder:
        bot = Path(folder) / "family_skew.py"
        bot.write_text(variant(limits))
        return grid.main([str(bot), *argv])


if __name__ == "__main__":
    sys.exit(main())
