"""Part III's figures (the guidebook's chapters 8 and 9): G11 a basket's spread, G12 the voucher smile, G13 the rival
field and G14 the GRAY_AREA gate. Run through make_figures.py (--only NAME).
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from make_figures import BLUE, GREEN, ORANGE, PINK, T, YELLOW, arrow, box, canvas, read, save, thousands


# -- G11 a basket's spread against its legs -----------------------------------------------------------------------

def basket_spread():
    rows, days = read("basket_spread"), read("basket_days")
    fig, axes = plt.subplots(2, 1, figsize=(8.5, 6.2), gridspec_kw={"height_ratios": [1, 1.1], "hspace": 0.55})
    ax = axes[0]
    one = [r for r in rows if r["day"] == "r2d0"]
    t = [int(r["timestamp"]) / 100 for r in one]
    ax.plot(t, [float(r["basket"]) for r in one], color=BLUE, linewidth=1.2, label="PICNIC_BASKET1 (its wall mid)")
    ax.plot(t, [float(r["legs"]) for r in one], color=ORANGE, linewidth=1.2, label="6 Croissants + 3 Jams + 1 Djembes")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.set_xlabel("tick (round 2, day 0)")
    ax.set_ylabel("price (credits)")
    ax.legend(loc="lower left", fontsize=8.5)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.set_title("One day: the basket and its legs move together")
    ax = axes[1]
    offset = {d["day"]: k * 10000 for k, d in enumerate(days)}
    for k, d in enumerate(days):
        pts = [r for r in rows if r["day"] == d["day"]]
        x = [offset[d["day"]] + int(r["timestamp"]) / 100 for r in pts]
        ax.plot(x, [float(r["spread"]) for r in pts], color=GREEN, linewidth=0.8)
        mean = float(d["mean"])
        ax.plot([offset[d["day"]], offset[d["day"]] + 10000], [mean, mean], color=T["ink"], linewidth=1.6)
        ax.text(offset[d["day"]] + 5000, 330, f"day {d['day'].removeprefix('r2d').replace('-', '−')}: mean {mean:.0f}, sd {float(d['sd']):.0f}",
                ha="center", fontsize=8.5, color=T["ink"], bbox={"facecolor": T["surface"], "edgecolor": "none", "pad": 1})
        if k:
            ax.axvline(offset[d["day"]], color=T["axis"], linewidth=1)
    level, band = float(days[0]["level"]), float(days[0]["level_band"])
    for y in (level - band, level + band):
        ax.axhline(y, color=PINK, linewidth=1.1, linestyle="--")
    ax.text(30150, level + band, f" sell above\n {level + band:.0f}", va="center", fontsize=8, color=T["secondary"])
    ax.text(30150, level - band, f" buy below\n {level - band:.0f}".replace("-", "−"), va="center", fontsize=8, color=T["secondary"])
    ax.axhline(0, color=T["axis"], linewidth=1)
    ax.set_xlim(0, 30000)
    ax.set_ylim(-300, 380)
    ax.set_xticks([0, 5000, 10000, 15000, 20000, 25000, 30000], ["0", "5,000", "0", "5,000", "0", "5,000", ""])
    ax.set_xlabel("tick, day by day (round 2, days −1, 0 and 1)")
    ax.set_ylabel("spread (credits)")
    ax.set_title(f"Three days: the spread, basket less legs; dashed, the template's bands at {level:.0f} ± {band:.0f}")
    fig.suptitle("Prosperity 3's PICNIC_BASKET1 against its legs", x=0.06, ha="left", fontsize=11, weight="bold", y=0.97)
    save(fig, "g11_basket_spread")


# -- G12 the voucher smile ----------------------------------------------------------------------------------------

def voucher_smile():
    rows, fits = read("voucher_smile"), read("voucher_smile_fit")
    fit = next(f for f in fits if f["fit"] == "all five days")
    a, b, c = (float(fit[k]) for k in "abc")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    strikes = sorted({int(r["strike"]) for r in rows})
    for strike, color in zip(strikes, (BLUE, ORANGE, GREEN, YELLOW, PINK)):
        pts = [r for r in rows if int(r["strike"]) == strike]
        ax.scatter([float(r["m"]) for r in pts], [float(r["v"]) for r in pts], s=9, color=color, alpha=0.55,
                   edgecolors="none", label=f"strike {strike:,}")
    ms = sorted(float(r["m"]) for r in rows)
    xs = [ms[0] + (ms[-1] - ms[0]) * k / 200 for k in range(201)]
    ax.plot(xs, [a * x * x + b * x + c for x in xs], color=T["ink"], linewidth=1.8,
            label=f"fitted smile: v = {a:.2f} m² + {b:.3f} m + {c:.3f}")
    ax.set_ylim(0.12, None)
    ax.set_xlabel("moneyness m = ln(strike / rock) / √(years to expiry)")
    ax.set_ylabel("implied volatility v (a year; 0.15 is 15%)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8, ncol=3, markerscale=1.8)
    ax.set_title("Prosperity 3's volcanic rock vouchers: implied vol on five days, one smile")
    save(fig, "g12_voucher_smile")


# -- G13 our settings against fields of rivals --------------------------------------------------------------------

FIELD_NAMES = {"none": "alone", "mm 0.5": "a maker at 0.5", "mm 1": "a maker at 1", "mm 2": "a maker at 2", "copy": "a copy of us",
               "three makers": "three makers", "adversaries": "sniper, spoofer, trapper", "flow": "maker, taker, copy",
               "crowd": "crowd of five", "six": "six bots"}


def rival_field():
    rows = read("rival_field")
    fields = [f for f in dict.fromkeys(r["field"] for r in rows) if f not in ("worst", "mean")]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 5.2), sharey=True)
    for ax, mode in zip(axes, ("per tick", "resting")):
        here = [r for r in rows if r["mode"] == mode]
        for i, field in enumerate(fields):
            cells = [float(r["pnl_k"]) for r in here if r["field"] == field]
            ax.plot([min(cells), max(cells)], [i, i], color=T["grid"], linewidth=5, solid_capstyle="round", zorder=1)
        for (kelp, resin), color, marker, label in (((0.5, 2.0), ORANGE, "o", "as committed: Kelp 0.5, Resin 2"),
                                                     ((0.5, 1.0), BLUE, "D", "Kelp 0.5, Resin 1")):
            pts = {r["field"]: float(r["pnl_k"]) for r in here if float(r["kelp_make_edge"]) == kelp and float(r["resin_make_edge"]) == resin}
            ax.scatter([pts[f] for f in fields], range(len(fields)), color=color, marker=marker, s=34, zorder=3, label=label,
                       edgecolors=T["surface"], linewidths=1)
        ax.set_yticks(range(len(fields)), [FIELD_NAMES.get(f, f) for f in fields])
        ax.set_ylim(len(fields) - 0.5, -0.5)
        ax.set_xlim(-5, 112)
        ax.set_xlabel("our PnL over three days (thousands of credits)")
        ax.set_title("orders live one tick" if mode == "per tick" else "orders rest")
        ax.grid(axis="y", visible=False)
    axes[0].set_ylabel("the other bots in the market")
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(plt.Line2D([], [], color=T["grid"], linewidth=5))
    labels.append("range over all six settings tried")
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=8.5, bbox_to_anchor=(0.55, -0.04))
    fig.suptitle("The same bot in 14 markets: Prosperity 3, round 1", x=0.06, ha="left", fontsize=11, weight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(fig, "g13_rival_field")


# -- G14 the GRAY_AREA gate (diagram) -----------------------------------------------------------------------------

def gray_area_gate():
    fig, ax = canvas(9.5, 4.8)
    top, mid, low = 0.88, 0.58, 0.3
    box(ax, 0.13, top, "a bot file\nthat trades", w=0.2, h=0.13, color=GREEN)
    box(ax, 0.39, top, "arena.validate", w=0.18, h=0.1, color=BLUE, weight="bold")
    box(ax, 0.63, top, "PASS", w=0.12, h=0.1, color=GREEN, weight="bold")
    box(ax, 0.87, top, "upload", w=0.14, h=0.1, color=ORANGE, weight="bold")
    box(ax, 0.145, low, "a bot file that sets\nGRAY_AREA = \"what it does\"", w=0.25, h=0.15, color=YELLOW, size=8.5)
    box(ax, 0.4, low, "arena.validate", w=0.18, h=0.1, color=BLUE, weight="bold")
    box(ax, 0.63, low, "FAIL, with its\nreason in capitals", w=0.18, h=0.13, color=T["loss"], weight="bold", size=8.5)
    box(ax, 0.63, mid, "an organiser's yes,\nwritten in ON_THE_DAY.md", w=0.23, h=0.13, color=PINK, size=8.5)
    box(ax, 0.87, mid, "validate with\n--allow-gray-area:\nWARN", w=0.17, h=0.17, color=BLUE, size=8.5)
    for a, b in (((0.23, top), (0.3, top)), ((0.48, top), (0.57, top)), ((0.69, top), (0.8, top)),
                 ((0.27, low), (0.31, low)), ((0.49, low), (0.54, low)), ((0.745, mid), (0.785, mid))):
        arrow(ax, a, b)
    arrow(ax, (0.63, low + 0.065), (0.63, mid - 0.065), color=PINK)
    ax.text(0.645, (low + mid) / 2, "ask first", fontsize=8, color=PINK, va="center")
    arrow(ax, (0.87, mid + 0.085), (0.87, top - 0.05), color=PINK)
    ax.text(0.63, low - 0.12, "without it: never uploaded", fontsize=8.5, color=T["loss"], ha="center", weight="bold")
    ax.text(0.145, low - 0.16, "backtest it freely; arena.compact\nkeeps the line and warns too", fontsize=8, color=T["secondary"], ha="center", va="center")
    ax.text(0.5, -0.02, "RUNBOOK.md, \"Rules that hold all day\"; ON_THE_DAY.md, \"Gray-area variants\"; python/arena/validate.py's gray_area_check.",
            ha="center", fontsize=8, color=T["secondary"])
    save(fig, "g14_gray_area_gate")


FIGURES = [basket_spread, voucher_smile, rival_field, gray_area_gate]
