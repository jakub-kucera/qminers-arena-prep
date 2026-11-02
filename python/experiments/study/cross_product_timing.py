"""Two timing checks between products, from the data alone (no bot, no engine).

usage (from the repo root): uv run python -m experiments.study.cross_product_timing

1. Do a basket's legs lead it, or the basket its legs? (Lee et al. 2025, cross-asset order flow.)
   On P3 round 2, all days, with mid prices: the correlation of the legs' implied move this tick,
   sum of weight * leg mid change, with the basket's mid change over the next h ticks, and the
   reverse. Similar small numbers both ways mean neither side leads.
2. How often do a buy and a sell market order arrive in the same tick? (Capponi et al. 2021,
   simultaneous arrivals.) Per product on P4 and P3 round 1: the share of ticks with a market
   trade at or above the best ask, at or below the best bid, and both, against that tick's book,
   next to the product of the one-sided shares (what independence would give).
3. Are basket trades that coincide with trades in its legs a different flow from isolated ones?
   (Petit et al. 2025: a trade described by what traded around it.) On P3 round 2's baskets and P2
   round 3's gift basket, all days: each tick's basket market trades, signed against that tick's
   book (at or through the ask a buy, the bid a sell, else by the side of the mid), are
   "with legs" when a leg traded within a tick of it, else "alone"; per class, the basket's mid
   move over the next h ticks in the trade's direction (mean, its standard error, and per day),
   against half the basket's spread, what a taker following it pays.

The numbers are in IDEAS.md ("Legs leading the basket", "Classifying market trades by
co-occurrence across a basket and its legs") and on the wiki pages
references/wiki/sources/cross-asset-order-flow.md, stochastic-liquidity-demand.md and
etf-trade-flow-decomposition.md.
"""

import math
from statistics import correlation, fmean, median, stdev

from arena.formats import prosperity

BASKETS = {
    "PICNIC_BASKET1": {"CROISSANTS": 6, "JAMS": 3, "DJEMBES": 1},
    "PICNIC_BASKET2": {"CROISSANTS": 4, "JAMS": 2},
}
HORIZONS = (1, 5, 20)
FAMILIES = {("p3", "2"): BASKETS, ("p2", "3"): {"GIFT_BASKET": {"CHOCOLATE": 4, "STRAWBERRIES": 6, "ROSES": 1}}}


def mid(book):
    if book is None or not book.bids or not book.asks:
        return None
    return (book.bids[0][0] + book.asks[0][0]) / 2


def lead_lag() -> None:
    days = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["2"])
    print("1. Lead-lag between a basket and its legs, P3 round 2, all days (correlations)")
    for basket, legs in BASKETS.items():
        products = [basket, *legs]
        mids = [[{p: mid(t.books.get(p)) for p in products} for t in day.ticks] for day in days]
        for h in HORIZONS:
            legs_now, basket_next, basket_now, legs_next = [], [], [], []
            for day in mids:
                for i in range(1, len(day) - h):
                    before, now, later = day[i - 1], day[i], day[i + h]
                    if any(v is None for row in (before, now, later) for v in row.values()):
                        continue
                    legs_now.append(sum(w * (now[p] - before[p]) for p, w in legs.items()))
                    basket_next.append(later[basket] - now[basket])
                    basket_now.append(now[basket] - before[basket])
                    legs_next.append(sum(w * (later[p] - now[p]) for p, w in legs.items()))
            print(f"   {basket} h={h:2}: legs lead {correlation(legs_now, basket_next):+.3f}, "
                  f"basket leads {correlation(basket_now, legs_next):+.3f}  (n={len(legs_now)})")


def simultaneous_trades() -> None:
    print("2. Ticks with both a buy and a sell market trade, round 1")
    for data in ("p4", "p3"):
        days = prosperity.load_days(prosperity.resolve_data_dir(data), ["1"])
        counts: dict[str, list[int]] = {}
        for day in days:
            for tick in day.ticks:
                for product in day.products:
                    c = counts.setdefault(product, [0, 0, 0, 0])
                    c[3] += 1
                    trades = tick.trades.get(product) or []
                    book = tick.books.get(product)
                    if not trades or book is None:
                        continue
                    best_bid = book.bids[0][0] if book.bids else None
                    best_ask = book.asks[0][0] if book.asks else None
                    buy = best_ask is not None and any(t.price >= best_ask for t in trades)
                    sell = best_bid is not None and any(t.price <= best_bid for t in trades)
                    c[0] += buy
                    c[1] += sell
                    c[2] += buy and sell
        for product, (buys, sells, both, n) in counts.items():
            print(f"   {data} {product:22} buy {buys / n:.4f}  sell {sells / n:.4f}  "
                  f"both {both / n:.5f}  if independent {buys / n * sells / n:.5f}")


def signed_volume(trades, book) -> int:
    """Market trades signed against the tick's book: at or through the ask +, the bid -, else by the side of the mid."""
    m, q = mid(book), 0
    for t in trades:
        if book.asks and t.price >= book.asks[0][0]:
            q += t.quantity
        elif book.bids and t.price <= book.bids[0][0]:
            q -= t.quantity
        elif m is not None and t.price != m:
            q += t.quantity if t.price > m else -t.quantity
    return q


def co_occurrence() -> None:
    print("3. Basket trades with and without trades in the legs (within a tick): the basket's mid move in the trade's direction")
    for (data, rnd), baskets in FAMILIES.items():
        days = prosperity.load_days(prosperity.resolve_data_dir(data), [rnd])
        for basket, legs in baskets.items():
            moves = {(c, h): {} for c in ("with legs", "alone") for h in HORIZONS}  # -> day -> moves
            spreads = []
            for day in days:
                mids = [mid(t.books.get(basket)) for t in day.ticks]
                leg_ticks = {i for i, t in enumerate(day.ticks) if any(t.trades.get(leg) for leg in legs)}
                for i, tick in enumerate(day.ticks):
                    book = tick.books.get(basket)
                    if not tick.trades.get(basket) or mids[i] is None:
                        continue
                    spreads.append(book.asks[0][0] - book.bids[0][0])
                    q = signed_volume(tick.trades[basket], book)
                    if q == 0:
                        continue
                    kind = "with legs" if leg_ticks & {i - 1, i, i + 1} else "alone"
                    for h in HORIZONS:
                        if i + h < len(mids) and mids[i + h] is not None:
                            moves[(kind, h)].setdefault(day.name, []).append(math.copysign(1, q) * (mids[i + h] - mids[i]))
            print(f"   {data} round {rnd} {basket} (half its spread {median(spreads) / 2:g})")
            for kind in ("with legs", "alone"):
                cells = []
                for h in HORIZONS:
                    xs = [x for day in moves[(kind, h)].values() for x in day]
                    per_day = " / ".join(f"{fmean(day):+.2f}" for day in moves[(kind, h)].values())
                    cells.append(f"h={h}: {fmean(xs):+.2f} ± {stdev(xs) / math.sqrt(len(xs)):.2f} ({per_day})")
                print(f"     {kind:9} {len([x for day in moves[(kind, 1)].values() for x in day]):4} trade ticks  " + "  ".join(cells))


if __name__ == "__main__":
    lead_lag()
    simultaneous_trades()
    co_occurrence()
