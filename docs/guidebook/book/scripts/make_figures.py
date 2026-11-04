"""The books' figures: every PNG in book/figures/, charts from book/data/ and the diagrams.

usage (from the repo root, a few seconds):
  uv run --group analysis python docs/guidebook/book/scripts/make_figures.py

Colours are arena.analysis's light THEME (checked with the dataviz skill's validator), categorical colours in slot
order. Each chart reads the CSV make_data.py wrote; nothing here computes a result.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parents[1]
DATA, OUT = HERE / "data", HERE / "figures"
sys.path.insert(0, str(HERE.parents[2] / "python"))
from arena.analysis import THEMES  # noqa: E402

T = THEMES["light"]
BLUE, ORANGE, GREEN, YELLOW, PINK = T["series"][:5]
plt.rcParams.update({
    "figure.facecolor": T["surface"], "axes.facecolor": T["surface"], "savefig.facecolor": T["surface"],
    "axes.edgecolor": T["axis"], "axes.labelcolor": T["secondary"], "xtick.color": T["secondary"], "ytick.color": T["secondary"],
    "text.color": T["ink"], "axes.grid": True, "grid.color": T["grid"], "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "legend.frameon": False, "figure.dpi": 100,
})


def read(name: str) -> list[dict]:
    with (DATA / f"{name}.csv").open() as file:
        return list(csv.DictReader(line for line in file if not line.startswith("#")))


def save(fig, name: str) -> None:
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"{name}.png")


def thousands(value, _=None) -> str:
    if abs(value) >= 1e6:
        return f"{value / 1e6:,.1f}M"
    return f"{value / 1000:,.0f}k" if abs(value) >= 1000 else f"{value:,.0f}"


def box(ax, x, y, text, w=0.2, h=0.09, color=None, size=9, weight="normal"):
    color = color or BLUE
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.01,rounding_size=0.015",
                                facecolor=color + "22", edgecolor=color, linewidth=1.2))
    ax.text(x, y, text, ha="center", va="center", fontsize=size, color=T["ink"], weight=weight)


def arrow(ax, a, b, color=None, style="-|>", rad=0.0, text=None):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=12, color=color or T["secondary"], linewidth=1.1,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.025, text, ha="center", fontsize=8, color=T["secondary"])


def canvas(width=8, height=4.2):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


# -- F1 the round's loop ------------------------------------------------------------------------------------------

def round_loop():
    fig, ax = canvas(9.5, 4.6)
    steps = [("the round's data\nand rules", 0.12, 0.78), ("diagnose:\nwhat is this market?", 0.37, 0.78),
             ("the bot:\nPARAMS for each product", 0.62, 0.78), ("backtest and grid\nunder two fill models", 0.87, 0.78),
             ("validate:\nsize, time, state", 0.87, 0.30), ("upload to\nthe portal", 0.62, 0.30),
             ("the portal's\ntwelve figures", 0.37, 0.30), ("calibrate: does our\nengine reproduce them?", 0.12, 0.30)]
    for k, (text, x, y) in enumerate(steps):
        box(ax, x, y, text, w=0.2, h=0.17, color=[BLUE, BLUE, GREEN, GREEN, YELLOW, ORANGE, ORANGE, PINK][k])
    for (_, x1, y1), (_, x2, y2) in zip(steps, steps[1:]):
        if y1 == y2:
            arrow(ax, (x1 + 0.1 * (1 if x2 > x1 else -1), y1), (x2 - 0.1 * (1 if x2 > x1 else -1), y2))
        else:
            arrow(ax, (x1, y1 - 0.085), (x2, y2 + 0.085))
    arrow(ax, (0.12, 0.385), (0.12, 0.695), color=PINK, text=None)
    ax.text(0.135, 0.54, "a fitted engine\nmakes the next\nbacktest honest", fontsize=8, color=PINK, va="center")
    arrow(ax, (0.62, 0.385), (0.62, 0.695), color=ORANGE)
    ax.text(0.635, 0.54, "the score says\nwhat to change", fontsize=8, color=ORANGE, va="center")
    ax.text(0.5, 0.06, "One round is five hours; the loop runs as often as there is time and submissions. "
            "The first lap should end in a validated upload by T+2:00.", ha="center", fontsize=8.5, color=T["secondary"])
    save(fig, "f01_round_loop")


# -- F2 an order book ---------------------------------------------------------------------------------------------

def order_book():
    rows = read("order_book")
    levels = [r for r in rows if r["side"] in ("bid", "ask")]
    extra = {r["side"]: float(r["price"]) for r in rows if r["side"] not in ("bid", "ask")}
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    prices = sorted({float(r["price"]) for r in levels})
    for r in levels:
        price, volume = float(r["price"]), int(r["volume"])
        sign = -1 if r["side"] == "bid" else 1
        ax.barh(price, sign * volume, height=0.7, color=BLUE if r["side"] == "bid" else ORANGE)
        ax.text(sign * (volume + 0.6), price, f"{volume} lots at {price:,.0f}", va="center", ha="left" if sign > 0 else "right", fontsize=9,
                bbox={"facecolor": T["surface"], "edgecolor": "none", "pad": 1})
    for name, color, label in (("mid", T["ink"], "mid"), ("wall_mid", GREEN, "wall mid")):
        ax.axhline(extra[name], color=color, linewidth=1, linestyle="--")
        ax.text(38, extra[name], f" {label} {extra[name]:,.1f}", va="center", ha="left", fontsize=9, color=color)
    ax.axvline(0, color=T["axis"], linewidth=1)
    ax.set_xlim(-38, 38)
    ax.set_ylim(min(prices) - 1.2, max(prices) + 1.2)
    ax.set_yticks(range(int(min(prices)) - 1, int(max(prices)) + 2))
    ax.set_xticks([-30, -20, -10, 0, 10, 20, 30], ["30", "20", "10", "0", "10", "20", "30"])
    ax.set_xlabel("lots resting at the price  (bids to the left, asks to the right)")
    ax.set_ylabel("price")
    ax.text(-36, max(prices) + 0.6, "bids: who will buy", color=BLUE, fontsize=9, weight="bold")
    ax.text(14, min(prices) - 0.9, "asks: who will sell", color=ORANGE, fontsize=9, weight="bold")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Prosperity 3's Kelp, round 1 day 0, timestamp {extra['timestamp']:,.0f}")
    save(fig, "f02_order_book")


# -- F3 the score's parts -----------------------------------------------------------------------------------------

def score_parts():
    rows = read("sessions")
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    xs = range(len(rows))
    for x, r in zip(xs, rows):
        cash, value, score = float(r["cash"]), float(r["position_value"]), float(r["score"])
        ax.bar(x - 0.2, cash, width=0.36, color=BLUE, label="cash (after fees)" if x == 0 else None)
        ax.bar(x + 0.2, value, width=0.36, color=ORANGE, label="position × mark" if x == 0 else None)
        ax.plot([x - 0.4, x + 0.4], [score, score], color=T["ink"], linewidth=2.2, label="score = their sum" if x == 0 else None)
        ax.text(x, max(cash, value, score) + 250, f"score €{score:,.2f}\nposition {int(r['end_position']):+d}", ha="center", fontsize=8.5)
    ax.axhline(0, color=T["axis"], linewidth=1)
    ax.set_xticks(list(xs), [r["session"] for r in rows])
    ax.set_ylabel("euros")
    ax.set_ylim(-6500, 7200)
    ax.legend(loc="lower left", ncol=3, fontsize=8.5)
    ax.set_title("The Varde rehearsal's three public sessions: two large parts, a small sum")
    save(fig, "f03_score_parts")


# -- F4 mid against wall mid --------------------------------------------------------------------------------------

def mid_and_wall():
    rows = read("mid_and_wall")
    t = [int(r["timestamp"]) / 100 for r in rows]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.step(t, [float(r["mid"]) for r in rows], where="post", color=T["muted"], linewidth=1, label="mid: jumps when a small order comes or goes")
    ax.step(t, [float(r["wall_mid"]) for r in rows], where="post", color=GREEN, linewidth=1.8, label="wall mid: moves when the large orders move")
    ax.set_xlabel("tick")
    ax.set_ylabel("price")
    ax.legend(loc="upper left", fontsize=8.5)
    ax.set_title("Prosperity 3's Kelp, the first 300 ticks of round 1 day 0")
    save(fig, "f04_mid_and_wall")


# -- F5 a round trip ----------------------------------------------------------------------------------------------

def round_trip():
    walk, fills = read("round_trip"), read("round_trip_fills")
    t = [int(r["step"]) for r in walk]
    fig, axes = plt.subplots(3, 1, figsize=(8, 6), sharex=True, gridspec_kw={"height_ratios": [1.4, 1, 1]})
    ax = axes[0]
    ax.step(t, [float(r["mid"]) for r in walk], where="post", color=T["muted"], linewidth=1, label="mid")
    for side, color, marker in (("buy", BLUE, "^"), ("sell", ORANGE, "v")):
        pts = [r for r in fills if r["side"] == side]
        ax.scatter([int(r["step"]) for r in pts], [float(r["price"]) for r in pts], color=color, marker=marker, s=18, zorder=3,
                   label=f"we {side}")
    ax.set_ylabel("price (€)")
    ax.legend(loc="lower left", ncol=3, fontsize=8)
    ax.set_title("A market maker's first 400 steps: LUMEN, the Varde rehearsal's session 1")
    axes[1].fill_between(t, [int(r["position"]) for r in walk], step="post", color=BLUE, alpha=0.35, linewidth=0)
    axes[1].axhline(0, color=T["axis"], linewidth=1)
    axes[1].set_ylabel("position (lots)")
    axes[2].plot(t, [float(r["pnl"]) for r in walk], color=GREEN, linewidth=1.6)
    axes[2].axhline(0, color=T["axis"], linewidth=1)
    axes[2].set_ylabel("PnL at the mid (€)")
    axes[2].set_xlabel("step")
    save(fig, "f05_round_trip")


# -- F6 income against copies -------------------------------------------------------------------------------------

def copies():
    rows = read("copies")
    fields = list(dict.fromkeys(r["field"] for r in rows))
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    colors = [BLUE, ORANGE, GREEN]
    for x, field in enumerate(fields):
        bots = [r for r in rows if r["field"] == field]
        width = 0.8 / len(bots)
        for k, r in enumerate(bots):
            pnl = float(r["pnl"])
            ax.bar(x - 0.4 + width * (k + 0.5), pnl, width=width * 0.92, color=colors[k])
            ax.text(x - 0.4 + width * (k + 0.5), pnl + 1200, thousands(pnl), ha="center", fontsize=8.5)
    together = [thousands(sum(float(r["pnl"]) for r in rows if r["field"] == field)) for field in fields]
    ax.set_xticks(range(len(fields)), [f"{name}\n(together {sum_})" for name, sum_ in
                                       zip(["our bot alone", "with one copy", "with two copies"], together)])
    ax.set_ylim(0, 82000)
    ax.yaxis.set_major_formatter(thousands)
    ax.set_ylabel("PnL over three days (credits)")
    ax.set_title("The same bot against copies of itself: Prosperity 3, round 1")
    save(fig, "f06_copies")


# -- F7 real against shuffled -------------------------------------------------------------------------------------

def shuffle():
    rows = read("shuffle")
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4))
    for ax, r in zip(axes, rows):
        real, shuffled = float(r["real"]), float(r["shuffled_mean"])
        bars = ax.bar([0, 1], [real, shuffled], color=[BLUE, T["muted"]], width=0.6)
        for bar, value in zip(bars, (real, shuffled)):
            ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:+,.0f}", ha="center", va="bottom" if value >= 0 else "top", fontsize=9)
        ax.axhline(0, color=T["axis"], linewidth=1)
        ax.set_xticks([0, 1], ["the real days", "the days shuffled\n(mean of 20 copies)"])
        ax.yaxis.set_major_formatter(thousands)
        unit = "cents" if r["market"] == "ABIDES" else "credits"
        ax.set_title(f"{r['market']}, {unit}   (p {float(r['p']):.2f})")
        ax.margins(y=0.15)
    axes[0].set_ylabel("the grid's best PnL (each panel its own scale)")
    save(fig, "f07_shuffle")


# -- F8 the smile window ------------------------------------------------------------------------------------------

def smile_window():
    rows = read("smile_window")
    w = [int(r["smile_window"]) for r in rows]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.plot(w, [float(r["pnl"]) for r in rows], marker="o", color=BLUE, linewidth=1.8, label="PnL over three days")
    ax.plot(w, [float(r["min_day"]) for r in rows], marker="o", color=ORANGE, linewidth=1.2, label="its worst day")
    for r in rows:
        ax.annotate(thousands(float(r["pnl"])), (int(r["smile_window"]), float(r["pnl"])), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=8.5)
    ax.axhline(0, color=T["axis"], linewidth=1)
    ax.set_xscale("log")
    ax.set_xticks(w, [f"{x:,}" for x in w])
    ax.minorticks_off()
    ax.yaxis.set_major_formatter(thousands)
    ax.set_xlabel("smile_window: the ticks the fair value averages over (log scale)")
    ax.set_ylabel("PnL (credits)")
    ax.legend(loc="lower right", fontsize=8.5)
    ax.margins(y=0.18)
    ax.set_title("One parameter, the fair's timescale: Prosperity 2's coconut coupon")
    save(fig, "f08_smile_window")


# -- F9 PnL under each fill model ---------------------------------------------------------------------------------

def fill_modes():
    rows = read("fill_modes")
    labels = {"all": "all\n(a print at or through\nour price fills us)", "worse": "worse\n(only a print\nthrough our price)",
              "none": "none\n(only the book\nwe can see)", "resting": "resting\n(orders stay and\nqueue behind others)"}
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    values = [float(r["pnl"]) for r in rows]
    bars = ax.bar(range(len(rows)), values, color=[BLUE, ORANGE, GREEN, YELLOW], width=0.62)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1200, f"{value:,.0f}", ha="center", fontsize=9)
    ax.set_xticks(range(len(rows)), [labels[r["mode"]] for r in rows], fontsize=8.5)
    ax.yaxis.set_major_formatter(thousands)
    ax.set_ylabel("PnL over three days (credits)")
    ax.set_title("One bot, the same three days, four answers: Prosperity 3, round 1")
    save(fig, "f09_fill_modes")


# -- F10 the grid under two fill models ---------------------------------------------------------------------------

def kelp_grid():
    rows = read("kelp_grid")
    makes = sorted({float(r["make_edge"]) for r in rows})
    takes = sorted({float(r["take_edge"]) for r in rows})
    cell = {(float(r["make_edge"]), float(r["take_edge"])): r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.9), sharey=True)
    values = [float(r[k]) for r in rows for k in ("pnl_all", "pnl_worse")]
    lo, hi = min(values), max(values)
    for ax, key, title in zip(axes, ("pnl_all", "pnl_worse"), ("under all", "under worse")):
        grid = [[float(cell[(m, t)][key]) for m in makes] for t in takes]
        best = max(rows, key=lambda r: float(r[key]))
        image = ax.imshow(grid, origin="lower", cmap=matplotlib.colors.LinearSegmentedColormap.from_list("ramp", T["ramp"]),
                          vmin=lo, vmax=hi, aspect="auto")
        for i, t in enumerate(takes):
            for j, m in enumerate(makes):
                value = grid[i][j]
                is_best = (m, t) == (float(best["make_edge"]), float(best["take_edge"]))
                ax.text(j, i, f"{value / 1000:.1f}" + ("\nbest" if is_best else ""), ha="center", va="center", fontsize=7.5,
                        color="white" if value > (lo + hi) / 2 else T["ink"], weight="bold" if is_best else "normal")
        ax.set_xticks(range(len(makes)), [f"{m:g}" for m in makes])
        ax.set_yticks(range(len(takes)), [f"{t:g}" for t in takes])
        ax.set_xlabel("make_edge: how far from fair we quote")
        ax.set_title(title)
        ax.grid(False)
    axes[0].set_ylabel("take_edge")
    bar = fig.colorbar(image, ax=axes, shrink=0.85, pad=0.02)
    bar.set_label("PnL over three days (thousands of credits)")
    bar.formatter = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}")
    bar.update_ticks()
    fig.suptitle("Kelp's two edges on Prosperity 3, round 1: the best cell moves with the fill model", x=0.06, ha="left",
                 fontsize=11, weight="bold")
    save(fig, "f10_kelp_grid")


# -- F11 days as folds --------------------------------------------------------------------------------------------

def folds():
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.0))
    for ax in axes:
        ax.set_xlim(0, 3)
        ax.set_ylim(-0.2, 3.2)
        ax.axis("off")
    for fold in range(3):
        y = 2.4 - fold
        for day in range(3):
            test = day == fold
            axes[0].add_patch(FancyBboxPatch((day + 0.05, y), 0.9, 0.55, boxstyle="round,pad=0.0,rounding_size=0.05",
                                             facecolor=ORANGE if test else BLUE + "55", edgecolor="none"))
            axes[0].text(day + 0.5, y + 0.27, f"day {day - 2}" + (": score" if test else ": fit"), ha="center", va="center",
                         fontsize=8.5, color="white" if test else T["ink"])
    axes[0].set_title("Leave one day out:\nfit on two days, score the third", fontsize=10)
    import random

    rng = random.Random(4)
    for fold in range(3):
        y = 2.4 - fold
        for k in range(60):
            test = rng.random() < 1 / 3
            axes[1].add_patch(plt.Rectangle((k * 0.05, y), 0.046, 0.55, facecolor=ORANGE if test else BLUE + "55", edgecolor="none"))
    axes[1].set_title("Shuffled k-fold over ticks:\nneighbours leak", fontsize=10)
    axes[1].text(1.5, -0.15, "a scored tick sits between fitted ones that share its price level and its regime",
                 ha="center", fontsize=8, color=T["secondary"])
    save(fig, "f11_folds")


# -- F12 calibrate's errors ---------------------------------------------------------------------------------------

def calibrate():
    rows = [r for r in read("calibrate") if r["error"] != ""]
    figures = list(dict.fromkeys(r["figure"] for r in rows))
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for label, color, marker, dy in (("ranked best", BLUE, "o", -0.15), ("closest on the fills", ORANGE, "D", 0.15)):
        pts = {r["figure"]: max(float(r["error"]) * 100, 0.01) for r in rows if r["setting"] == label}
        name = next(r["engine_setting"] for r in rows if r["setting"] == label)
        ax.scatter([pts[f] for f in figures], [k + dy for k in range(len(figures))], color=color, marker=marker, s=30, zorder=3,
                   label=f"{label}: {name.replace(', fee 0.001, max_actions 10', '')}")
    ax.axvline(5, color=T["loss"], linewidth=1.2, linestyle="--")
    ax.text(5.4, -0.45, "5%: calibrate's acceptance line", fontsize=8, color=T["loss"], va="center")
    ax.set_xscale("log")
    ax.set_xlim(0.01, 1000)
    ax.set_xticks([0.01, 0.1, 1, 10, 100, 1000], ["0.01%", "0.1%", "1%", "10%", "100%", "1000%"])
    ax.set_yticks(range(len(figures)), figures)
    ax.set_xlabel("how far our backtest is from the portal's figure (log scale)")
    ax.set_ylim(len(figures) - 0.5, -0.8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=8)
    ax.set_title("No setting fits every figure: calibrate on the Varde upload")
    save(fig, "f12_calibrate")


# -- F13 the architecture -----------------------------------------------------------------------------------------

def architecture():
    fig, ax = canvas(9, 5.4)
    box(ax, 0.13, 0.88, "the day's data\n(any layout)", w=0.2, h=0.1, color=T["muted"])
    box(ax, 0.13, 0.66, "format plug-in\nformats/<name>.py", w=0.2, h=0.1, color=YELLOW, weight="bold")
    box(ax, 0.13, 0.44, "Day of Ticks\n(model.py)", w=0.2, h=0.1, color=BLUE)
    box(ax, 0.5, 0.88, "bot file\nSTRATEGY · EXECUTION · ADAPTER", w=0.36, h=0.1, color=GREEN, weight="bold")
    box(ax, 0.5, 0.44, "engine.run_day\nmatching · fills · limits · marks", w=0.34, h=0.12, color=BLUE, weight="bold")
    box(ax, 0.5, 0.2, "Rust twin (--engine rust)\nthe same results, 40-130× faster", w=0.3, h=0.1, color=T["muted"], size=8)
    arrow(ax, (0.13, 0.83), (0.13, 0.71), text=None)
    arrow(ax, (0.13, 0.61), (0.13, 0.49), text=None)
    ax.text(0.145, 0.55, "load_days", fontsize=8, color=T["secondary"])
    arrow(ax, (0.23, 0.44), (0.33, 0.44))
    arrow(ax, (0.5, 0.83), (0.5, 0.5))
    ax.text(0.51, 0.68, "load_bot: the plug-in\nwraps the bot's call", fontsize=8, color=T["secondary"])
    arrow(ax, (0.2, 0.61), (0.36, 0.84), style="-|>", rad=-0.2)
    arrow(ax, (0.5, 0.38), (0.5, 0.25), style="<|-|>")
    tools = [("backtest", 0.88), ("grid · compare\nPBO DSR SPA StepM", 0.74), ("stress", 0.60), ("validate", 0.46),
             ("diagnose (no bot)", 0.32), ("calibrate ⇄ portal", 0.18)]
    for text, y in tools:
        box(ax, 0.87, y, text, w=0.22, h=0.1, color=ORANGE if "calibrate" not in text else PINK, size=8)
        if "diagnose" not in text:
            arrow(ax, (0.67, 0.44), (0.76, y), color=T["axis"])
    arrow(ax, (0.23, 0.42), (0.76, 0.32), color=T["axis"], rad=0.15)
    ax.text(0.5, 0.03, "The engine knows no format: a new exchange is a new plug-in and a new ADAPTER, nothing else.",
            ha="center", fontsize=8.5, color=T["secondary"])
    save(fig, "f13_architecture")


# -- F14 the day's timeline ---------------------------------------------------------------------------------------

# Short labels for RUNBOOK's times; a time RUNBOOK adds shows its own text, so the figure can't drift silently.
ROUND_LABELS = {0: "data, rules;\nnote the deadline", 0.25: "diagnose,\nlast bot\nbacktested", 0.5: "new products\ninto PARAMS",
                1: "grid under\ntwo fill models", 1.5: "stress;\nstop_loss", 2: "a validated\nbot uploaded",
                4.5: "stop changing\nthe strategy", 4.833: "final marked;\nhandover"}
WEEKEND_LABELS = {"arrival, registration": "reg.", "opening ceremony": "", "workshop": "work-\nshop", "playground (90 min)": "play-\nground",
                  "lunch": "", "dinner": "", "coffee break": "", "breakfast": "", "lunch, closing": "closing"}


def timeline():
    rows = read("timeline")
    fig, axes = plt.subplots(2, 1, figsize=(9, 4.6), gridspec_kw={"height_ratios": [1, 1.25]})
    ax = axes[0]
    for r in (r for r in rows if r["part"] == "weekend"):
        start, end, label = float(r["start"]), float(r["end"]), r["label"]
        is_round = label.startswith("round")
        meal = label in ("lunch", "dinner", "coffee break", "breakfast")
        color = BLUE if is_round else YELLOW if "playground" in label else T["grid"] if meal else T["muted"]
        ax.add_patch(plt.Rectangle((start, 0.2), end - start - 0.08, 0.6, facecolor=color + ("cc" if is_round else "88"), edgecolor="none"))
        ax.text((start + end) / 2, 0.5, label if is_round else WEEKEND_LABELS.get(label, label), ha="center", va="center",
                fontsize=8 if is_round else 7, color="white" if is_round else T["ink"])
    ax.set_xlim(8, 38)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    hours = list(range(8, 39, 2))
    ax.set_xticks(hours, [f"{'Sat' if h < 24 else 'Sun'} {h % 24:02d}" if h in (8, 24) else f"{h % 24:02d}" for h in hours], fontsize=8)
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.set_title("The weekend (ON_THE_DAY.md's timeline; the weights are the site's, unconfirmed)")
    ax = axes[1]
    steps = [(float(r["start"]), ROUND_LABELS.get(float(r["start"]), r["label"])) for r in rows if r["part"] == "round"]
    ax.plot([0, 5], [0, 0], color=T["axis"], linewidth=2)
    for k, (t, text) in enumerate(steps):
        color = ORANGE if t >= 2 else BLUE
        ax.scatter([t], [0], color=color, s=40, zorder=3)
        y = [0.5, -0.5, 0.95, -0.95][k % 4] if t < 1.6 else (0.55 if k % 2 == 0 else -0.55)
        ax.plot([t, t], [0, y * 0.6], color=color, linewidth=0.8)
        ax.text(t, y, text, ha="center", va="center", fontsize=7.5)
    ax.set_xlim(-0.3, 5.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_yticks([])
    ax.set_xticks([0, 1, 2, 3, 4, 5], ["T", "T+1h", "T+2h", "T+3h", "T+4h", "T+5h"], fontsize=8)
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.set_title("Each round (RUNBOOK.md, \"Each round\"), deadline at T+5h unless the dashboard says earlier")
    fig.tight_layout()
    save(fig, "f14_timeline")


# -- G15 the fill curve: what each fill rule would pay at each distance ------------------------------------------

def fill_curve():
    rows = [r for r in read("fill_curve") if float(r["distance"]) <= 2]
    d = [float(r["distance"]) for r in rows]
    lots = [float(r["lots"]) for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    ax = axes[0]
    ax.plot(d, [float(r["p_print"]) * 100 for r in rows], marker="o", color=BLUE, linewidth=1.8)
    ax.set_xlabel("distance from the wall mid (ticks)")
    ax.set_ylabel("ticks with a print there or beyond (%)")
    ax.set_title("How often the market reaches a quote")
    # a quote at d earns d a lot: under `all` from the lots printed at or beyond d, under `worse` only beyond it
    under_all = [x * q for x, q in zip(d, lots)]
    under_worse = [x * q for x, q in zip(d, lots[1:] + [0.0])]
    width = 0.18
    ax = axes[1]
    ax.bar([x - width / 2 for x in d], under_all, width=width, color=BLUE, label="all: a print at the quote fills it")
    ax.bar([x + width / 2 for x in d], under_worse, width=width, color=ORANGE, label="worse: only a print beyond it")
    for x, a, w in zip(d, under_all, under_worse):
        ax.text(x - width / 2, a + 0.01, f"{a:.2f}", ha="center", fontsize=7.5)
        ax.text(x + width / 2, w + 0.01, f"{w:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(d, [f"{x:g}" for x in d])
    ax.set_xlabel("distance from the wall mid (ticks)")
    ax.set_ylabel("edge earned a side a tick (credits)")
    ax.set_title("What a quote there could earn")
    ax.legend(loc="upper left", fontsize=7.5)
    fig.suptitle("Prosperity 3's Kelp, round 1: the market's offer, before any queue or rival", x=0.06, ha="left", fontsize=11,
                 weight="bold")
    fig.tight_layout()
    save(fig, "g15_fill_curve")


# -- G16 PnL against delay ----------------------------------------------------------------------------------------

def delay():
    rows = read("delay")
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    width = 0.36
    for k, (mode, color) in enumerate((("all", BLUE), ("worse", ORANGE))):
        pts = [r for r in rows if r["mode"] == mode]
        xs = [int(r["delay"]) + (k - 0.5) * width for r in pts]
        bars = ax.bar(xs, [float(r["pnl"]) for r in pts], width=width * 0.92, color=color, label=mode)
        for bar, r in zip(bars, pts):
            ax.text(bar.get_x() + bar.get_width() / 2, float(r["pnl"]) + 900, thousands(float(r["pnl"])), ha="center", fontsize=8.5)
    ax.set_xticks([0, 1, 2], ["on time", "one tick late", "two ticks late"])
    ax.yaxis.set_major_formatter(thousands)
    ax.set_ylabel("PnL over three days (credits)")
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_title("The same bot with its orders arriving late: Prosperity 3, round 1")
    save(fig, "g16_delay")


def main() -> int:
    for draw in (round_loop, order_book, score_parts, mid_and_wall, round_trip, copies, shuffle, smile_window, fill_modes,
                 kelp_grid, folds, calibrate, architecture, timeline, fill_curve, delay):
        draw()
    return 0


if __name__ == "__main__":
    sys.exit(main())
