import json
from typing import Dict, List, Tuple
from datamodel import OrderDepth, TradingState, Order

class Trader:
    POSITION_LIMIT = 50

    def __init__(self):
        pass

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        conversions = 0

        # Load persistent state
        memory = {}
        if state.traderData:
            try:
                memory = json.loads(state.traderData)
            except Exception:
                memory = {}

        if "ema" not in memory:
            memory["ema"] = {}

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Current position
            pos = state.position.get(product, 0)
            buy_capacity = self.POSITION_LIMIT - pos
            sell_capacity = self.POSITION_LIMIT + pos  # max quantity we can sell (positive int)

            buy_orders = order_depth.buy_orders
            sell_orders = order_depth.sell_orders

            if not buy_orders and not sell_orders:
                result[product] = orders
                continue

            sorted_bids = sorted(buy_orders.keys(), reverse=True)
            sorted_asks = sorted(sell_orders.keys())

            best_bid = sorted_bids[0] if sorted_bids else None
            best_ask = sorted_asks[0] if sorted_asks else None

            # Calculate mid price & order-book weighted mid price
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2.0
                bid_vol = buy_orders[best_bid]
                ask_vol = abs(sell_orders[best_ask])
                vwap_mid = (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)
            elif best_bid is not None:
                mid_price = float(best_bid)
                vwap_mid = float(best_bid)
            else:
                mid_price = float(best_ask)
                vwap_mid = float(best_ask)

            # Determine fair value per product
            if product == "RAINFOREST_RESIN":
                fair_price = 10000.0
            elif product == "KELP":
                prev_ema = memory["ema"].get(product, mid_price)
                alpha = 0.2
                current_ema = alpha * vwap_mid + (1 - alpha) * prev_ema
                memory["ema"][product] = current_ema
                fair_price = 0.5 * current_ema + 0.5 * vwap_mid
            elif product == "SQUID_INK":
                prev_ema = memory["ema"].get(product, mid_price)
                alpha = 0.35
                current_ema = alpha * vwap_mid + (1 - alpha) * prev_ema
                memory["ema"][product] = current_ema
                fair_price = 0.6 * vwap_mid + 0.4 * current_ema
            else:
                prev_ema = memory["ema"].get(product, mid_price)
                current_ema = 0.25 * mid_price + 0.75 * prev_ema
                memory["ema"][product] = current_ema
                fair_price = current_ema

            # Inventory skew adjustment
            pos_ratio = pos / float(self.POSITION_LIMIT)
            if product == "RAINFOREST_RESIN":
                skew_mult = 1.0
            elif product == "SQUID_INK":
                skew_mult = 2.5
            else:
                skew_mult = 1.5

            adj_fair = fair_price - (pos_ratio * skew_mult)

            # 1. Taker logic: Snatch mispriced orders from book
            # Buy underpriced asks
            for ask_p in sorted_asks:
                ask_v = abs(sell_orders[ask_p])
                # Condition to take ask
                take_cond = False
                if product == "RAINFOREST_RESIN":
                    if ask_p < 10000 or (pos < 0 and ask_p == 10000):
                        take_cond = True
                else:
                    if ask_p <= adj_fair - 0.7:
                        take_cond = True

                if take_cond and buy_capacity > 0:
                    qty = min(ask_v, buy_capacity)
                    orders.append(Order(product, ask_p, qty))
                    buy_capacity -= qty

            # Sell overpriced bids
            for bid_p in sorted_bids:
                bid_v = buy_orders[bid_p]
                # Condition to take bid
                take_cond = False
                if product == "RAINFOREST_RESIN":
                    if bid_p > 10000 or (pos > 0 and bid_p == 10000):
                        take_cond = True
                else:
                    if bid_p >= adj_fair + 0.7:
                        take_cond = True

                if take_cond and sell_capacity > 0:
                    qty = min(bid_v, sell_capacity)
                    orders.append(Order(product, bid_p, -qty))
                    sell_capacity -= qty

            # 2. Maker logic: Passive quoting to earn spread
            if best_bid is not None and best_ask is not None:
                spread = best_ask - best_bid

                # Determine maker bid price
                if product == "RAINFOREST_RESIN":
                    if pos > 35:
                        quote_bid = 9996
                    elif pos > 20:
                        quote_bid = 9997
                    elif pos < -35:
                        quote_bid = 10000
                    elif pos < -20:
                        quote_bid = 9999
                    else:
                        quote_bid = 9998 if best_bid < 9998 else (best_bid + 1 if spread > 1 and best_bid + 1 < 10000 else 9998)
                else:
                    target_bid = int(round(adj_fair - 1.0))
                    if spread > 1:
                        if pos_ratio > 0.6:
                            quote_bid = best_bid
                        else:
                            quote_bid = min(best_bid + 1, target_bid)
                    else:
                        quote_bid = min(best_bid, target_bid)
                    quote_bid = min(quote_bid, int(adj_fair - 0.5))

                # Determine maker ask price
                if product == "RAINFOREST_RESIN":
                    if pos < -35:
                        quote_ask = 10004
                    elif pos < -20:
                        quote_ask = 10003
                    elif pos > 35:
                        quote_ask = 10000
                    elif pos > 20:
                        quote_ask = 10001
                    else:
                        quote_ask = 10002 if best_ask > 10002 else (best_ask - 1 if spread > 1 and best_ask - 1 > 10000 else 10002)
                else:
                    target_ask = int(round(adj_fair + 1.0))
                    if spread > 1:
                        if pos_ratio < -0.6:
                            quote_ask = best_ask
                        else:
                            quote_ask = max(best_ask - 1, target_ask)
                    else:
                        quote_ask = max(best_ask, target_ask)
                    quote_ask = max(quote_ask, int(adj_fair + 0.5))

                # Safety: Ensure maker bid is strictly lower than maker ask
                if quote_bid >= quote_ask:
                    quote_bid = quote_ask - 1

                # Send passive orders if capacity remains
                if buy_capacity > 0:
                    orders.append(Order(product, quote_bid, buy_capacity))
                    buy_capacity = 0

                if sell_capacity > 0:
                    orders.append(Order(product, quote_ask, -sell_capacity))
                    sell_capacity = 0

            # Aggregate and strictly enforce position limit constraints
            orders_by_price: Dict[int, int] = {}
            for o in orders:
                orders_by_price[o.price] = orders_by_price.get(o.price, 0) + o.quantity

            final_orders: List[Order] = []
            cur_buy = 0
            cur_sell = 0
            max_buy = self.POSITION_LIMIT - pos
            max_sell = self.POSITION_LIMIT + pos

            for p, q in orders_by_price.items():
                if q > 0:
                    allowed_q = min(q, max_buy - cur_buy)
                    if allowed_q > 0:
                        final_orders.append(Order(product, p, allowed_q))
                        cur_buy += allowed_q
                elif q < 0:
                    needed_sell = abs(q)
                    allowed_q = min(needed_sell, max_sell - cur_sell)
                    if allowed_q > 0:
                        final_orders.append(Order(product, p, -allowed_q))
                        cur_sell += allowed_q

            result[product] = final_orders

        traderData = json.dumps(memory)
        return result, conversions, traderData
