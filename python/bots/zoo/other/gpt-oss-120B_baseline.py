# gpt-oss-120B_baseline.py
import json
from typing import List, Tuple, Dict

# The exchange provides these classes; we only need their interfaces.
from datamodel import Order, TradingState, OrderDepth


class Trader:
    """
    Simple baseline trader.

    Strategy:
    * For each product, look at the current best bid and best ask from the
      order book.
    * If we have buying capacity (position < +limit), place a small buy order
      at the best bid price (adding liquidity).
    * If we have selling capacity (position > -limit), place a small sell order
      at the best ask price (adding liquidity).
    * Order sizes are capped at 10 units per side and respect the position limits.
    * No state is kept across iterations apart from an empty JSON string
      (required by the interface).
    """

    # Position limits as given in the problem statement.
    POSITION_LIMITS: Dict[str, int] = {
        "RAINFOREST_RESIN": 50,
        "KELP": 50,
        "SQUID_INK": 50,
    }

    def __init__(self) -> None:
        # No instance‑level state is required; everything is derived from
        # `state` or from `traderData`.
        pass

    def _load_trader_data(self, data_str: str) -> dict:
        """Deserialize the traderData string (JSON)."""
        try:
            return json.loads(data_str) if data_str else {}
        except json.JSONDecodeError:
            return {}

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        # Load any persisted data (not used in this baseline).
        _ = self._load_trader_data(state.traderData)

        result: Dict[str, List[Order]] = {}
        MAX_ORDER_SIZE = 10  # hard cap per side per iteration

        for product, depth in state.order_depths.items():
            orders: List[Order] = []

            # -----------------------------------------------------------------
            # 1. Determine position limits and current position.
            # -----------------------------------------------------------------
            limit = self.POSITION_LIMITS.get(product, 0)
            position = state.position.get(product, 0)

            # Remaining capacity to buy (positive) and sell (negative).
            buy_capacity = max(0, limit - position)          # how many we may still buy
            sell_capacity = max(0, position + limit)        # how many we may still sell
            # sell_capacity is expressed as a positive number of units we can sell.

            # -----------------------------------------------------------------
            # 2. Extract best bid and best ask from the order book.
            # -----------------------------------------------------------------
            best_bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
            best_ask = min(depth.sell_orders.keys()) if depth.sell_orders else None

            # -----------------------------------------------------------------
            # 3. Create a buy order at the best bid (if possible).
            # -----------------------------------------------------------------
            if best_bid is not None and buy_capacity > 0:
                qty = min(MAX_ORDER_SIZE, buy_capacity)
                orders.append(Order(symbol=product, price=best_bid, quantity=qty))

            # -----------------------------------------------------------------
            # 4. Create a sell order at the best ask (if possible).
            # -----------------------------------------------------------------
            if best_ask is not None and sell_capacity > 0:
                qty = -min(MAX_ORDER_SIZE, sell_capacity)   # sell => negative quantity
                orders.append(Order(symbol=product, price=best_ask, quantity=qty))

            result[product] = orders

        # No conversions in this round.
        conversions = 0

        # Persist (empty) trader data for the next iteration.
        trader_data = json.dumps({})

        return result, conversions, trader_data
