"""Part III's data (the guidebook's chapters 8 and 9): G11 a basket's spread, G12 the voucher smile, G13 the rival
field, and the adversaries' table chapter 9 quotes. Run through make_data.py (--only NAME).
"""

from __future__ import annotations

import ast
import re
import statistics as st

from make_data import ROOT, run, write

BASKET, LEGS = "PICNIC_BASKET1", {"CROISSANTS": 6, "JAMS": 3, "DJEMBES": 1}


def _template_entry(product: str) -> dict:
    """A product's PARAMS entry as written in the template (its literal dict, read without running the bot)."""
    text = (ROOT / "python/bots/template.py").read_text()
    at = text.index(f'"{product}": {{')
    start = text.index("{", at)
    depth = 0
    for k, char in enumerate(text[start:], start=start):
        depth += char == "{"
        depth -= char == "}"
        if depth == 0:
            return ast.literal_eval(text[start:k + 1])
    raise ValueError(product)


def basket_spread() -> None:
    """G11: PICNIC_BASKET1's wall mid against 6 Croissants + 3 Jams + 1 Djembes (their wall mids) on P3 round 2's three
    days, every 10th tick, and each day's spread statistics over every tick, with the template's level and band."""
    from arena.formats import prosperity

    days = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["2"])
    rows, stats = [], []
    for day in days:
        spreads = []
        for k, tick in enumerate(day.ticks):
            books = [tick.books.get(p) for p in (BASKET, *LEGS)]
            if any(b is None or b.wall_mid is None for b in books):
                continue
            basket = books[0].wall_mid
            legs = sum(w * b.wall_mid for w, b in zip(LEGS.values(), books[1:]))
            spreads.append(basket - legs)
            if k % 10 == 0:
                rows.append([day.name, tick.timestamp, basket, legs, basket - legs])
        stats.append([day.name, round(st.fmean(spreads), 2), round(st.pstdev(spreads), 2), spreads[0], len(spreads)])
    entry = _template_entry(BASKET)
    source = "arena.formats.prosperity.load_days(p3, ['2']): PICNIC_BASKET1's wall mid less 6 CROISSANTS + 3 JAMS + 1 DJEMBES (wall mids)"
    write("basket_spread", source + ", every 10th tick", ["day", "timestamp", "basket", "legs", "spread"], rows)
    write("basket_days", source + f"; every tick; the template's PARAMS level {entry['level']}, level_band {entry['level_band']}",
          ["day", "mean", "sd", "open", "ticks", "level", "level_band"], [s + [entry["level"], entry["level_band"]] for s in stats])


def voucher_smile() -> None:
    """G12: P3's volcanic vouchers' implied vol against moneyness m = ln(K/S)/sqrt(T) on their five distinct days
    (experiments.day.p3_smile's points, every 100th tick), and its parabola fitted on all five days and leaving each out."""
    from experiments.day import p3_smile

    days = p3_smile.load()
    per_day = {day.name: p3_smile.points(day) for day in days}
    rows = [[name, r["K"], round(r["m"], 5), round(r["v"], 5)] for name, pts in per_day.items() for r in pts
            if r["v"] is not None and r["t"] % 10_000 == 0]
    write("voucher_smile", "experiments.day.p3_smile.points on P3's five distinct voucher days (3-0 3-1 3-2 4-3 5-4), "
          "ticks at multiples of 10,000; strikes with time value", ["day", "strike", "m", "v"], rows)
    fits = [["all five days", *p3_smile.fit_parabola([r for pts in per_day.values() for r in pts])]]
    for name in per_day:
        fits.append([f"without {name}", *p3_smile.fit_parabola([r for other, pts in per_day.items() if other != name for r in pts])])
    write("voucher_smile_fit", "experiments.day.p3_smile.fit_parabola over every tick: v = a m^2 + b m + c",
          ["fit", "a", "b", "c"], [[f[0], *(round(x, 4) for x in f[1:])] for f in fits])


def _tables(output: str) -> list[list[list[str]]]:
    """Every Markdown table in a command's output, as rows of cells (the rule row left out)."""
    tables, current = [], []
    for line in output.splitlines() + [""]:
        if line.startswith("|"):
            cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("-: "):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables


def rival_field() -> None:
    """G13: our PnL per candidate setting in each field of rival archetypes, per tick and resting."""
    output = run(["-m", "experiments.day.rival_field", "--engine", "rust"])
    rows = []
    for mode, table in zip(("per tick", "resting"), _tables(output)):
        header = table[0]
        for cells in table[1:]:
            if cells[0] == "best reply":
                continue
            kelp, resin = re.findall(r"make_edge ([\d.]+)", cells[0])
            for field, value in zip(header[1:], cells[1:]):
                rows.append([mode, float(kelp), float(resin), field, float(value)])
    write("rival_field", "uv run python -m experiments.day.rival_field --engine rust: P3 round 1, all, thousands of credits",
          ["mode", "kelp_make_edge", "resin_make_edge", "field", "pnl_k"], rows)


def adversaries() -> None:
    """Chapter 9's adversaries: the template as committed and with every product on wall_mid, alone and against each rival."""
    output = run(["-m", "experiments.day.adversaries", "--data", "p3", "--days", "1", "--engine", "rust"])
    rows = []
    for cells in _tables(output)[0][1:]:
        variant, rival, total, change, theirs, against = cells
        found = re.match(r"([-\d.]+) \(([-\d.]+) / ([-\d.]+)\)", total)
        units, value = (against.split(", ") + [""])[:2] if against != "-" else ("", "")
        rows.append([variant, rival, float(found[1]), float(found[2]), float(found[3]), float(change),
                     "" if theirs == "-" else float(theirs), units.replace(",", ""), value.replace("+", "")])
    write("adversaries", "uv run python -m experiments.day.adversaries --data p3 --days 1 --engine rust: --resting, all, thousands of credits",
          ["variant", "rival", "total", "kelp", "resin", "change", "rival_pnl", "units_with_rival", "their_value_50"], rows)


def level_mode() -> None:
    """Chapter 8's level mode: P4 Hydrogel and Velvetfruit, the held-out total and the level estimated each way
    (experiments.day.p4_level_template, the four distinct days of P4 rounds 3-4)."""
    output = run(["-m", "experiments.day.p4_level_template", "--engine", "rust"])
    rows, product = [], None
    for line in output.splitlines():
        if line and not line.startswith(" "):
            product = line.strip()
        found = re.match(r"\s+(total over the held-out days|CHOSEN \(tuned and levelled on all four days\):|other days' mean, level_weight None|"
                         r"the day so far \(\"day\"\))\s+([-\d.]+)k", line)
        if found and product:
            label = {"total over the held-out days": "held out (nested leave-one-day-out)", "the day so far (\"day\")": "level from the day so far",
                     "other days' mean, level_weight None": "level from the other days"}.get(found[1], "in-sample (all four days)")
            rows.append([product, label, float(found[2])])
    write("level_mode", "uv run python -m experiments.day.p4_level_template --engine rust: P4 rounds 3-4's four distinct days, "
          "thousands of credits over the four", ["product", "setting", "pnl_k"], rows)


def zoo() -> None:
    """Chapter 9's zoo: every zoo bot alone, head to head with the template, inside arena.sim and in the field of 13."""
    output = run(["-m", "experiments.study.zoo", "--engine", "rust"])
    rows = []
    for cells in _tables(output)[0][1:]:
        bot, alone, worse, h2h, in_sim, field, errors, breaches, _ = cells
        theirs, ours = (h2h.split(" / ") + [""])[:2] if h2h != "-" else ("", "")
        rows.append([bot, alone, worse, theirs, ours, in_sim, "" if field == "-" else field, errors, breaches])
    write("zoo", "uv run python -m experiments.study.zoo --engine rust: P3 round 1, thousands of credits; the field of 13 leaves out "
          "the local models", ["bot", "alone_all", "alone_worse", "h2h_bot", "h2h_template", "in_sim", "in_field", "errors", "breaches"], rows)


STEPS = {"zoo": zoo, "basket_spread": basket_spread, "voucher_smile": voucher_smile, "rival_field": rival_field, "adversaries": adversaries,
         "level_mode": level_mode}
