# trading_algorithm.py

import json
from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List, Tuple

class Trader:
    """
    Simple deterministic trading strategy.

    For each product at every iteration:
      * If we are below the long limit, submit a single buy order at the current best ask price.
      * If we are above the short limit, submit a single sell order at the current best bid price.

    No state is kept between iterations; all information needed is provided in the TradingState.
    """

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []

            # Current position for this product; default 0 if not held
            current_position = state.position.get(product, 0)

            # Get limits from the problem description
            position_limit = 50  # all products have limit 50

            # Determine best bid (highest price in buy_orders) and best ask (lowest price in sell_orders)
            best_bid_price = None
            best_ask_price = None

            if order_depth.buy_orders:
                best_bid_price = max(order_depth.buy_orders.keys())
            if order_depth.sell_orders:
                best_ask_price = min(order_depth.sell_orders.keys())

            # Place buy order if we can increase position
            if best_ask_price is not None and current_position < position_limit:
                orders.append(Order(symbol=product, price=best_ask_price, quantity=1))

            # Place sell order if we can decrease position
            if best_bid_price is not None and current_position > -position_limit:
                orders.append(Order(symbol=product, price=best_bid_price, quantity=-1))

            result[product] = orders

        conversions = 0  # not used in this round
        trader_data = ""  # no persistent state needed

        return result, conversions, trader_data
