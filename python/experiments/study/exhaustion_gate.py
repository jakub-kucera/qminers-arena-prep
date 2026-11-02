"""Does pulling a side whose best level is being exhausted pay? A dropped variant of the template, gridded.

usage (from the repo root): uv run python -m experiments.study.exhaustion_gate ROUND [arena.grid's options]
       uv run python -m experiments.study.exhaustion_gate 1 --data data/abides --grid 'PARAMS.ABM.gate_ber=None,0.1,0.2' \
           --set PARAMS.ABM.ber_window=50 --modes all,worse --scenario rest:resting,queue=prob --holdout last

Zhao & Linetsky's book exhaustion rate (references/wiki/sources/mm-adverse-selection-rl.md): over the
last `ber_window` calls, the market volume that hit a side's best (sells at or below the bid, buys at
or above the ask, each against the book of the call before) over the summed size at that best. Where
a side's rate reaches `gate_ber`, the variant pulls that side's quotes, as `gate_move` does after a
move (the larger side if both do). `experiments.day.quote_markouts`' "exhaustion" state is the same
measure on the template's fills; on the ABIDES days, fills after a high reading lose every day.

The variant is python/bots/template.py with the gate patched in at run time and written to a
temporary file, so it follows the committed template and needs no Rust twin (the grid runs on the
Python engine). The gate is not in the template: on ABIDES it substitutes for `gate_move` and adds
nothing on top of it, and on Prosperity it costs (IDEAS.md, "A book-exhaustion gate").
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from arena import grid

TEMPLATE = Path("python/bots/template.py")
PATCHES = (  # (anchor in the template, the text to put after it)
    ('    "gate_window": 20,\n', '    "gate_ber": None,\n    "ber_window": 20,\n'),
    ('        p = {**p, "pull": 1 if recent > 0 else -1}\n',
     '    if p["gate_ber"] is not None:\n'
     '        side = exhaustion_gate(market.trades.get(product, []), book, p, memory)\n'
     '        if side:\n'
     '            p = {**p, "pull": side}\n'),
)
GATE = '''

def exhaustion_gate(trades, book, p, memory) -> int:
    """-1 to pull the bid, 1 the ask, 0 neither: the side whose exhaustion rate over ber_window calls reaches gate_ber."""
    bid, ask = memory.get("eb_bid"), memory.get("eb_ask")
    trail = memory.setdefault("eb", [])
    if bid and ask:
        sells = sum(q for _, _, q, price in trades if price <= bid[0])
        buys = sum(q for _, _, q, price in trades if price >= ask[0])
        trail.append([sells, buys, bid[1], ask[1]])
        del trail[:-p["ber_window"]]
    if book.bids and book.asks:
        memory["eb_bid"], memory["eb_ask"] = list(book.bids[0]), list(book.asks[0])
    if len(trail) < p["ber_window"]:
        return 0
    bid_rate = sum(t[0] for t in trail) / max(sum(t[2] for t in trail), 1)
    ask_rate = sum(t[1] for t in trail) / max(sum(t[3] for t in trail), 1)
    if bid_rate >= p["gate_ber"] and bid_rate >= ask_rate:
        return -1
    if ask_rate >= p["gate_ber"]:
        return 1
    return 0
'''


def variant() -> str:
    """The template's source with the gate in it; fails if an anchor has moved."""
    source = TEMPLATE.read_text()
    for anchor, text in PATCHES:
        if source.count(anchor) != 1:
            raise SystemExit(f"the template changed: {anchor.strip()!r} is not there exactly once")
        source = source.replace(anchor, anchor + text)
    marker = "\n\ndef fair_value("
    if source.count(marker) != 1:
        raise SystemExit("the template changed: no single fair_value to put the gate before")
    return source.replace(marker, GATE + marker)


def main(argv: list[str] | None = None) -> int:
    with tempfile.TemporaryDirectory() as folder:
        bot = Path(folder) / "exhaustion_gate.py"
        bot.write_text(variant())
        return grid.main([str(bot), *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    sys.exit(main())
