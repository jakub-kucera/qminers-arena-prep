"""Part I's figures (the guidebook's chapters 1 and 2): G2, the three data shapes becoming one Day of Ticks.

Run from the repo root: uv run --group analysis python docs/guidebook/book/scripts/make_figures.py --only data_shapes
"""

from __future__ import annotations

from matplotlib.patches import FancyBboxPatch

from make_figures import BLUE, GREEN, ORANGE, PINK, YELLOW, T, arrow, box, canvas, save


def _panel(ax, x, y, w, h, color, title, sample):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.01,rounding_size=0.015",
                                facecolor=color + "18", edgecolor=color, linewidth=1.2))
    ax.text(x - w / 2 + 0.012, y + h / 2 - 0.022, title, ha="left", va="top", fontsize=8.2, weight="bold", color=T["ink"])
    ax.text(x - w / 2 + 0.012, y + h / 2 - 0.075, sample, ha="left", va="top", fontsize=6.9, family="monospace",
            color=T["secondary"], linespacing=1.35)


def data_shapes():
    """G2: snapshots, prints with an aggressor flag and an event log, each through its plug-in into a Day of Ticks."""
    fig, ax = canvas(10, 5.6)
    rows = [
        (0.80, BLUE, "Snapshots (Prosperity)",
         "prices: day;timestamp;product;bid_price_1;...\n        0;400;KELP;2029;2;2028;23;...\n"
         "trades: timestamp;buyer;seller;symbol;...\n        500;;;KELP;SEASHELLS;2031.0;1",
         "prosperity.py", "each row is a tick's book;\nthe trades file joins it by timestamp"),
        (0.50, ORANGE, "Prints with an aggressor flag (Varde)",
         '{"t": 1, "book": {"LUMEN": {"bids":\n   [[10145, 5], ...], "asks": [...]}},\n'
         ' "prints": [{"sym": "LUMEN", "px": 10145,\n   "qty": 1, "aggressor": "sell"}, ...]}',
         "the round's plug-in\n(drill.py's pattern)", "each line is a tick; the flag makes\nthe buyer or the seller \"taker\""),
        (0.20, GREEN, "An event log (an exchange's own feed)",
         "add     17  buy  2029  5\nmodify  17            3\nexecute 17            2\ndelete  17",
         "orderlog.py", "replays every event;\nthe book after each step is a tick"),
    ]
    for y, color, title, sample, plugin, how in rows:
        _panel(ax, 0.18, y, 0.34, 0.235, color, title, sample)
        box(ax, 0.49, y + 0.035, plugin, w=0.16, h=0.085, color=YELLOW, size=8.3, weight="bold")
        ax.text(0.49, y - 0.035, how, ha="center", va="top", fontsize=7.1, color=T["secondary"], linespacing=1.25)
        arrow(ax, (0.35, y + 0.035), (0.41, y + 0.035), color=color)
        arrow(ax, (0.57, y + 0.035), (0.66, 0.56 + (y - 0.5) * 0.3), color=color)
    ax.text(0.49, 0.965, "format plug-ins: load_days", ha="center", fontsize=8.5, color=T["secondary"], weight="bold")
    ax.text(0.18, 0.965, "what the exchange publishes", ha="center", fontsize=8.5, color=T["secondary"], weight="bold")
    ax.text(0.82, 0.965, "what the engine reads (model.py)", ha="center", fontsize=8.5, color=T["secondary"], weight="bold")
    _panel(ax, 0.82, 0.57, 0.31, 0.46, BLUE, "a Day of Ticks",
           "Day\n  name, products, limits, info\n  ticks: [Tick, Tick, ...]\n\nTick\n  timestamp\n  books:  product -> Book\n"
           "          bids, asks: (price, lots)\n  trades: product -> [MarketTrade]\n          price, lots, buyer, seller\n"
           "  marks:  product -> price")
    box(ax, 0.82, 0.19, "engine.run_day and every tool:\nbacktest, grid, diagnose, calibrate", w=0.31, h=0.1, color=PINK, size=8.2)
    arrow(ax, (0.82, 0.335), (0.82, 0.245))
    ax.text(0.5, 0.015, "A new exchange costs a plug-in (and the bot's ADAPTER); nothing to the right of the plug-ins changes.",
            ha="center", fontsize=8.3, color=T["secondary"])
    save(fig, "g02_data_shapes")


FIGURES = [data_shapes]
