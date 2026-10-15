import json
from typing import Any

from datamodel import Order, OrderDepth, TradingState


class Trader:
    LIMITS = {
        "RAINFOREST_RESIN": 50,
        "KELP": 50,
        "SQUID_INK": 50,
    }

    RESIN_FAIR = 10000

    def run(self, state: TradingState):
        history = self._load_history(state.traderData)
        result: dict[str, list[Order]] = {}

        for symbol, depth in state.order_depths.items():
            limit = self.LIMITS.get(symbol, 50)
            position = state.position.get(symbol, 0)

            best_bid, best_ask, observed_price = self._book_statistics(depth)

            if observed_price is None:
                result[symbol] = []
                continue

            symbol_history = history.setdefault(symbol, {})
            previous_price = symbol_history.get("mid", observed_price)

            symbol_history["mid"] = observed_price
            symbol_history["ema_fast"] = self._ema(
                symbol_history.get("ema_fast"),
                observed_price,
                0.22,
            )
            symbol_history["ema_slow"] = self._ema(
                symbol_history.get("ema_slow"),
                observed_price,
                0.035,
            )
            symbol_history["velocity"] = self._ema(
                symbol_history.get("velocity"),
                observed_price - previous_price,
                0.20,
            )
            symbol_history["volatility"] = self._ema(
                symbol_history.get("volatility"),
                abs(observed_price - previous_price),
                0.08,
            )

            if symbol == "RAINFOREST_RESIN":
                fair_value = float(self.RESIN_FAIR)
                quote_edge = 1.0
                take_edge = 0.0
            elif symbol == "KELP":
                fair_value = (
                    0.65 * symbol_history["ema_fast"]
                    + 0.35 * symbol_history["ema_slow"]
                )
                quote_edge = max(
                    1.0,
                    min(3.0, 1.1 + 0.7 * symbol_history["volatility"]),
                )
                take_edge = 0.5
            else:
                fast = symbol_history["ema_fast"]
                slow = symbol_history["ema_slow"]
                velocity = symbol_history["velocity"]

                momentum_value = fast + max(-3.0, min(3.0, 1.8 * velocity))
                fair_value = 0.72 * momentum_value + 0.28 * slow

                quote_edge = max(
                    1.0,
                    min(5.0, 1.4 + 0.9 * symbol_history["volatility"]),
                )
                take_edge = 0.7

            orders: list[Order] = []

            buy_room = max(0, limit - position)
            sell_room = max(0, limit + position)

            if (
                best_ask is not None
                and best_ask <= fair_value - take_edge
                and buy_room > 0
            ):
                quantity = min(
                    buy_room,
                    abs(depth.sell_orders[best_ask]),
                )
                if quantity > 0:
                    orders.append(Order(symbol, best_ask, quantity))
                    buy_room -= quantity

            if (
                best_bid is not None
                and best_bid >= fair_value + take_edge
                and sell_room > 0
            ):
                quantity = min(
                    sell_room,
                    depth.buy_orders[best_bid],
                )
                if quantity > 0:
                    orders.append(Order(symbol, best_bid, -quantity))
                    sell_room -= quantity

            inventory_bias = position / limit

            buy_quote = int(fair_value - quote_edge - 1.2 * inventory_bias)
            sell_quote = int(fair_value + quote_edge - 1.2 * inventory_bias)

            if best_bid is not None:
                buy_quote = min(buy_quote, best_bid + 1)

            if best_ask is not None:
                sell_quote = max(sell_quote, best_ask - 1)

            if buy_quote >= sell_quote:
                buy_quote = int(fair_value - quote_edge)
                sell_quote = int(fair_value + quote_edge)

            quote_size = 8 if symbol == "RAINFOREST_RESIN" else 6

            if buy_room > 0 and (
                best_ask is None or buy_quote < best_ask
            ):
                orders.append(
                    Order(
                        symbol,
                        buy_quote,
                        min(buy_room, quote_size),
                    )
                )

            if sell_room > 0 and (
                best_bid is None or sell_quote > best_bid
            ):
                orders.append(
                    Order(
                        symbol,
                        sell_quote,
                        -min(sell_room, quote_size),
                    )
                )

            result[symbol] = orders

        return (
            result,
            0,
            json.dumps(
                history,
                separators=(",", ":"),
                allow_nan=False,
            ),
        )

    @staticmethod
    def _ema(old_value: Any, value: float, alpha: float) -> float:
        if old_value is None:
            return value
        return alpha * value + (1.0 - alpha) * float(old_value)

    @staticmethod
    def _load_history(data: str) -> dict[str, dict[str, float]]:
        if not data:
            return {}

        try:
            parsed = json.loads(data)
        except (TypeError, ValueError):
            return {}

        if not isinstance(parsed, dict):
            return {}

        return parsed

    @staticmethod
    def _book_statistics(
        depth: OrderDepth,
    ) -> tuple[int | None, int | None, float | None]:
        best_bid = max(depth.buy_orders) if depth.buy_orders else None
        best_ask = min(depth.sell_orders) if depth.sell_orders else None

        if best_bid is not None and best_ask is not None:
            bid_volume = max(1, depth.buy_orders[best_bid])
            ask_volume = max(1, abs(depth.sell_orders[best_ask]))

            microprice = (
                best_bid * ask_volume + best_ask * bid_volume
            ) / (bid_volume + ask_volume)

            return best_bid, best_ask, microprice

        if best_bid is not None:
            return best_bid, None, float(best_bid)

        if best_ask is not None:
            return None, best_ask, float(best_ask)

        return None, None, None
