"""Do the market trades in the data cluster in time? (Acero, Plank & Zhang 2026, Hawkes order flow.)

usage (from the repo root): uv run python -m experiments.trade_clustering

A Hawkes-driven market maker quotes from recent order flow, which only pays if a trade makes more
trades likely soon after. Per product, on P3 and P4 round 1 (all days): the share of ticks with a
market trade, then the same share among ticks that follow a trade within the last k ticks. A ratio
near 1 means arrivals are memoryless at that horizon; well above 1 means they cluster. The
per-side line does the same for buys after buys (a trade at or above the best ask, against that
tick's book).

The numbers are in IDEAS.md ("Quoting from clustered order flow") and on the wiki page
references/wiki/sources/hawkes-structured-mm.md.
"""

from arena.formats import prosperity

HORIZONS = (1, 5, 20)


def side(tick, product):
    """+1 if a market trade lifted the ask this tick, -1 if one hit the bid, 0 otherwise."""
    trades = tick.trades.get(product) or []
    book = tick.books.get(product)
    if not trades or book is None:
        return 0
    if book.asks and any(t.price >= book.asks[0][0] for t in trades):
        return 1
    if book.bids and any(t.price <= book.bids[0][0] for t in trades):
        return -1
    return 0


def ratios(flags: list[list[bool]], k: int) -> tuple[float, float]:
    """(unconditional share, share given an event in the previous k ticks), pooled over days."""
    n = hits = cond_n = cond_hits = 0
    for day in flags:
        for i, now in enumerate(day):
            n += 1
            hits += now
            if any(day[max(0, i - k):i]):
                cond_n += 1
                cond_hits += now
    return hits / n, (cond_hits / cond_n if cond_n else float("nan"))


def main() -> None:
    for data in ("p3", "p4"):
        days = prosperity.load_days(prosperity.resolve_data_dir(data), ["1"])
        print(f"{data} round 1, {len(days)} days")
        for product in days[0].products:
            any_trade = [[bool(t.trades.get(product)) for t in d.ticks] for d in days]
            buys = [[side(t, product) == 1 for t in d.ticks] for d in days]
            cells = []
            for k in HORIZONS:
                base, cond = ratios(any_trade, k)
                cells.append(f"k={k:2} {cond / base:4.2f}")
            base_b, cond_b = ratios(buys, 5)
            print(f"   {product:22} trade share {base:.3f}  after a trade: {'  '.join(cells)}"
                  f"   buy after buy (k=5): {cond_b / base_b if base_b else float('nan'):4.2f}")


if __name__ == "__main__":
    main()
