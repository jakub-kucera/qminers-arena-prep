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


def penalty_paid(result: DayResult, rate: float) -> float:
    """What --limit-penalty charged the bot: `rate` for each lot beyond a limit, each tick."""
    return sum(rate * max(abs(p) - result.limits[product], 0) for product, series in result.positions.items() for p in series)


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
