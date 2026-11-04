"""Part V's figures: G22 one tick through the template (a diagram, its example row from data/one_tick.csv) and G23 the
parameters by group, coloured by their IDEAS.md verdict (data/parameters.csv).

Run from the repo root: uv run --group analysis python docs/guidebook/book/scripts/make_figures.py --only one_tick_diagram parameter_verdicts
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from make_figures import BLUE, GREEN, ORANGE, PINK, T, YELLOW, arrow, box, canvas, read, save


# -- G22 one tick through the template ----------------------------------------------------------------------------

def one_tick_diagram():
    tick = {r["key"]: r["value"] for r in read("one_tick")}
    fig, ax = canvas(11, 5.2)
    xs = [0.185 + k * 0.146 for k in range(6)]
    stages = [
        ("fair", "fair_value", BLUE,
         "the book;\nfair, wall_size,\nsmoothing", "the fair value\n(and memory's\nlast fair)",
         f"sized mid:\n{tick['fair']}"),
        ("take", "STRATEGY", BLUE,
         "the book's levels,\nthe fair, take_edge,\nroom under the limit", "Plan.takes;\nuses up\nbook levels",
         f"{tick['take']}\n(at or below\nfair − take_edge)"),
        ("clear", "STRATEGY", BLUE,
         "the plan's position\nif all fills, target,\nclear_edge", "more Plan.takes",
         f"{tick['clear']}\n(back to\nthe target, 0)"),
        ("make", "STRATEGY", BLUE,
         "what is left of\nthe book; make_edge,\nmake_inside, skew,\nmake_size", "Plan.quotes",
         tick["make"].replace("; ", ";\n")),
        ("EXECUTION", "execute, on_the_way,\nwent", ORANGE,
         "the plan, resting\norders, orders on\ntheir way, the cap", "cancels and new\norders (takes are\nimmediate-or-cancel)",
         f"nothing rests:\n{tick['cancels']} cancels,\n{tick['sent'].count(';') + 1} orders sent"),
        ("ADAPTER", "read_book, Trader.run", GREEN,
         "the exchange's state\n(TradingState);\nDELAY, ORDERS_REST", "the exchange's\nOrder and Cancel;\ntraderData",
         "filled:\n" + tick["filled"].replace("; ", ";\n").replace(" (book)", "") +
         f";\nposition {int(tick['position']):+d} → {int(tick['position_after'])}".replace("-", "−")),
    ]
    rows = [(0.64, "reads"), (0.45, "writes"), (0.2, f"this tick\n(Kelp, {int(tick['timestamp']):,})")]
    for y, label in rows:
        ax.text(0.012, y, label, ha="left", va="center", fontsize=8.5, color=T["secondary"], weight="bold")
    for k, (x, (name, where, color, reads, writes, example)) in enumerate(zip(xs, stages)):
        box(ax, x, 0.86, f"{name}\n\n", w=0.122, h=0.15, color=color, size=10, weight="bold")
        ax.text(x, 0.835, where, ha="center", va="top", fontsize=7, color=T["secondary"])
        ax.text(x, 0.64, reads, ha="center", va="center", fontsize=7.5, color=T["ink"])
        ax.text(x, 0.45, writes, ha="center", va="center", fontsize=7.5, color=T["ink"])
        ax.add_patch(FancyBboxPatch((x - 0.067, 0.09), 0.134, 0.22, boxstyle="round,pad=0.0,rounding_size=0.012",
                                    facecolor=T["midpoint"], edgecolor="none"))
        ax.text(x, 0.2, example, ha="center", va="center", fontsize=7.5, color=T["ink"])
        if k < 5:
            arrow(ax, (x + 0.063, 0.86), (xs[k + 1] - 0.063, 0.86))
    ax.plot([xs[0] - 0.06, xs[3] + 0.06], [0.955, 0.955], color=BLUE, linewidth=1)
    ax.text((xs[0] + xs[3]) / 2, 0.97, "STRATEGY: trade_product, one product at a time (a Plan)",
            ha="center", fontsize=8, color=BLUE)
    ax.text(0.5, 0.025, f"Prices in credits. The book: bids {tick['bids']}; asks {tick['asks']}. The two takes filled against "
            f"the book; the quotes met no trade and died at the tick's end (Prosperity's rule).", ha="center", fontsize=7.5,
            color=T["secondary"])
    save(fig, "g22_one_tick")


# -- G23 the parameters by verdict --------------------------------------------------------------------------------

VERDICT_COLOURS = {"kept": BLUE, "dropped here": ORANGE, "open": GREEN, "measured": YELLOW, "mixed": PINK}


def parameter_verdicts():
    rows = read("parameters")
    groups = list(dict.fromkeys(r["group"] for r in rows))
    layout = [groups[:3], groups[3:]]
    fig, axes = plt.subplots(2, 3, figsize=(11, 7.0), gridspec_kw={"height_ratios": [7.9, 10.9]})
    for top, (line, names) in enumerate(zip(axes, layout)):
        for ax, group in zip(line, names + [None] * (3 - len(names))):
            ax.set_xlim(0, 1)
            ax.axis("off")
            if group is None:
                continue
            entries = [r for r in rows if r["group"] == group]
            height = 7 if top == 0 else 10
            ax.set_ylim(height, -0.9)
            ax.text(0, -0.55, group, fontsize=10.5, weight="bold", color=T["ink"], va="center")
            for k, r in enumerate(entries):
                colour = VERDICT_COLOURS[r["verdict"]]
                ax.add_patch(FancyBboxPatch((0.0, k + 0.1), 1.0, 0.8, boxstyle="round,pad=0.0,rounding_size=0.015",
                                            facecolor=colour + "33", edgecolor=colour, linewidth=1.1, mutation_aspect=14))
                ax.text(0.03, k + 0.5, r["label"], fontsize=7.8, va="center", ha="left", color=T["ink"])
                ax.text(0.97, k + 0.5, r["verdict"], fontsize=7.2, va="center", ha="right", color=T["secondary"], style="italic")
    counts = {v: sum(r["verdict"] == v for r in rows) for v in VERDICT_COLOURS}
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=VERDICT_COLOURS[v] + "33", edgecolor=VERDICT_COLOURS[v]) for v in counts if counts[v]]
    fig.legend(handles, [f"{v} ({counts[v]})" for v in counts if counts[v]], loc="upper left", bbox_to_anchor=(0.06, 0.955), ncol=5,
               fontsize=8.5, frameon=False)
    fig.suptitle("The template's parameters, each coloured by the verdict of the IDEAS.md row that tested it", x=0.065, y=0.99,
                 ha="left", fontsize=11, weight="bold")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.9, bottom=0.02, wspace=0.08, hspace=0.12)
    save(fig, "g23_parameters")


FIGURES = [one_tick_diagram, parameter_verdicts]
