import json
from datamodel import Order, OrderDepth, TradingState

class Trader:
    def run(self, state: TradingState):
        result = {}
        conversions = 0
        traderData = ""  # no persistent state needed for this simple strategy

        for product, order_depth in state.order_depths.items():
            buy_orders = order_depth.buy_orders
            sell_orders = order_depth.sell_orders

            best_bid = max(buy_orders.keys()) if buy_orders else None
            best_ask = min(sell_orders.keys()) if sell_orders else None

            orders = []

            pos = state.position.get(product, 0)
            limit = 50
            max_buy = limit - pos
            max_sell = limit + pos

            # Buy side
            if best_ask is not None and max_buy > 0:
                qty = min(5, max_buy)
                if pos > 0:
                    bid_price = best_ask - 1
                    if bid_price < 0:
                        bid_price = 0
                else:
                    bid_price = best_ask
                orders.append(Order(product, bid_price, qty))

            # Sell side
            if best_bid is not None and max_sell > 0:
                qty = min(5, max_sell)
                if pos < 0:
                    ask_price = best_bid + 1
                else:
                    ask_price = best_bid
                if ask_price < 0:
                    ask_price = 0
                orders.append(Order(product, ask_price, -qty))

            result[product] = orders

        return result, conversions, traderData
