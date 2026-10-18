import json
from datamodel import OrderDepth, TradingState, Order
from typing import List


class Trader:
    def run(self, state: TradingState):
        result = {}

        # Load persistent state from traderData
        if state.traderData:
            try:
                data = json.loads(state.traderData)
            except (json.JSONDecodeError, TypeError, ValueError):
                data = {"mids": {}}
        else:
            data = {"mids": {}}

        total_iterations = 10000
        iteration = state.timestamp // 100

        for product in state.order_depths:
            order_depth = state.order_depths[product]
            orders: List[Order] = []

            if not order_depth.buy_orders or not order_depth.sell_orders:
                result[product] = []
                continue

            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            mid = (best_bid + best_ask) / 2.0
            spread = best_ask - best_bid
            position = state.position.get(product, 0)
            limit = 50

            # Update mid history
            if product not in data["mids"]:
                data["mids"][product] = []
            data["mids"][product].append(mid)
            if len(data["mids"][product]) > 60:
                data["mids"][product] = data["mids"][product][-60:]

            # Product-specific parameters
            if product == "RAINFOREST_RESIN":
                alpha = 0.06
                momentum_wt = 0.0
                take_threshold = max(5, spread)
                mm_qty = 6
                inv_coef = 0.15
            elif product == "KELP":
                alpha = 0.12
                momentum_wt = 0.25
                take_threshold = max(4, spread)
                mm_qty = 5
                inv_coef = 0.2
            else:  # SQUID_INK
                alpha = 0.2
                momentum_wt = 0.5
                take_threshold = max(6, spread + 2)
                mm_qty = 4
                inv_coef = 0.25

            # Fair value: exponential weighted average of recent mids
            mids = data["mids"][product]
            n = len(mids)
            if n == 1:
                fair_value = mids[0]
            else:
                fv = mids[-1]
                for i in range(1, min(n, 30)):
                    fv = mids[-(i + 1)] + alpha * (fv - mids[-(i + 1)])
                fair_value = fv

            # Add momentum component
            if n >= 4:
                momentum = (mids[-1] - mids[-min(n, 5)]) / min(3, n - 1)
                fair_value += momentum * momentum_wt

            # End-of-day: flatten positions
            if iteration > 9000:
                urgency = (iteration - 9000) / 1000.0  # 0 to 1
                fair_value -= position * urgency * 0.5

            # Inventory adjustment: shift fair value to encourage reducing position
            adj_fv = fair_value - position * inv_coef

            # Quote prices around adjusted fair value
            half_spread = max(1, spread // 2)
            bid_price = int(round(adj_fv - half_spread))
            ask_price = int(round(adj_fv + half_spread))

            # Ensure bid < ask
            if bid_price >= ask_price:
                mid_int = int(round(adj_fv))
                bid_price = mid_int - 1
                ask_price = mid_int + 1

            # Clamp to avoid crossing the spread (for market making)
            bid_price = min(bid_price, best_ask - 1)
            ask_price = max(ask_price, best_bid + 1)
            bid_price = max(bid_price, 1)
            ask_price = min(ask_price, 999999)

            # Max quantities based on position limits
            max_buy = max(0, limit - position)
            max_sell = max(0, position + limit)

            total_buy = 0
            total_sell = 0

            # --- Taking decisions ---
            # Buy at best_ask if it's well below fair value
            if best_ask <= fair_value - take_threshold and max_buy > 0:
                qty = min(mm_qty, max_buy)
                orders.append(Order(product, best_ask, qty))
                total_buy += qty

            # Sell at best_bid if it's well above fair value
            if best_bid >= fair_value + take_threshold and max_sell > 0:
                qty = min(mm_qty, max_sell)
                orders.append(Order(product, best_bid, -qty))
                total_sell += qty

            # --- Market making ---
            # Quote bid if we can still buy and haven't taken
            if total_buy == 0 and max_buy > 0 and position < limit - 1:
                qty = min(mm_qty, max_buy)
                # Reduce size when heavily long
                if position > 25:
                    qty = max(1, qty // 2)
                # Near limit: be very conservative
                if position > 40:
                    qty = 1
                orders.append(Order(product, bid_price, qty))
                total_buy += qty

            # Quote ask if we can still sell and haven't taken
            if total_sell == 0 and max_sell > 0 and position > -(limit - 1):
                qty = min(mm_qty, max_sell)
                # Reduce size when heavily short
                if position < -25:
                    qty = max(1, qty // 2)
                # Near limit: be very conservative
                if position < -40:
                    qty = 1
                orders.append(Order(product, ask_price, -qty))
                total_sell += qty

            # Safety: enforce position limits
            if total_buy > 0 and position + total_buy > limit:
                excess = position + total_buy - limit
                # Remove buy orders (keep sell orders)
                orders = [o for o in orders if o.quantity < 0]
                # Add back reduced buy
                remaining_buy = max(0, total_buy - excess)
                if remaining_buy > 0:
                    # Find the price of the first buy order we had
                    for o in orders:
                        pass
                    # Re-add a buy at bid_price or best_ask
                    if best_ask <= fair_value - take_threshold:
                        orders.append(Order(product, best_ask, remaining_buy))
                    elif bid_price < best_ask:
                        orders.append(Order(product, bid_price, remaining_buy))

            if total_sell > 0 and position - total_sell < -limit:
                excess = total_sell - (position + limit)
                orders = [o for o in orders if o.quantity > 0]
                remaining_sell = max(0, total_sell - excess)
                if remaining_sell > 0:
                    if best_bid >= fair_value + take_threshold:
                        orders.append(Order(product, best_bid, -remaining_sell))
                    elif ask_price > best_bid:
                        orders.append(Order(product, ask_price, -remaining_sell))

            result[product] = orders

        traderData = json.dumps(data)
        return result, 0, traderData
