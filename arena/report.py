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


def format_day(result: DayResult) -> str:
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
    if result.limit_breaches:
        timestamp, product = result.limit_breaches[0]
        lines.append(
            f"  ! {len(result.limit_breaches)} ticks with orders cancelled for breaching a limit, "
            f"first {product} at {timestamp}"
        )
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
    """Writes three CSVs per day, read back by arena.analysis.

    <day>_timeline.csv  per product per tick: position, mark, pnl, best bid/ask, limit
    <day>_fills.csv     every fill
    <day>_orders.csv    every order that reached the market (after the limit check)
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / f"{result.day}_timeline.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "product", "position", "mark", "pnl", "best_bid", "best_ask", "limit"])
        for product in result.products:
            rows = zip(
                result.timestamps,
                result.positions[product],
                result.marks[product],
                result.pnl[product],
                result.best_bids[product],
                result.best_asks[product],
            )
            for timestamp, position, mark, pnl, bid, ask in rows:
                writer.writerow([timestamp, product, position, mark, pnl, _blank(bid), _blank(ask), result.limits[product]])
    with (out_dir / f"{result.day}_fills.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "product", "price", "quantity", "source", "counterparty"])
        for fill in result.fills:
            writer.writerow([fill.timestamp, fill.product, fill.price, fill.quantity, fill.source, fill.counterparty])
    with (out_dir / f"{result.day}_orders.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "product", "price", "quantity"])
        for timestamp, order in result.orders:
            writer.writerow([timestamp, order.product, order.price, order.quantity])


def _blank(value: float | None) -> float | str:
    return "" if value is None else value
