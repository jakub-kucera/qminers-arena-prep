import json
from datamodel import Order, OrderDepth, TradingState

class Trader:
    def __init__(self):
        self.trader_data = {}

    def run(self, state: TradingState):
        # Load trader data
        try:
            self.trader_data = json.loads(state.traderData)
        except json.JSONDecodeError:
            self.trader_data = {}

        result = {}  # symbol -> list of Order
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            current_pos = state.position.get(product, 0)
            max_pos = 50
            min_pos = -50

            buy_orders = order_depth.buy_orders
            sell_orders = order_depth.sell_orders

            best_bid = max(buy_orders.keys()) if buy_orders else None
            best_ask = min(sell_orders.keys()) if sell_orders else None

            if best_bid is not None and best_ask is not None:
                mid = (best_bid + best_ask) / 2
            else:
                mid = 0  # default mid price if no orders

            bid_price = int(mid - 0.5)
            ask_price = int(mid + 0.5)

            # Calculate maximum possible buy and sell quantities
            max_buy = max_pos - current_pos
            max_sell = current_pos - min_pos

            # Determine buy quantity
            buy_qty = 0
            if best_bid is None or bid_price > best_bid:
                if max_buy > 0:
                    buy_qty = min(1, max_buy)  # send 1 unit per iteration

            # Determine sell quantity
            sell_qty = 0
            if best_ask is None or ask_price < best_ask:
                if max_sell > 0:
                    sell_qty = min(1, max_sell)

            # Check if sum of deltas is within position limits
            sum_delta = buy_qty - sell_qty
            new_pos = current_pos + sum_delta

            orders_for_product = []
            if buy_qty > 0 and new_pos <= max_pos:
                orders_for_product.append(Order(product, bid_price, buy_qty))
            if sell_qty > 0 and new_pos >= min_pos:
                orders_for_product.append(Order(product, ask_price, -sell_qty))

            # Ensure that if both orders are placed, their combined effect doesn't exceed limits
            if len(orders_for_product) > 0:
                result[product] = orders_for_product

            # Update trader data
            self.trader_data[product] = {
                'last_bid': bid_price,
                'last_ask': ask_price,
                'current_pos': current_pos
            }

        # Convert trader data back to string
        traderData = json.dumps(self.trader_data)
        return result, 0, traderData
