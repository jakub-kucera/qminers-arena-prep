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

The numbers are in IDEAS.md ("Legs leading the basket") and on the wiki pages
references/wiki/sources/cross-asset-order-flow.md and stochastic-liquidity-demand.md.
"""

from statistics import correlation

from arena.formats import prosperity

BASKETS = {
    "PICNIC_BASKET1": {"CROISSANTS": 6, "JAMS": 3, "DJEMBES": 1},
    "PICNIC_BASKET2": {"CROISSANTS": 4, "JAMS": 2},
}
HORIZONS = (1, 5, 20)


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


if __name__ == "__main__":
    lead_lag()
    simultaneous_trades()
