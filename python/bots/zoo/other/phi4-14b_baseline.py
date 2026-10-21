import json
from typing import List
from datamodel import Order, OrderDepth, TradingState, Trade

class Trader:
    def __init__(self):
        # Initialize state with default values
        self.state = {
            'rainforest_resin_position': 0,
            'kelp_sma': [],
            'kelp_window_size': 10,
            'kelp_last_prices': [],
            'squid_ink_mav': [],
            'squid_ink_window_size': 10,
            'squid_ink_last_prices': [],
            'cash': 0
        }

    def run(self, state: TradingState):
        result = {}
        
        # Decode traderData safely
        trader_data = self.safe_loads(state.traderData)
        if trader_data is not None:
            self.state.update(trader_data)

        # Execute trading strategies
        self.trade_rainforest_resin(state, result)
        self.trade_kelp(state, result)
        self.trade_squid_ink(state, result)

        # Serialize state to string for the next iteration
        trader_data = json.dumps(self.state)
        return result, 0, trader_data

    def safe_loads(self, data: str):
        """Safely load JSON, returning None if data is not valid JSON."""
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    def trade_rainforest_resin(self, state, result):
        order_depth = state.order_depths['RAINFOREST_RESIN']
        current_position = self.state['rainforest_resin_position']
        limit = 50

        # Simple strategy: hold a balanced position
        if current_position < limit:
            buy_quantity = min(limit - current_position, 10)
            if buy_quantity > 0:
                best_price = min(order_depth.buy_orders.keys())
                result['RAINFOREST_RESIN'] = [Order('RAINFOREST_RESIN', best_price, buy_quantity)]
        elif current_position > -limit:
            sell_quantity = min(current_position, 10)
            if sell_quantity > 0:
                best_price = max(order_depth.sell_orders.keys())
                result['RAINFOREST_RESIN'] = [Order('RAINFOREST_RESIN', best_price, -sell_quantity)]

    def trade_kelp(self, state, result):
        order_depth = state.order_depths['KELP']
        last_prices = self.state['kelp_last_prices']
        window_size = self.state['kelp_window_size']
        current_position = self.state['kelp_position'] if 'kelp_position' in self.state else 0
        limit = 50

        # Update prices
        mid_price = order_depth.sell_orders[min(order_depth.sell_orders.keys())] + \
                    order_depth.buy_orders[max(order_depth.buy_orders.keys())]
        last_prices.append(mid_price)
        if len(last_prices) > window_size:
            last_prices.pop(0)

        # Calculate SMA
        if len(last_prices) == window_size:
            sma = sum(last_prices) / window_size
            if current_position < limit:
                if mid_price < sma:
                    buy_quantity = min(limit - current_position, 10)
                    if buy_quantity > 0:
                        best_price = min(order_depth.buy_orders.keys())
                        result['KELP'] = [Order('KELP', best_price, buy_quantity)]
            elif current_position > -limit:
                if mid_price > sma:
                    sell_quantity = min(current_position, 10)
                    if sell_quantity > 0:
                        best_price = max(order_depth.sell_orders.keys())
                        result['KELP'] = [Order('KELP', best_price, -sell_quantity)]

        self.state['kelp_last_prices'] = last_prices

    def trade_squid_ink(self, state, result):
        order_depth = state.order_depths['SQUID_INK']
        last_prices = self.state['squid_ink_last_prices']
        window_size = self.state['squid_ink_window_size']
        current_position = self.state['squid_ink_position'] if 'squid_ink_position' in self.state else 0
        limit = 50

        # Update prices
        mid_price = order_depth.sell_orders[min(order_depth.sell_orders.keys())] + \
                    order_depth.buy_orders[max(order_depth.buy_orders.keys())]
        last_prices.append(mid_price)
        if len(last_prices) > window_size:
            last_prices.pop(0)

        # Calculate moving average
        if len(last_prices) == window_size:
            mav = sum(last_prices) / window_size
            deviation = mid_price - mav

            if current_position < limit:
                if deviation < -5:  # Buy if price is significantly below the moving average
                    buy_quantity = min(limit - current_position, 10)
                    if buy_quantity > 0:
                        best_price = min(order_depth.buy_orders.keys())
                        result['SQUID_INK'] = [Order('SQUID_INK', best_price, buy_quantity)]
            elif current_position > -limit:
                if deviation > 5:  # Sell if price is significantly above the moving average
                    sell_quantity = min(current_position, 10)
                    if sell_quantity > 0:
                        best_price = max(order_depth.sell_orders.keys())
                        result['SQUID_INK'] = [Order('SQUID_INK', best_price, -sell_quantity)]

        self.state['squid_ink_last_prices'] = last_prices
