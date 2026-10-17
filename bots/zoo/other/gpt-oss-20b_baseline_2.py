# trader.py
import json
from typing import List
from datamodel import Order, OrderDepth, TradingState

class Trader:
    """
    Simple deterministic trend‑following strategy.
    For each product (except the stable RAINFOREST_RESIN) we:
        - Compute the current mid price.
        - Compare it to the mid price seen in the previous iteration.
        - If the mid price has risen, we buy one unit at the best ask.
        - If it has fallen, we sell one unit at the best bid.
    Positions are capped at ±50.  No trading is done for RAINFOREST_RESIN.
    The previous mid price for each product is stored in traderData (JSON).
    """

    def run(self, state: TradingState):
        # Load previous mid prices
        if state.traderData:
            prev_mid = json.loads(state.traderData)
        else:
            prev_mid = {}

        orders = {}
        for product, depth in state.order_depths.items():
            # Determine best bid and best ask
            buy_prices = list(depth.buy_orders.keys())
            sell_prices = list(depth.sell_orders.keys())
            best_bid = max(buy_prices) if buy_prices else None
            best_ask = min(sell_prices) if sell_prices else None

            # Compute current mid price
            if best_bid is not None and best_ask is not None:
                mid = (best_bid + best_ask) / 2.0
            elif best_bid is not None:
                mid = float(best_bid)
            elif best_ask is not None:
                mid = float(best_ask)
            else:
                # No orders for this product; skip
                orders[product] = []
                continue

            # Store current mid price for next iteration
            prev_mid[product] = mid

            # Determine price movement relative to previous mid
            last_mid = prev_mid.get(product, mid)
            delta = mid - last_mid

            # Current position
            position = state.position.get(product, 0)

            # Build order list
            order_list: List[Order] = []

            # Stable product: do nothing
            if product == "RAINFOREST_RESIN":
                pass

            # Trend following for KELP
            elif product == "KELP":
                qty = 1
                if delta > 0:  # price rising: buy
                    if position < 50 and best_ask is not None:
                        order_list.append(Order(product, best_ask, qty))
                elif delta < 0:  # price falling: sell
                    if position > -50 and best_bid is not None:
                        order_list.append(Order(product, best_bid, -qty))

            # Trend following for SQUID_INK
            elif product == "SQUID_INK":
                qty = 1
                if delta > 0:  # price rising: buy
                    if position < 50 and best_ask is not None:
                        order_list.append(Order(product, best_ask, qty))
                elif delta < 0:  # price falling: sell
                    if position > -50 and best_bid is not None:
                        order_list.append(Order(product, best_bid, -qty))

            orders[product] = order_list

        # Convert state to JSON for next iteration
        trader_data_str = json.dumps(prev_mid)
        return orders, 0, trader_data_str
