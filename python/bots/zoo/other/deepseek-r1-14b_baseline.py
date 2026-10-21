import json

class Trader:
    def __init__(self):
        self.trader_data = {}

    def run(self, state: 'TradingState') -> ('dict', int, str):
        result = {}
        current_trader_data = state.traderData
        trader_state = json.loads(current_trader_data) if current_trader_data else {}

        for product in state.order_depths:
            orders = []
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)

            # Calculate best bid and ask
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

            # Calculate mid price
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
            else:
                mid_price = None

            # Get or initialize product state
            product_state = trader_state.get(product, {
                'position': position,
                'price_history': [],
                'ma_window': 200,
                'ma_value': None,
            })

            # Update price history
            if mid_price is not None:
                product_state['price_history'].append(mid_price)
                # Maintain the length of price_history to be at most ma_window
                if len(product_state['price_history']) > product_state['ma_window']:
                    product_state['price_history'].pop(0)

            # Calculate moving average
            if product_state['price_history']:
                ma_value = sum(product_state['price_history']) / len(product_state['price_history'])
                product_state['ma_value'] = ma_value
            else:
                product_state['ma_value'] = None

            # Determine if we should buy or sell
            if product_state['ma_value'] is not None and mid_price is not None:
                if mid_price > product_state['ma_value']:
                    # Consider buying if not at max position
                    if position < 50:
                        if best_ask is not None:
                            orders.append(Order(product, best_ask, 1))
                elif mid_price < product_state['ma_value']:
                    # Consider selling if not at min position
                    if position > -50:
                        if best_bid is not None:
                            orders.append(Order(product, best_bid, -1))

            # Update the orders for this product
            result[product] = orders

            # Update the product's state in trader_state
            trader_state[product] = product_state

        # Serialize the updated trader_state
        new_trader_data = json.dumps(trader_state)
        return result, 0, new_trader_data
