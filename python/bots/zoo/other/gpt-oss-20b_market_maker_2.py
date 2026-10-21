import json
from datamodel import Order, TradingState, OrderDepth

class Trader:
    """
    Very simple market‑making strategy that always places a bid below the best ask
    and an ask above the best bid.  The order size is fixed at 5 contracts.
    Inventory is kept in the range [-20, +20] by reducing the side that
    increases the position.
    """

    MAX_POS = 50          # position limit per product
    QUANTITY = 5          # quantity per order
    SPREAD = 2            # tick spread around the mid price

    def run(self, state: TradingState):
        """
        Parameters
        ----------
        state : TradingState
            Current state of the market.

        Returns
        -------
        tuple
            (orders, conversions, traderData)
        """
        orders_by_product = {}
        conversions = 0
        # we do not need to persist anything across iterations for this simple strategy
        traderData = json.dumps({})  # empty dict serialized to JSON

        for symbol, depth in state.order_depths.items():
            # Best bid and ask prices
            if depth.buy_orders:
                best_bid = max(depth.buy_orders.keys())
            else:
                best_bid = None

            if depth.sell_orders:
                best_ask = min(depth.sell_orders.keys())
            else:
                best_ask = None

            # If the book is incomplete we skip this product
            if best_bid is None or best_ask is None:
                orders_by_product[symbol] = []
                continue

            # Mid price (integer division)
            mid = (best_bid + best_ask) // 2

            # Prices for our orders
            bid_price = mid - self.SPREAD // 2
            ask_price = mid + self.SPREAD // 2

            # Current position
            pos = state.position.get(symbol, 0)

            # Decide which side to trade based on inventory
            orders = []

            # Buy side
            if pos < 20 and pos + self.QUANTITY <= self.MAX_POS:
                orders.append(Order(symbol, bid_price, self.QUANTITY))

            # Sell side
            if pos > -20 and pos - self.QUANTITY >= -self.MAX_POS:
                orders.append(Order(symbol, ask_price, -self.QUANTITY))

            # Position limit rejection check
            # Total buy volume that would be filled
            total_buy = sum(o.quantity for o in orders if o.quantity > 0)
            # Total sell volume that would be filled
            total_sell = sum(-o.quantity for o in orders if o.quantity < 0)

            if total_buy > 0 and pos + total_buy > self.MAX_POS:
                orders = []  # reject all orders for this product
            if total_sell > 0 and pos - total_sell < -self.MAX_POS:
                orders = []  # reject all orders for this product

            orders_by_product[symbol] = orders

        return orders_by_product, conversions, traderData
