"""The guidebook's Part IV figures (chapters 11 to 13): G17 the permutation test's null, G18 CSCV's splits (a
diagram), G20 the leader's chance of first against its stake. make_figures.py draws them (--only NAME)."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from make_figures import BLUE, GREEN, ORANGE, T, YELLOW, arrow, canvas, read, save, thousands


# -- G17 the permutation test's null, with the real search marked ------------------------------------------------

def g17_permutation():
    rows = read("permutation_null")
    grids = [("Kelp", "Kelp's make_edge × take_edge, 64 cells\nProsperity 3, round 1"),
             ("Hydrogel", "Hydrogel's level_band × clear_edge, 20 cells\nProsperity 4, rounds 3 and 4")]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    for ax, (name, title) in zip(axes, grids):
        mine = [r for r in rows if r["grid"] == name]
        real = next(r for r in mine if r["run"] == "real")
        copies = [r for r in mine if r["run"] == "copy"]
        for y, (key, label, pkey) in enumerate((("best", "the best cell's PnL", "p_best"), ("lift", "its lift over\nthe median cell", "p_lift"))):
            values = [float(r[key]) for r in copies]
            ax.scatter([float(real[key])], [1 - y], s=130, marker="D", facecolor="none", edgecolor=BLUE, linewidth=2, zorder=2,
                       label="the real days" if y == 0 else None)
            ax.scatter(values, [1 - y] * len(values), s=30, color=T["muted"], alpha=0.8, zorder=3, edgecolor=T["surface"], linewidth=0.6,
                       label="19 copies, ticks shuffled" if y == 0 else None)
            ax.annotate(f"real {thousands(float(real[key]))}  ·  p {float(real[pkey]):.2f}", (float(real[key]), 1 - y), textcoords="offset points",
                        xytext=(0, 11), ha="center", fontsize=8.5, color=T["ink"])
            ax.text(-0.02, 1 - y, label, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8.5, color=T["secondary"])
        if name == "Hydrogel":
            top = max(float(r["best"]) for r in copies)
            ax.annotate(f"one copy at {thousands(top)}, {1 - top / float(real['best']):.1%} below", (top, 1), textcoords="offset points",
                        xytext=(-4, -16), ha="right", fontsize=7.5, color=T["secondary"])
        ax.set_yticks([])
        ax.set_ylim(-0.6, 1.7)
        ax.spines["left"].set_visible(False)
        ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_formatter(thousands)
        ax.set_xlabel("PnL of the products the grid sets (credits)")
        ax.set_title(title, fontsize=9.5)
        ax.margins(x=0.12)
    axes[0].legend(loc="lower left", fontsize=8, ncol=2, bbox_to_anchor=(0.0, -0.02))
    fig.suptitle("The permutation test: is the real search's result unusual among searches of shuffled days?", x=0.02, ha="left",
                 fontsize=11, weight="bold")
    fig.tight_layout(w_pad=6)
    save(fig, "g17_permutation_null")


# -- G18 CSCV's splits (a diagram) --------------------------------------------------------------------------------

def g18_cscv():
    fig, ax = canvas(9.5, 4.8)
    blocks, x0, w = 6, 0.05, 0.065
    days = ["day 1", "day 1", "day 2", "day 2", "day 3", "day 3"]
    ax.text(x0, 0.93, "1. Cut the days into blocks (here 6; the Kelp grid used 18, six a day)", fontsize=9, color=T["ink"], weight="bold")
    for b in range(blocks):
        ax.add_patch(FancyBboxPatch((x0 + b * w, 0.83), w - 0.008, 0.06, boxstyle="round,pad=0,rounding_size=0.006",
                                    facecolor=T["grid"], edgecolor=T["axis"], linewidth=0.8))
        ax.text(x0 + b * w + (w - 0.008) / 2, 0.86, f"{b + 1}", ha="center", va="center", fontsize=8)
        if b % 2 == 0:
            ax.text(x0 + b * w + w - 0.004, 0.795, days[b], ha="center", fontsize=7.5, color=T["secondary"])
    ax.text(x0, 0.71, "2. Every way to split them into two halves (6 blocks: 20 ways; 18 blocks: 48,620, of which 4,000 are drawn)",
            fontsize=9, color=T["ink"], weight="bold")
    ax.text(0.55, 0.64, "3. The best cell on the training half: its rank\n    among all the cells on the other half", fontsize=9,
            color=T["ink"], weight="bold", va="center")
    splits = [((0, 2, 4), 0.86), ((0, 1, 2), 0.71), ((1, 3, 5), 0.38), ((2, 4, 5), 0.93)]
    for k, (train, rank) in enumerate(splits):
        y = 0.52 - k * 0.11
        for b in range(blocks):
            inside = b in train
            ax.add_patch(FancyBboxPatch((x0 + b * w, y), w - 0.008, 0.07, boxstyle="round,pad=0,rounding_size=0.006",
                                        facecolor=BLUE if inside else ORANGE + "55", edgecolor="none"))
            ax.text(x0 + b * w + (w - 0.008) / 2, y + 0.035, "fit" if inside else "test", ha="center", va="center", fontsize=7,
                    color="white" if inside else T["ink"])
        arrow(ax, (x0 + blocks * w + 0.01, y + 0.035), (0.54, y + 0.035), color=T["axis"])
        ax.text(0.5, y + 0.06, "pick the best", ha="center", fontsize=7, color=T["secondary"])
        # the rank bar: 0 worst, 1 best, the median marked
        left, width = 0.58, 0.3
        ax.plot([left, left + width], [y + 0.035] * 2, color=T["grid"], linewidth=6, solid_capstyle="round")
        ax.plot([left + width / 2] * 2, [y + 0.005, y + 0.065], color=T["secondary"], linewidth=1, linestyle="--")
        below = rank < 0.5
        ax.scatter([left + width * rank], [y + 0.035], s=60, color=YELLOW if below else GREEN, zorder=3, edgecolor=T["surface"], linewidth=1)
        ax.text(left + width + 0.015, y + 0.035, "below the median:\ncounts as overfit" if below else "above the median", fontsize=7.5,
                va="center", color=T["ink"])
    ax.text(0.58, 0.575, "worst", fontsize=7, color=T["secondary"], ha="center")
    ax.text(0.73, 0.575, "median", fontsize=7, color=T["secondary"], ha="center")
    ax.text(0.88, 0.575, "best", fontsize=7, color=T["secondary"], ha="center")
    ax.text(x0, 0.035, "4. PBO is the share of the splits whose pick ranks below the median on the half it never saw. The ranks drawn here are "
            "an illustration; on the Kelp grid it was 0%.", fontsize=8.5, color=T["secondary"])
    save(fig, "g18_cscv")


# -- G20 the leader's chance of first against its stake -----------------------------------------------------------

def g20_stake():
    rows = read("standings")
    cases = list(dict.fromkeys(r["case"] for r in rows))
    colors = [BLUE, ORANGE, GREEN]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.9), sharey=True)
    for ax, power, title in zip(axes, ("1", "0"), ("A smaller stake earns proportionally less\n(the mean scales with k, as a smaller position does)",
                                                  "A smaller stake keeps its whole edge\n(only the spread scales with k)")):
        for case, color in zip(cases, colors):
            pts = [r for r in rows if r["mean_power"] == power and r["case"] == case]
            k = [float(r["k"]) for r in pts]
            first = [float(r["first"]) * 100 for r in pts]
            ax.plot(k, first, marker="o", markersize=5, color=color, linewidth=2, label=case)
            ax.annotate(f"{first[-1]:.0f}%", (k[-1], first[-1]), textcoords="offset points", xytext=(6, 0), va="center", fontsize=8, color=T["ink"])
            ax.annotate(f"{first[0]:.0f}%", (k[0], first[0]), textcoords="offset points", xytext=(-6, 0), va="center", ha="right", fontsize=8,
                        color=T["ink"])
        ax.axvline(1, color=T["axis"], linewidth=1, linestyle="--")
        ax.text(1.02, 42, "the bot as\nbacktested", fontsize=7.5, color=T["secondary"])
        ax.set_xticks([0.25, 0.5, 0.75, 1, 1.25, 1.5], ["¼", "½", "¾", "1", "1¼", "1½"])
        ax.set_xlim(0.05, 1.7)
        ax.set_xlabel("risk multiplier k on the last round's bot")
        ax.set_title(title, fontsize=9.5)
    axes[0].set_ylabel("chance of finishing first (%)")
    axes[0].set_ylim(40, 102)
    axes[0].legend(title="the leader's last round at k = 1 (the synthetic field's units)", title_fontsize=8, fontsize=8, loc="upper center",
                   bbox_to_anchor=(1.05, -0.2), ncol=3)
    fig.suptitle("Halve the stake to keep a lead? It depends on the edge: a simulated final", x=0.02, y=1.07, ha="left", fontsize=11, weight="bold")
    save(fig, "g20_stake")


FIGURES = [g17_permutation, g18_cscv, g20_stake]
