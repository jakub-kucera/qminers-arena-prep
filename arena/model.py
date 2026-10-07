"""Format-agnostic market data and order types shared by the engine and the format adapters.

Order and fill quantities are signed: positive buys, negative sells. Book volumes are positive.
Prices are ints in Prosperity data, but nothing here depends on that.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    """Visible order book for one product. Levels are (price, volume), best price first."""

    bids: tuple[tuple[float, int], ...] = ()
    asks: tuple[tuple[float, int], ...] = ()

    @property
    def mid(self) -> float | None:
        if not self.bids or not self.asks:
            return None
        return (self.bids[0][0] + self.asks[0][0]) / 2


@dataclass(frozen=True)
class MarketTrade:
    """A trade between other participants, as reported by the data."""

    product: str
    price: float
    quantity: int
    buyer: str = ""
    seller: str = ""
    timestamp: int = 0


@dataclass(frozen=True)
class Tick:
    """Everything the market shows at one timestamp."""

    timestamp: int
    books: dict[str, Book]
    # Trades printed at this timestamp. Our orders can fill against them (see engine.TradeMatching).
    trades: dict[str, list[MarketTrade]]
    # Prices to value open positions at. Products missing here fall back to the book mid.
    marks: dict[str, float]


@dataclass(frozen=True)
class Day:
    """One continuous session. The engine starts each day flat, with a freshly loaded bot."""

    name: str
    products: list[str]
    limits: dict[str, int]
    ticks: list[Tick]


@dataclass(frozen=True)
class Order:
    product: str
    price: float
    quantity: int


@dataclass(frozen=True)
class Fill:
    timestamp: int
    product: str
    price: float
    quantity: int
    source: str  # "book": took a visible level, "trade": matched against a market trade
    counterparty: str = ""
