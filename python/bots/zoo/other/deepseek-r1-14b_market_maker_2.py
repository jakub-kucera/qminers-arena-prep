import json
from datamodel import Order, OrderDepth, TradingState, Trade

class Trader:
    def run(self, state: TradingState):
        result = {}  # symbol -> list of Order
        traderData = state.traderData
        data = json.loads(traderData) if traderData else {}

        # Initialize data structure if not present
        if 'mid_prices' not in data:
            data['mid_prices'] = {}
        if 'positions' not in data:
            data['positions'] = {}

        for product in state.order_depths:
            order_depth = state.order_depths[product]
            current_pos = state.position.get(product, 0)
            data['positions'][product] = current_pos

            # Calculate mid price
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
                data['mid_prices'][product] = mid_price
            else:
                mid_price = None

            # Determine quantities based on position limits
            max_buy = 50 - current_pos
            max_sell = -50 - current_pos
            quantity_buy = max_buy if max_buy > 0 else 0
            quantity_sell = -max_sell if max_sell < 0 else 0

            # Calculate bid and ask prices
            orders = []
            if mid_price is not None:
                bid_price = int(mid_price - 1)
                ask_price = int(mid_price + 1)

                if quantity_buy > 0:
                    orders.append(Order(product, bid_price, quantity_buy))
                if quantity_sell > 0:
                    orders.append(Order(product, ask_price, -quantity_sell))
            result[product] = orders

        # Update traderData
        new_traderData = json.dumps(data)
        conversions = 0
        return result, conversions, new_traderData
