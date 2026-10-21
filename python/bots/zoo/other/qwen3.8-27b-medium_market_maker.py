import json
from datamodel import OrderDepth, TradingState, Order
from typing import List

class Trader:
    def run(self, state: TradingState):
        result = {}

        # --- Parse persistent state ---
        if state.traderData:
            try:
                data = json.loads(state.traderData)
            except (json.JSONDecodeError, TypeError):
                data = {}
        else:
            data = {}
        if "fv" not in data:
            data["fv"] = {}
        if "n" not in data:
            data["n"] = {}

        for product in state.order_depths:
            od = state.order_depths[product]
            orders: List[Order] = []

            bids = od.buy_orders     # {price: positive_volume}
            asks = od.sell_orders    # {price: negative_volume}

            if not bids and not asks:
                result[product] = []
                continue

            bb = max(bids.keys()) if bids else 0
            ba = min(asks.keys()) if asks else None

            if bb > 0 and ba is not None and ba > bb:
                mid = (bb + ba) / 2.0
                spread = ba - bb
            elif bb > 0:
                mid = float(bb)
                spread = 4
            elif ba is not None:
                mid = float(ba)
                spread = 4
            else:
                result[product] = []
                continue

            # --- Fair value (EWMA of mid price) ---
            data["n"][product] = data["n"].get(product, 0) + 1
            n = data["n"][product]

            if product not in data["fv"]:
                data["fv"][product] = mid
            else:
                alphas = {"RAINFOREST_RESIN": 0.02, "KELP": 0.04, "SQUID_INK": 0.08}
                alpha = alphas.get(product, 0.05)
                # Blend with current mid more in early iterations
                if n < 20:
                    alpha = max(alpha, 0.2)
                data["fv"][product] = alpha * mid + (1.0 - alpha) * data["fv"][product]

            fv = data["fv"][product]
            pos = state.position.get(product, 0)
            lim = 50

            # --- Product-specific parameters ---
            if product == "RAINFOREST_RESIN":
                base_qty = 8
                make_thresh = 3
                take_thresh = 4
            elif product == "KELP":
                base_qty = 5
                make_thresh = 4
                take_thresh = 5
            else:
                base_qty = 3
                make_thresh = 5
                take_thresh = 6

            # --- Inventory-aware sizing ---
            inv_ratio = pos / lim  # -1 to +1
            size_factor = max(0.2, 1.0 - abs(inv_ratio) * 0.7)
            adj_qty = max(1, int(base_qty * size_factor))

            # --- Market making (passive quotes) ---
            # Quote at best bid / best ask to be competitive
            # Only quote if consistent with fair value
            make_bid_ok = (bb <= fv + make_thresh)
            make_ask_ok = (ba is not None and ba >= fv - make_thresh)

            # Don't add to inventory beyond 60% of limit
            if pos > lim * 0.6:
                make_bid_ok = False
            if pos < -lim * 0.6:
                make_ask_ok = False

            # Don't quote into the limit
            if pos >= lim - 1:
                make_bid_ok = False
            if pos <= -lim + 1:
                make_ask_ok = False

            make_bid_qty = adj_qty if make_bid_ok else 0
            make_ask_qty = adj_qty if make_ask_ok else 0

            # --- Taking (aggressive, cross the spread) ---
            take_buy_qty = 0
            take_buy_price = 0
            take_sell_qty = 0
            take_sell_price = 0

            # Buy at best ask if it's well below fair value
            if ba is not None and ba < fv - take_thresh:
                avail = -asks.get(ba, -1)
                room = max(0, lim - pos - make_bid_qty)
                take_buy_qty = min(adj_qty, avail, room)
                if take_buy_qty > 0:
                    take_buy_price = ba

            # Sell at best bid if it's well above fair value
            if bb > fv + take_thresh:
                avail = bids.get(bb, 1)
                room = max(0, pos + lim - make_ask_qty)
                take_sell_qty = min(adj_qty, avail, room)
                if take_sell_qty > 0:
                    take_sell_price = bb

            # --- Position limit enforcement ---
            total_buy = make_bid_qty + take_buy_qty
            total_sell = make_ask_qty + take_sell_qty

            if pos + total_buy > lim:
                excess = pos + total_buy - lim
                take_buy_qty = max(0, take_buy_qty - excess)
                excess = pos + make_bid_qty + take_buy_qty - lim
                if excess > 0:
                    make_bid_qty = max(0, make_bid_qty - excess)
                total_buy = make_bid_qty + take_buy_qty

            if pos - total_sell < -lim:
                excess = -(pos - total_sell) - lim
                take_sell_qty = max(0, take_sell_qty - excess)
                excess = -(pos - make_ask_qty - take_sell_qty) - lim
                if excess > 0:
                    make_ask_qty = max(0, make_ask_qty - excess)
                total_sell = make_ask_qty + take_sell_qty

            # --- Place orders ---
            if make_bid_qty > 0 and bb > 0:
                orders.append(Order(product, bb, make_bid_qty))

            if make_ask_qty > 0 and ba is not None and ba > 0:
                orders.append(Order(product, ba, -make_ask_qty))

            if take_buy_qty > 0 and take_buy_price > 0:
                orders.append(Order(product, take_buy_price, take_buy_qty))

            if take_sell_qty > 0 and take_sell_price > 0:
                orders.append(Order(product, take_sell_price, -take_sell_qty))

            result[product] = orders

        traderData = json.dumps(data)
        return result, 0, traderData
