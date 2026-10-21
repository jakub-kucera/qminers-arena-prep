import json
from typing import List, Dict
from datamodel import OrderDepth, TradingState, Order, Trade

class Trader:
    def __init__(self):
        self.reset()

    def reset(self):
        self.traderData = {
            "cash": 0,
            "positions": { "RAINFOREST_RESIN": 0, "KELP": 0, "SQUID_INK": 0 },
            "buy_prices": { "RAINFOREST_RESIN": None, "KELP": None, "SQUID_INK": None },
            "sell_prices": { "RAINFOREST_RESIN": None, "KELP": None, "SQUID_INK": None },
            "buy_orders": { "RAINFOREST_RESIN": [], "KELP": [], "SQUID_INK": [] },
            "sell_orders": { "RAINFOREST_RESIN": [], "KELP": [], "SQUID_INK": [] }
        }

    def run(self, state: TradingState):
        # Deserialize traderData
        if state.traderData:
            self.traderData = json.loads(state.traderData)

        # Update cash and positions based on recent trades
        for product, trades in state.own_trades.items():
            for trade in trades:
                if trade.seller == "my_trader_id":  # Assuming your ID is known
                    self.traderData["cash"] += trade.quantity * trade.price
                if trade.buyer == "my_trader_id":
                    self.traderData["cash"] -= trade.quantity * trade.price
                self.traderData["positions"][product] += trade.quantity

        # Strategy for each product
        result = {}
        for product, order_depth in state.order_depths.items():
            orders = []

            # RAINFOREST_RESIN: Stable, so hold a small position
            if product == "RAINFOREST_RESIN":
                target_position = 10
                current_position = self.traderData["positions"].get(product, 0)
                if current_position < target_position:
                    # Buy if below target
                    best_price = min(order_depth.buy_orders.keys())
                    quantity = min(target_position - current_position, 50)
                    orders.append(Order(product, best_price, quantity))
                elif current_position > target_position:
                    # Sell if above target
                    best_price = max(order_depth.sell_orders.keys())
                    quantity = min(current_position - target_position, 50)
                    orders.append(Order(product, best_price, -quantity))

            # KELP: Trend following
            elif product == "KELP":
                mid_price = (min(order_depth.sell_orders.keys()) + max(order_depth.buy_orders.keys())) // 2
                if self.traderData["sell_prices"].get(product) is None:
                    self.traderData["sell_prices"][product] = mid_price
                if self.traderData["buy_prices"].get(product) is None:
                    self.traderData["buy_prices"][product] = mid_price

                # Simple moving average crossover strategy
                if mid_price > self.traderData["sell_prices"][product]:
                    # Current trend is up, consider buying
                    best_price = max(order_depth.buy_orders.keys())
                    quantity = 10  # Small position
                    orders.append(Order(product, best_price, quantity))
                elif mid_price < self.traderData["buy_prices"][product]:
                    # Current trend is down, consider selling
                    best_price = min(order_depth.sell_orders.keys())
                    quantity = 10  # Small position
                    orders.append(Order(product, best_price, -quantity))

                # Update prices
                self.traderData["sell_prices"][product] = max(self.traderData["sell_prices"][product], mid_price)
                self.traderData["buy_prices"][product] = min(self.traderData["buy_prices"][product], mid_price)

            # SQUID_INK: Pattern recognition
            elif product == "SQUID_INK":
                # Look for potential reversal patterns
                if len(order_depth.buy_orders) > 0 and len(order_depth.sell_orders) > 0:
                    top_buy_price = max(order_depth.buy_orders.keys())
                    top_sell_price = min(order_depth.sell_orders.keys())
                    if top_buy_price > top_sell_price:  # Potential reversal
                        # Buy at sell side, sell at buy side
                        quantity = 10
                        orders.append(Order(product, top_sell_price, quantity))
                        orders.append(Order(product, top_buy_price, -quantity))

            # Ensure position limits
            current_position = self.traderData["positions"].get(product, 0)
            for order in orders:
                if (order.quantity > 0 and current_position + order.quantity > 50) or \
                   (order.quantity < 0 and current_position + order.quantity < -50):
                    orders.remove(order)

            result[product] = orders

        # Serialize traderData
        self.traderData["traderData"] = json.dumps(self.traderData)

        # Return orders and traderData
        conversions = 0
        return result, conversions, self.traderData["traderData"]

