"""Summaries of backtest results, as text tables and CSV files."""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

from arena.engine import DayResult


@dataclass(frozen=True)
class ProductStats:
    product: str
    pnl: float
    fills: int
    volume: int
    max_position: int
    at_limit: float  # share of ticks spent at the position limit


def product_stats(result: DayResult) -> list[ProductStats]:
    stats = []
    for product in result.products:
        positions = result.positions[product]
        fills = [fill for fill in result.fills if fill.product == product]
        limit = result.limits[product]
        stats.append(
            ProductStats(
                product=product,
                pnl=result.pnl[product][-1] if positions else 0.0,
                fills=len(fills),
                volume=sum(abs(fill.quantity) for fill in fills),
                max_position=max((abs(p) for p in positions), default=0),
                at_limit=sum(abs(p) >= limit for p in positions) / len(positions) if positions else 0.0,
            )
        )
    return stats


def total_pnl(result: DayResult) -> list[float]:
    return [sum(values) for values in zip(*result.pnl.values())]


def max_drawdown(series: list[float]) -> float:
    peak, drawdown = float("-inf"), 0.0
    for value in series:
        peak = max(peak, value)
        drawdown = max(drawdown, peak - value)
    return drawdown


def format_day(result: DayResult, penalty: float | None = None) -> str:
    """The day's summary; `penalty` is the run's --limit-penalty, which changes what a breach is."""
    stats = [s for s in product_stats(result) if s.fills or s.max_position]
    lines = [f"{result.day} · {len(result.timestamps):,} ticks"]
    if stats:
        width = max(len(s.product) for s in stats)
        lines.append(f"  {'product':<{width}}  {'pnl':>10}  {'fills':>6}  {'volume':>7}  {'max|pos|':>8}  {'at limit':>8}")
        for s in stats:
            lines.append(
                f"  {s.product:<{width}}  {s.pnl:>10,.0f}  {s.fills:>6,}  {s.volume:>7,}"
                f"  {s.max_position:>8}  {s.at_limit:>8.1%}"
            )
    else:
        lines.append("  no trades")
    total = total_pnl(result)
    lines.append(f"  total pnl {total[-1] if total else 0:,.0f} · max drawdown {max_drawdown(total):,.0f}")

    ms = sorted(s * 1000 for s in result.step_seconds)
    if ms:
        p99 = ms[min(len(ms) - 1, int(len(ms) * 0.99))]
        lines.append(f"  bot time per tick: mean {statistics.fmean(ms):.2f} ms · p99 {p99:.2f} ms · max {ms[-1]:.2f} ms")

    if result.errors:
        timestamp, error = result.errors[0]
        lines.append(f"  ! {len(result.errors)} errors, first at {timestamp}: {last_line(error)}")
    if result.cancels:
        placed = len({order.id for _, order in result.orders})
        lines.append(f"  orders: {placed:,} placed · {len(result.cancels):,} cancelled")
    if result.limit_breaches and penalty is not None:
        timestamp, product = result.limit_breaches[0]
        lines.append(f"  ! {len(result.limit_breaches)} ticks over a limit (--limit-penalty), first {product} at {timestamp}, "
                     f"charged {penalty_paid(result, penalty):,.0f} in all")
    elif result.limit_breaches:
        timestamp, product = result.limit_breaches[0]
        lines.append(
            f"  ! {len(result.limit_breaches)} ticks with orders cancelled for breaching a limit, "
            f"first {product} at {timestamp}"
        )
    if result.races:
        lines.append(f"  {len(result.races)} ticks with orders rejected after another bot's fill moved your position (a race)")
    return "\n".join(lines)


def penalty_paid(result: DayResult, rate: float, product: str | None = None) -> float:
    """What --limit-penalty charged the bot: `rate` for each lot beyond a limit, each tick (one product's, or all)."""
    products = result.positions if product is None else [product]
    return sum(rate * max(abs(p) - result.limits[name], 0) for name in products for p in result.positions[name])


QUANTILES = (0.5, 0.68, 0.95, 0.997)  # the portal's |position| quantiles
BLOCKS = 20  # the batch-means standard error splits the day into this many blocks


def format_metrics(result: DayResult, penalty: float | None = None) -> str:
    """The figures the Arena's portal shows on each submission, in its order (ON_THE_DAY.md, "Known so far"),
    per product and in total, then our PnL, which should be cash + position × mark − penalty.

    fills: our fills, and in brackets the orders they filled (the portal's "filled orders" may count either).
    volume: lots traded. position: the end position. cash: what trading left, the penalty not taken off.
    mark: the price the end position is valued at (--mark). penalty: what --limit-penalty charged, 0 without it.
    s.e. ticks: the standard error of the day's PnL from its per-tick changes taken as independent,
    stdev × √ticks. s.e. blocks: the same from the sums of BLOCKS consecutive blocks, stdev × √BLOCKS
    (batch means, which allows for correlated changes). The portal doesn't say how it computes its own,
    so compare both with the first upload's. |position|: quantiles over the day's ticks, interpolated
    linearly between ranks (numpy's default).
    """
    rate = penalty or 0.0
    stats = [s for s in product_stats(result) if s.fills or s.max_position]
    if not stats:
        return "  portal metrics: no trades"
    header = ["", "fills", "volume", "position", "cash", "mark", "penalty", "s.e. ticks", "s.e. blocks",
              "|position| q50/68/95/99.7", "pnl"]
    rows = []
    for s in stats:
        fills = [fill for fill in result.fills if fill.product == s.product]
        position, mark, pnl = result.positions[s.product][-1], result.marks[s.product][-1], result.pnl[s.product][-1]
        paid = penalty_paid(result, rate, s.product)
        quantiles = " / ".join(f"{q:g}" for q in _quantiles([abs(p) for p in result.positions[s.product]], QUANTILES))
        rows.append([s.product, f"{s.fills:,} ({len({f.order_id for f in fills}):,})", f"{s.volume:,}", f"{position:,}",
                     f"{pnl - position * mark + paid:,.2f}", f"{mark:,.2f}", f"{paid:,.2f}",
                     *_standard_errors(result.pnl[s.product]), quantiles, f"{pnl:,.2f}"])
    if len(stats) > 1:
        total = total_pnl(result)
        paid = sum(penalty_paid(result, rate, s.product) for s in stats)
        cash = sum(result.pnl[s.product][-1] - result.positions[s.product][-1] * result.marks[s.product][-1] for s in stats)
        orders = len({f.order_id for f in result.fills})
        rows.append(["total", f"{sum(s.fills for s in stats):,} ({orders:,})", f"{sum(s.volume for s in stats):,}", "-",
                     f"{cash + paid:,.2f}", "-", f"{paid:,.2f}", *_standard_errors(total), "-", f"{total[-1]:,.2f}"])
    widths = [max(len(row[k]) for row in [header, *rows]) for k in range(len(header))]
    lines = ["  portal metrics (--metrics):"]
    for row in [header, *rows]:
        lines.append("    " + "  ".join(cell.ljust(w) if k == 0 else cell.rjust(w) for k, (cell, w) in enumerate(zip(row, widths))))
    return "\n".join(lines)


def format_metrics_total(results: list[DayResult], penalty: float | None = None) -> str:
    """The portal's figures for a whole submission, with the days added up.

    The portal shows one set of metrics per submission, not one per day. This table adds each
    day's fills, volume, cash and penalty, takes the last day's end position and mark, pools the
    |position| quantiles over every day's ticks, and adds a third standard error from the daily
    PnLs (`s.e. days`, stdev x sqrt(days)). `pnl` is the sum of the days; the line below the table
    gives the sum and the mean, so either can be compared with the portal's `score`. If the
    evaluation runs the days as one continuous session instead of summing them, the end position
    and cash can differ: the first upload's page says which.
    """
    rate = penalty or 0.0
    products: list[str] = []
    for result in results:
        for product in result.products:
            if product in products:
                continue
            stats = next((s for s in product_stats(result) if s.product == product), None)
            if stats and (stats.fills or stats.max_position):
                products.append(product)
    label = f"{len(results)} day" + ("" if len(results) == 1 else "s")
    if not products:
        return f"  portal metrics over {label}: no trades"

    rows: list[list[str]] = []
    sum_fills = sum_orders = sum_volume = 0
    sum_cash = sum_paid = sum_pnl = 0.0
    for product in products:
        fills = orders = volume = 0
        position = 0
        cash = mark = paid = pnl = 0.0
        abs_positions: list[int] = []
        series_by_day: list[list[float]] = []
        day_totals: list[float] = []
        for result in results:
            if product not in result.products:
                continue
            stats = next((s for s in product_stats(result) if s.product == product), None)
            if stats is None:
                continue
            positions = result.positions.get(product, [])
            marks = result.marks.get(product, [])
            series = result.pnl.get(product, [])
            day_paid = penalty_paid(result, rate, product)
            day_pnl = series[-1] if series else 0.0
            end_position = positions[-1] if positions else 0
            end_mark = marks[-1] if marks else 0.0
            fills += stats.fills
            orders += len({fill.order_id for fill in result.fills if fill.product == product})
            volume += stats.volume
            position = end_position
            mark = end_mark
            cash += day_pnl - end_position * end_mark + day_paid
            paid += day_paid
            pnl += day_pnl
            abs_positions.extend(abs(p) for p in positions)
            series_by_day.append(series)
            day_totals.append(day_pnl)
        quantiles = " / ".join(f"{q:g}" for q in _quantiles(abs_positions, QUANTILES)) if abs_positions else "-"
        rows.append([product, f"{fills:,} ({orders:,})", f"{volume:,}", f"{position:,}", f"{cash:,.2f}",
                     f"{mark:,.2f}", f"{paid:,.2f}", *_total_standard_errors(series_by_day, day_totals),
                     quantiles, f"{pnl:,.2f}"])
        sum_fills += fills
        sum_orders += orders
        sum_volume += volume
        sum_cash += cash
        sum_paid += paid
        sum_pnl += pnl

    total_series = [series for series in (total_pnl(result) for result in results) if series]
    total_days = [series[-1] for series in total_series]
    if len(products) > 1:
        rows.append(["total", f"{sum_fills:,} ({sum_orders:,})", f"{sum_volume:,}", "-", f"{sum_cash:,.2f}", "-",
                     f"{sum_paid:,.2f}", *_total_standard_errors(total_series, total_days), "-", f"{sum_pnl:,.2f}"])

    header = ["", "fills", "volume", "position", "cash", "mark", "penalty", "s.e. ticks", "s.e. blocks",
              "s.e. days", "|position| q50/68/95/99.7", "pnl"]
    widths = [max(len(row[k]) for row in [header, *rows]) for k in range(len(header))]
    lines = [f"  portal metrics over {label} (--metrics):"]
    for row in [header, *rows]:
        lines.append("    " + "  ".join(cell.ljust(w) if k == 0 else cell.rjust(w) for k, (cell, w) in enumerate(zip(row, widths))))
    finals = [series[-1] for series in total_series]
    mean = statistics.fmean(finals) if finals else 0.0
    lines.append(f"  days: {len(results)} · sum {sum(finals):,.2f} · mean {mean:,.2f}")
    return "\n".join(lines)


def _total_standard_errors(series_by_day: list[list[float]], day_totals: list[float]) -> list[str]:
    """The two within-run standard errors over all days' tick changes, and one across the daily totals."""
    changes = [b - a for series in series_by_day for a, b in zip([0.0, *series], series)]
    ticks = statistics.stdev(changes) * len(changes) ** 0.5 if len(changes) > 1 else None
    blocks = None
    if len(changes) >= 2 * BLOCKS:
        edges = [len(changes) * k // BLOCKS for k in range(BLOCKS + 1)]
        blocks = statistics.stdev(sum(changes[a:b]) for a, b in zip(edges, edges[1:])) * BLOCKS**0.5
    days = statistics.stdev(day_totals) * len(day_totals) ** 0.5 if len(day_totals) > 1 else None
    return ["-" if v is None else f"{v:,.2f}" for v in (ticks, blocks, days)]


def _standard_errors(pnl: list[float]) -> list[str]:
    """format_metrics' two standard errors of a PnL series' last value, as text ("-" if too short)."""
    changes = [b - a for a, b in zip([0.0, *pnl], pnl)]
    ticks = statistics.stdev(changes) * len(changes) ** 0.5 if len(changes) > 1 else None
    blocks = None
    if len(changes) >= 2 * BLOCKS:
        edges = [len(changes) * k // BLOCKS for k in range(BLOCKS + 1)]
        blocks = statistics.stdev(sum(changes[a:b]) for a, b in zip(edges, edges[1:])) * BLOCKS**0.5
    return ["-" if v is None else f"{v:,.2f}" for v in (ticks, blocks)]


def _quantiles(values: list[float], qs: tuple[float, ...]) -> list[float]:
    """Each quantile of `values`, interpolated linearly between ranks (numpy.quantile's default)."""
    xs = sorted(values)
    out = []
    for q in qs:
        h = (len(xs) - 1) * q
        lo = int(h)
        out.append(xs[lo] + (h - lo) * (xs[min(lo + 1, len(xs) - 1)] - xs[lo]))
    return out


def format_rivals(names: list[str], results: list[DayResult]) -> str:
    """One line per rival bot that traded in the same market."""
    lines = []
    for name, result in zip(names, results):
        total = total_pnl(result)
        line = f"  vs {name}: pnl {total[-1] if total else 0:,.0f} · {len(result.fills):,} fills"
        if result.errors:
            line += f" · ! {len(result.errors)} errors"
        if result.limit_breaches:
            line += f" · ! {len(result.limit_breaches)} limit breaches"
        if result.races:
            line += f" · {len(result.races)} races"
        lines.append(line)
    return "\n".join(lines)


def format_overall(results: list[DayResult]) -> str:
    finals = {r.day: (total_pnl(r) or [0.0])[-1] for r in results}
    by_product: dict[str, float] = {}
    for result in results:
        for s in product_stats(result):
            by_product[s.product] = by_product.get(s.product, 0.0) + s.pnl
    days = " · ".join(f"{day} {pnl:,.0f}" for day, pnl in finals.items())
    products = " · ".join(f"{product} {pnl:,.0f}" for product, pnl in by_product.items() if pnl)
    return f"total over {len(results)} days: {sum(finals.values()):,.0f}\n  by day: {days}\n  by product: {products or '-'}"


def last_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[-1] if lines else text


def write_csvs(result: DayResult, out_dir: Path) -> None:
    """Writes four CSVs per day, read back by arena.analysis.

    <day>_timeline.csv  per product per tick: position, mark, pnl, best bid/ask, limit, wall mid
    <day>_fills.csv     every fill
    <day>_orders.csv    every order working at each tick (placed then, or resting from earlier)
    <day>_trades.csv    every market trade in the data, for measuring how the price moves after trades
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / f"{result.day}_timeline.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "product", "position", "mark", "pnl", "best_bid", "best_ask", "limit", "wall_mid"])
        for product in result.products:
            rows = zip(
                result.timestamps,
                result.positions[product],
                result.marks[product],
                result.pnl[product],
                result.best_bids[product],
                result.best_asks[product],
                result.wall_mids[product],
            )
            for timestamp, position, mark, pnl, bid, ask, wall in rows:
                writer.writerow(
                    [timestamp, product, position, mark, pnl, _blank(bid), _blank(ask), result.limits[product], _blank(wall)]
                )
    with (out_dir / f"{result.day}_fills.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "product", "price", "quantity", "source", "counterparty", "order_id"])
        for fill in result.fills:
            writer.writerow(
                [fill.timestamp, fill.product, fill.price, fill.quantity, fill.source, fill.counterparty, fill.order_id]
            )
    with (out_dir / f"{result.day}_orders.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "id", "product", "price", "quantity"])
        for timestamp, order in result.orders:
            writer.writerow([timestamp, order.id, order.product, order.price, order.quantity])
    with (out_dir / f"{result.day}_trades.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "product", "price", "quantity", "buyer", "seller"])
        for timestamp, trade in result.market_trades:
            writer.writerow([timestamp, trade.product, trade.price, trade.quantity, trade.buyer, trade.seller])


def _blank(value: float | None) -> float | str:
    return "" if value is None else value
