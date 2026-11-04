"""The guidebook's Part II, chapters 6 and 7: G7-G10, each from the CSV its data step in data_part2b.py writes."""

from __future__ import annotations

import matplotlib.pyplot as plt

from make_figures import BLUE, GREEN, ORANGE, T, read, save, thousands


# -- G7 the mirror test -------------------------------------------------------------------------------------------

def mirror_test():
    rows = read("mirror_test")
    summary = {r["day"]: r for r in read("mirror_summary")}["r1d-2"]
    ticks = [int(r["tick"]) for r in rows]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8.5, 5.4), sharex=True, gridspec_kw={"height_ratios": [1, 1.25]})
    top.plot(ticks, [float(r["mark"]) for r in rows], color=BLUE, linewidth=1.1, label="the day as it was")
    top.plot(ticks, [float(r["mark_mirrored"]) for r in rows], color=ORANGE, linewidth=1.1, label="the day mirrored")
    top.set_ylabel("Kelp's mid (credits)")
    top.legend(loc="upper left", fontsize=8.5, ncol=2)
    top.set_title("The price: the mirror turns every rise into a fall")
    bottom.plot(ticks, [int(r["position"]) for r in rows], color=BLUE, linewidth=1.0)
    bottom.plot(ticks, [int(r["position_mirrored"]) for r in rows], color=ORANGE, linewidth=1.0)
    for level in (50, -50):
        bottom.axhline(level, color=T["muted"], linewidth=0.9, linestyle="--")
    bottom.text(ticks[-1], 50, "limit +50", ha="right", va="bottom", fontsize=8, color=T["secondary"])
    bottom.text(ticks[-1], -50, "limit −50", ha="right", va="top", fontsize=8, color=T["secondary"])
    bottom.axhline(0, color=T["axis"], linewidth=1)
    bottom.set_ylim(-58, 58)
    bottom.set_ylabel("our position (lots)")
    bottom.set_xlabel("tick of the day")
    bottom.set_title(f"Our position: a mean of {float(summary['mean_position']):+.1f} lots against {float(summary['mean_position_mirrored']):+.1f}, "
                     f"and {float(summary['pnl']):,.0f} credits on both")
    bottom.xaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    fig.suptitle("The mirror test: the template on Prosperity 3's Kelp, round 1, day −2", x=0.06, ha="left", fontsize=11, weight="bold")
    fig.tight_layout()
    save(fig, "g07_mirror_test")


# -- G8 PnL against skew ------------------------------------------------------------------------------------------

def skew_grid():
    rows = read("skew_grid")
    skews = [float(r["skew"]) for r in rows]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    for key, color, label, offset in (("pnl_all", BLUE, "all: a print at our price fills us", 8),
                                      ("pnl_worse", ORANGE, "worse: only a print through it", -14)):
        values = [float(r[key]) for r in rows]
        ax.plot(skews, values, marker="o", color=color, linewidth=1.8, label=label)
        for x, y in zip(skews, values):
            ax.annotate(f"{y / 1000:.1f}k", (x, y), textcoords="offset points", xytext=(0, offset),
                        ha="center", fontsize=8, color=color)
    ax.set_xticks(skews, [f"{s:g}" for s in skews])
    ax.set_ylim(0, 21_000)
    ax.set_yticks(range(0, 20_001, 4000))
    ax.yaxis.set_major_formatter(thousands)
    ax.set_xlabel("skew: ticks both quotes move against the position, at the full limit")
    ax.set_ylabel("Kelp's PnL over three days (credits)")
    ax.legend(loc="lower left", fontsize=8.5)
    ax.set_title("Every tick of skew costs: Prosperity 3's Kelp, round 1")
    save(fig, "g08_skew")


# -- G9 the coupon's residual: does it revert, and how fast -------------------------------------------------------

def coupon_acf():
    rows = read("coupon_acf")
    days = sorted({r["day"] for r in rows})
    fig, ax = plt.subplots(figsize=(8, 3.9))
    for day, color in zip(days, (BLUE, ORANGE, GREEN)):
        points = [r for r in rows if r["day"] == day and r["series"] == "residual"]
        ax.plot([int(r["lag"]) for r in points], [float(r["autocorrelation"]) for r in points], marker="o", markersize=3.5,
                color=color, linewidth=1.4, label=f"day {day[-1]}")
    lives = [float(r["lag"]) for r in rows if r["series"] == "half-life from lag 1"]
    ax.axhline(0.5, color=T["muted"], linewidth=0.9, linestyle="--")
    ax.axhline(0, color=T["axis"], linewidth=1)
    ax.axvspan(min(lives), max(lives), color=T["muted"], alpha=0.18, linewidth=0)
    ax.text((min(lives) * max(lives)) ** 0.5, 0.93, f"half-life from the lag-1 value:\n{min(lives):.0f} to {max(lives):.0f} ticks",
            ha="center", va="top", fontsize=8, color=T["secondary"])
    for window, label in ((20, "smile_window 20:\nlost 267k"), (5000, "smile_window 5,000:\nmade 442k")):
        ax.axvline(window, color=T["secondary"], linewidth=0.9, linestyle=":")
        ax.text(window * 1.12, -0.2, label, fontsize=8, color=T["secondary"], va="bottom")
    ax.set_xscale("log")
    ax.set_xticks([1, 10, 100, 1000, 5000], ["1", "10", "100", "1,000", "5,000"])
    ax.minorticks_off()
    ax.set_ylim(-0.32, 1.05)
    ax.set_xlabel("lag (ticks, log scale)")
    ax.set_ylabel("autocorrelation of the residual")
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_title("How long the coupon's gap from its model lasts: Prosperity 2's coconut coupon, round 4")
    save(fig, "g09_residual_acf")


# -- G10 the perturbed days ---------------------------------------------------------------------------------------

def stress_variants():
    rows = [r for r in read("stress_variants") if r["product"] == "total"]
    variants = list(dict.fromkeys(r["variant"] for r in rows))
    names = list(dict.fromkeys(r["perturbation"] for r in rows))
    labels = {"plain": "plain", "vol2": "volatility\n×2", "trend_up": "trend\nup", "trend_down": "trend\ndown", "shift_up": "shift\nup",
              "shift_down": "shift\ndown", "spike_up": "spike\nup", "spike_down": "spike\ndown", "no_wall": "no wall"}
    value = {(r["variant"], r["perturbation"]): float(r["pnl"]) for r in rows}
    fig, ax = plt.subplots(figsize=(9, 3.9))
    width = 0.27
    for k, (variant, color) in enumerate(zip(variants, (BLUE, ORANGE, GREEN))):
        xs = [i + (k - 1) * width for i in range(len(names))]
        ys = [value[(variant, n)] for n in names]
        ax.bar(xs, ys, width=width * 0.92, color=color, label=variant.replace("Resin's guard", "Resin's fixed_guard"))
        for x, y, n in zip(xs, ys, names):
            if variant == variants[2] and n.startswith("trend"):
                ax.text(x, y + 1200, f"{y / 1000:.1f}k", ha="center", fontsize=7.5, color=color, weight="bold")
    ax.set_xticks(range(len(names)), [labels[n] for n in names], fontsize=8.5)
    ax.yaxis.set_major_formatter(thousands)
    ax.set_ylim(0, 92_000)
    ax.set_ylabel("PnL over three days (credits)")
    ax.legend(loc="upper center", fontsize=8.5, ncol=3, bbox_to_anchor=(0.5, 1.0))
    ax.set_title("The same three days with their prices moved: the template on Prosperity 3, round 1")
    save(fig, "g10_stress")


FIGURES = [mirror_test, skew_grid, coupon_acf, stress_variants]
