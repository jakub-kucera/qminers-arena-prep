"""The guidebook's Part II, chapters 3-5: G3 the signature plot, G4 the market-making margin, G5 markouts by horizon,
G6 Olivia's trades on Squid Ink. Each reads a CSV that parts/data_part2a.py wrote.

Run from the repo root: uv run --group analysis python docs/guidebook/book/scripts/make_figures.py --only signature margins markouts olivia
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from make_figures import BLUE, GREEN, ORANGE, PINK, T, read, save

NAMES = {"KELP": "Kelp", "RAINFOREST_RESIN": "Resin", "SQUID_INK": "Squid Ink", "ABM": "ABIDES",
         "ASH_COATED_OSMIUM": "Osmium", "INTARIAN_PEPPER_ROOT": "Pepper Root"}


# -- G3 the signature plot ----------------------------------------------------------------------------------------

def signature():
    rows = read("signature")
    products = [("KELP", BLUE), ("RAINFOREST_RESIN", GREEN), ("SQUID_INK", ORANGE), ("ABM", PINK)]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    for ax, reference in zip(axes, ("mid", "wall mid")):
        for product, color in products:
            pts = [r for r in rows if r["product"] == product and r["reference"] == reference]
            base = next(float(r["variance_per_tick"]) for r in pts if r["lag"] == "50")
            lags = [int(r["lag"]) for r in pts]
            values = [float(r["variance_per_tick"]) / base for r in pts]
            label = {"ABM": "ABIDES's stock (10 days)"}.get(product, f"{NAMES[product]} (Prosperity 3, round 1)")
            ax.plot(lags, values, marker="o", markersize=3.5, color=color, linewidth=1.6, label=label)
            # the value at one tick is arena.diagnose's `sig` column; Squid Ink's and ABIDES's sit close, so one goes above
            dy = {"SQUID_INK": 6, "ABM": -6}.get(product, 0)
            ax.annotate(f"{values[0]:.1f}", (lags[0], values[0]), textcoords="offset points", xytext=(-6, dy), ha="right",
                        va="center", fontsize=8, color=color)
        ax.axhline(1, color=T["axis"], linewidth=1)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.45, 1500)
        ax.set_xticks([1, 10, 50, 100, 1000], ["1", "10", "50", "100", "1,000"])
        ax.minorticks_off()
        ax.set_xlabel("h, ticks between the two prices (log scale)")
        ax.set_title(f"the {reference}")
    axes[0].set_yticks([0.05, 0.1, 0.3, 1, 3, 10, 50], ["0.05", "0.1", "0.3", "1", "3", "10", "50"])
    axes[0].set_ylabel("variance of h-tick changes over h,\nas a multiple of its value at 50 ticks")
    axes[1].legend(loc="upper right", fontsize=8)
    fig.suptitle("The signature plot: falling where noise reverts, flat for a random walk, rising where moves continue",
                 x=0.06, ha="left", fontsize=11, weight="bold")
    fig.tight_layout()
    save(fig, "g03_signature")


# -- G4 the market-making margin ----------------------------------------------------------------------------------

def margins():
    rows = [r for r in read("margins") if not r["market"].startswith("Prosperity 4")]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ys = list(range(len(rows)))[::-1]
    for y, r in zip(ys, rows):
        half, impact, margin = float(r["half_spread_paid"]), float(r["impact_50"]), float(r["margin"])
        ax.barh(y + 0.17, half, height=0.32, color=GREEN, label="what the taker paid, against the wall mid" if y == ys[0] else None)
        ax.barh(y - 0.17, -impact, height=0.32, color=ORANGE, label="the move after, 50 ticks on (taken back)" if y == ys[0] else None)
        ax.scatter([margin], [y], color=T["ink"], marker="D", s=34, zorder=3, label="the margin: their difference" if y == ys[0] else None)
        ax.text(max(half, margin) + 0.08, y + 0.17, f"margin {margin:+.2f}", va="center", fontsize=8.5, weight="bold")
    ax.axvline(0, color=T["axis"], linewidth=1)
    ax.set_yticks(ys, [f"{NAMES[r['product']]}\n({'Prosperity 3, credits' if r['market'].startswith('Prosperity') else 'ABIDES, cents'})"
                       for r in rows], fontsize=8.5)
    ax.set_xlim(-1.6, 2.1)
    ax.set_xlabel("a unit traded, in ticks (a credit on Prosperity, a cent on ABIDES)")
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(k) for k in sorted(labels, key=lambda k: ("taker" not in k, "margin" in k))]
    ax.legend([handles[k] for k in order], [labels[k] for k in order], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=7.5)
    ax.grid(axis="y", visible=False)
    ax.set_title("Half the spread against the impact: where plain market making can pay", pad=24)
    save(fig, "g04_margins")


# -- G5 markouts by horizon ---------------------------------------------------------------------------------------

def markouts():
    rows = [r for r in read("markouts") if r["reference"] == "wall mid"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for ax, (market, color, unit) in zip(axes, (("Prosperity 3 Kelp", BLUE, "credits"), ("ABIDES", PINK, "cents"))):
        pts = [r for r in rows if r["market"] == market]
        xs = list(range(len(pts)))
        values = [float(r["markout"]) for r in pts]
        ax.plot(xs, values, marker="o", color=color, linewidth=1.8)
        for x, v in zip(xs, values):
            if x in (0, 1, len(xs) - 1) or (market == "ABIDES" and x == 6):
                ax.annotate(f"{v:+.2f}", (x, v), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
        ax.axhline(0, color=T["axis"], linewidth=1)
        ax.set_xticks(xs, ["at the\nfill" if r["horizon"] == "0" else f"{int(r['horizon']):,}" for r in pts], fontsize=8)
        ax.set_xlabel("ticks after the fill")
        ax.set_ylabel(f"markout a unit ({unit})")
        ax.set_title(f"{'Prosperity 3, Kelp (3 days)' if market != 'ABIDES' else 'ABIDES (10 days)'}")
        ax.margins(y=0.2)
    axes[0].set_ylim(0, 0.9)
    fig.suptitle("The template's passive fills, valued against the wall mid as time passes", x=0.06, ha="left", fontsize=11,
                 weight="bold")
    fig.tight_layout()
    save(fig, "g05_markouts")


# -- G6 Olivia's trades -------------------------------------------------------------------------------------------

def olivia():
    prices, trades = read("olivia_prices"), read("olivia_trades")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot([int(r["tick"]) for r in prices], [float(r["wall_mid"]) for r in prices], color=T["muted"], linewidth=0.9,
            label="Squid Ink's wall mid")
    seen = set()
    for r in trades:
        key = (r["day"], r["tick"])
        if key in seen:  # one decision printed as two trades (two counterparties at the same tick)
            continue
        seen.add(key)
        lots = sum(int(t["lots"]) for t in trades if (t["day"], t["tick"]) == key)
        buy = r["side"] == "buy"
        ax.scatter([int(r["tick"])], [float(r["price"])], color=BLUE if buy else ORANGE, marker="^" if buy else "v", s=70, zorder=3,
                   edgecolor=T["surface"], linewidth=0.8)
        ax.annotate(f"{'buys' if buy else 'sells'} {lots}", (int(r["tick"]), float(r["price"])), textcoords="offset points",
                    xytext=(0, -16 if buy else 10), ha="center", fontsize=8, color=BLUE if buy else ORANGE)
    for k in (1, 2):
        ax.axvline(k * 10000, color=T["axis"], linewidth=0.8, linestyle="--")
    for k, name in enumerate(("day 2", "day 3", "day 4")):
        ax.text(k * 10000 + 200, 2112, name, fontsize=8.5, color=T["secondary"])
    ax.scatter([], [], color=BLUE, marker="^", s=50, label="Olivia buys")
    ax.scatter([], [], color=ORANGE, marker="v", s=50, label="Olivia sells")
    ax.set_xlim(0, 30000)
    ax.set_ylim(1735, 2135)
    ax.set_xticks([0, 5000, 10000, 15000, 20000, 25000, 30000], ["0", "5,000", "10,000", "15,000", "20,000", "25,000", "30,000"])
    ax.set_xlabel("tick, the three days end to end")
    ax.set_ylabel("price (credits)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9), ncol=3, fontsize=8)
    ax.set_title("Olivia's trades on Prosperity 3's Squid Ink, round 5: at each day's low and high")
    save(fig, "g06_olivia")


FIGURES = [signature, margins, markouts, olivia]
