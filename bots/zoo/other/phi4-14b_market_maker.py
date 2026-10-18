import json
from typing import List, Dict
from datamodel import Order, OrderDepth, TradingState, Trade

class Trader:
    def __init__(self):
        self.fair_values = {}  # To store estimated fair values
        self.last_mid_prices = {}  # To store last mid prices
        self.position_limits = {'RAINFOREST_RESIN': 50, 'KELP': 50, 'SQUID_INK': 50}
        self.bids_spread = 1
        self.asks_spread = 1
        self.max_inventory = 10

    def run(self, state: TradingState):
        result = {}  # symbol -> list of Order
        trader_data = json.loads(state.traderData or '{}')

        # Update fair values and last mid prices
        for product, order_depth in state.order_depths.items():
            mid_price = (min(order_depth.sell_orders) + max(order_depth.buy_orders)) / 2
            self.last_mid_prices[product] = mid_price

            if product in trader_data.get('fair_values', {}):
                self.fair_values[product] = (self.fair_values[product] + mid_price) / 2
            else:
                self.fair_values[product] = mid_price

        # Prepare orders
        for product, order_depth in state.order_depths.items():
            current_position = state.position.get(product, 0)
            inventory = abs(current_position)

            # Determine bid and ask prices based on fair value
            bid_price = int(self.fair_values[product]) - self.bids_spread
            ask_price = int(self.fair_values[product]) + self.asks_spread

            # Ensure we don't exceed position limits
            max_bid_quantity = self.position_limits[product] - inventory
            max_ask_quantity = self.position_limits[product] - (self.position_limits[product] - inventory)

            if max_bid_quantity > 0:
                result[product] = [Order(product, bid_price, min(max_bid_quantity, self.max_inventory))]
            else:
                result[product] = []

            if max_ask_quantity > 0:
                result[product].append(Order(product, ask_price, -min(max_ask_quantity, self.max_inventory)))
            else:
                result[product] = result.get(product, [])

        # Prepare trader data for the next iteration
        trader_data['fair_values'] = self.fair_values
        trader_data_json = json.dumps(trader_data)

        return result, 0, trader_data_json

# The datamodel module is assumed to be provided by the exchange as described.
