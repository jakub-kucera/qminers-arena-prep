import json
from typing import List, Dict
from datamodel import Order, OrderDepth, TradingState

class Trader:
    def __init__(self):
        self.trader_data = {
            "cash": 0,
            "inventory": {},
            "fair_value": {
                "RAINFOREST_RESIN": 10000,  # Starting fair value
                "KELP": 2030,  # Starting fair value
                "SQUID_INK": 1969  # Starting fair value
            }
        }

    def run(self, state: TradingState):
        # Load previous trader data
        if state.traderData:
            self.trader_data = json.loads(state.traderData)

        # Initialize inventory if not already present
        for product in state.order_depths.keys():
            if product not in self.trader_data["inventory"]:
                self.trader_data["inventory"][product] = 0

        # Update cash and inventory from trades
        self._update_from_trades(state)

        # Prepare the orders
        result = {}
        for product, order_depth in state.order_depths.items():
            fair_value = self.trader_data["fair_value"][product]
            inventory = self.trader_data["inventory"][product]

            # Determine spread and quote levels
            bid_price = fair_value - 1
            ask_price = fair_value + 1
            bid_quantity = 10
            ask_quantity = 10

            # Adjust bid/ask prices based on inventory
            if inventory > 0:
                bid_price += inventory // 5
                ask_price -= inventory // 5
            elif inventory < 0:
                bid_price -= abs(inventory) // 5
                ask_price += abs(inventory) // 5

            # Ensure we are within position limits
            max_position = 50
            if inventory + ask_quantity > max_position:
                ask_quantity = max_position - inventory
            if inventory - bid_quantity < -max_position:
                bid_quantity = inventory + max_position

            # Create orders
            orders = [
                Order(product, bid_price, bid_quantity),
                Order(product, ask_price, -ask_quantity)
            ]

            # Filter out invalid orders
            orders = [order for order in orders if self._is_order_valid(order, inventory)]

            result[product] = orders

        # Update trader data
        trader_data_str = json.dumps(self.trader_data)
        return result, 0, trader_data_str

    def _update_from_trades(self, state: TradingState):
        for product, trades in state.own_trades.items():
            for trade in trades:
                self.trader_data["cash"] += trade.price * trade.quantity
                self.trader_data["inventory"][product] += trade.quantity

    def _is_order_valid(self, order: Order, current_inventory: int) -> bool:
        max_position = 50
        if order.quantity > 0:  # Buy order
            return current_inventory + order.quantity <= max_position
        else:  # Sell order
            return current_inventory + order.quantity >= -max_position

# Ensure to include the datamodel module as per the competition's specification
