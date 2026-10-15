import json
from typing import List, Dict

from datamodel import OrderDepth, TradingState, Order


class Trader:
    """Simple market‑making trader.

    * Maintains a short moving‑average of recent mid‑prices for each product.
    * Uses that average as a fair‑value estimate.
    * Places passive limit orders a few shells away from the fair value.
    * Takes any existing orders that are priced more favorably than the estimate.
    * Keeps inventory within the ±50‑unit position limits.
    """

    # How many recent mid‑prices to keep for the moving average.
    HISTORY_LEN = 20
    # Number of shells to stay away from the fair value when quoting.
    SPREAD = 2
    # Maximum order size the trader will send in a single iteration.
    MAX_ORDER_SIZE = 20

    def _update_history(self, history: Dict[str, List[int]], product: str, mid: float) -> None:
        """Append a new mid‑price to the rolling history for *product*."""
        lst = history.setdefault(product, [])
        lst.append(mid)
        if len(lst) > self.HISTORY_LEN:
            lst.pop(0)

    def _fair_price(self, history: Dict[str, List[int]], product: str, fallback: float) -> float:
        """Return the average of the stored mids, or *fallback* if no history yet."""
        lst = history.get(product, [])
        if not lst:
            return fallback
        return sum(lst) / len(lst)

    def run(self, state: TradingState):
        """Return (orders_by_product, conversions, trader_data)."""
        # ------------------------------------------------------------------
        # Load persistent data from the previous iteration.
        # ------------------------------------------------------------------
        if state.traderData:
            try:
                trader_data = json.loads(state.traderData)
            except Exception:
                trader_data = {}
        else:
            trader_data = {}

        # History of recent mids, e.g. {"RAINFOREST_RESIN": [9999.5, 10001.0, ...], ...}
        history = trader_data.get("mid_history", {})

        # Prepare the container for this iteration's orders.
        orders_by_product: Dict[str, List[Order]] = {}

        # ------------------------------------------------------------------
        # Process each product independently.
        # ------------------------------------------------------------------
        for product, depth in state.order_depths.items():
            # ------------------------------------------------------------------
            # 1) Compute the current mid‑price from the order book.
            # ------------------------------------------------------------------
            best_bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
            best_ask = min(depth.sell_orders.keys()) if depth.sell_orders else None

            # Mid‑price is the average of the best bid and best ask when both exist.
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2.0
            elif best_bid is not None:
                mid_price = float(best_bid)
            elif best_ask is not None:
                mid_price = float(best_ask)
            else:
                # Empty book – cannot price; skip this product this iteration.
                orders_by_product[product] = []
                continue

            # ------------------------------------------------------------------
            # 2) Update and fetch the fair‑value estimate.
            # ------------------------------------------------------------------
            self._update_history(history, product, mid_price)
            fair = self._fair_price(history, product, mid_price)

            # ------------------------------------------------------------------
            # 3) Determine how much we can still buy / sell respecting limits.
            # ------------------------------------------------------------------
            position = state.position.get(product, 0)
            limit = 50  # all products share the same limit in the spec
            can_buy = limit - position          # positive if we may buy more
            can_sell = limit + position         # positive if we may sell more (since selling reduces position)

            # ------------------------------------------------------------------
            # 4) Build the order list.
            # ------------------------------------------------------------------
            product_orders: List[Order] = []

            # --------------------------------------------------------------
            # 4a) Aggressively capture mis‑priced orders already on the book.
            # --------------------------------------------------------------
            # If the best ask is cheaper than our fair value, buy it.
            if best_ask is not None and best_ask < fair and can_buy > 0:
                volume_at_ask = -depth.sell_orders[best_ask]  # sell_orders store negative volumes
                qty = min(self.MAX_ORDER_SIZE, can_buy, volume_at_ask)
                if qty > 0:
                    product_orders.append(Order(product, best_ask, qty))  # positive = buy

            # If the best bid is higher than our fair value, sell into it.
            if best_bid is not None and best_bid > fair and can_sell > 0:
                volume_at_bid = depth.buy_orders[best_bid]
                qty = min(self.MAX_ORDER_SIZE, can_sell, volume_at_bid)
                if qty > 0:
                    product_orders.append(Order(product, best_bid, -qty))  # negative = sell

            # --------------------------------------------------------------
            # 4b) Post passive quotes around the fair value.
            # --------------------------------------------------------------
            # Desired passive bid/ask prices (rounded to integers).
            bid_price = int(fair) - self.SPREAD
            ask_price = int(fair) + self.SPREAD

            # Only place a bid if we still have buying capacity.
            if can_buy > 0 and (best_bid is None or bid_price > best_bid):
                qty = min(self.MAX_ORDER_SIZE, can_buy)
                product_orders.append(Order(product, bid_price, qty))

            # Only place an ask if we still have selling capacity.
            if can_sell > 0 and (best_ask is None or ask_price < best_ask):
                qty = min(self.MAX_ORDER_SIZE, can_sell)
                product_orders.append(Order(product, ask_price, -qty))

            # ------------------------------------------------------------------
            # 5) Store the orders for this product.
            # ------------------------------------------------------------------
            orders_by_product[product] = product_orders

        # ------------------------------------------------------------------
        # Persist the updated history for the next iteration.
        # ------------------------------------------------------------------
        trader_data["mid_history"] = history
        trader_data_str = json.dumps(trader_data)

        # No conversions in this round.
        conversions = 0

        return orders_by_product, conversions, trader_data_str
