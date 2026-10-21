import json
from typing import List, Dict, Any
from datamodel import OrderDepth, TradingState, Order


class OrderManager:
    """
    Strictly enforces position limits and manages order collection for a product.
    Guarantees sum(buys) <= LIMIT - pos and sum(abs(sells)) <= LIMIT + pos.
    """
    def __init__(self, symbol: str, limit: int, current_pos: int):
        self.symbol = symbol
        self.limit = limit
        self.current_pos = current_pos
        self.buy_budget = max(0, limit - current_pos)
        self.sell_budget = max(0, limit + current_pos)
        self.buy_orders: Dict[int, int] = {}   # price -> quantity (> 0)
        self.sell_orders: Dict[int, int] = {}  # price -> quantity (> 0, absolute)
        self.total_bought = 0
        self.total_sold = 0

    def buy(self, price: int, quantity: int) -> int:
        price = int(round(price))
        quantity = int(quantity)
        if quantity <= 0:
            return 0
        fill_qty = min(quantity, self.buy_budget)
        if fill_qty > 0:
            self.buy_orders[price] = self.buy_orders.get(price, 0) + fill_qty
            self.buy_budget -= fill_qty
            self.total_bought += fill_qty
            return fill_qty
        return 0

    def sell(self, price: int, quantity: int) -> int:
        price = int(round(price))
        quantity = int(quantity)
        if quantity <= 0:
            return 0
        fill_qty = min(quantity, self.sell_budget)
        if fill_qty > 0:
            self.sell_orders[price] = self.sell_orders.get(price, 0) + fill_qty
            self.sell_budget -= fill_qty
            self.total_sold += fill_qty
            return fill_qty
        return 0

    @property
    def effective_pos(self) -> int:
        return self.current_pos + self.total_bought - self.total_sold

    def get_orders(self) -> List[Order]:
        orders: List[Order] = []
        for p, q in self.buy_orders.items():
            if q > 0:
                orders.append(Order(self.symbol, p, q))
        for p, q in self.sell_orders.items():
            if q > 0:
                orders.append(Order(self.symbol, p, -q))
        return orders


class Trader:
    def trade_rainforest_resin(self, order_depth: OrderDepth, pos: int, memory: dict) -> List[Order]:
        om = OrderManager("RAINFOREST_RESIN", 50, pos)
        fair_value = 10000

        sorted_asks = sorted(order_depth.sell_orders.items(), key=lambda x: x[0])
        sorted_bids = sorted(order_depth.buy_orders.items(), key=lambda x: x[0], reverse=True)

        # 1. Take mispriced orders
        for ask_p, ask_v in sorted_asks:
            avail = -ask_v
            if ask_p <= 9998:
                om.buy(ask_p, avail)
            elif ask_p == 9999 and om.effective_pos < 0:
                cover_qty = min(avail, -om.effective_pos)
                om.buy(ask_p, cover_qty)

        for bid_p, bid_v in sorted_bids:
            avail = bid_v
            if bid_p >= 10002:
                om.sell(bid_p, avail)
            elif bid_p == 10001 and om.effective_pos > 0:
                dump_qty = min(avail, om.effective_pos)
                om.sell(bid_p, dump_qty)

        # 2. Market Making with Inventory Skew
        eff_pos = om.effective_pos

        # Passive Bid
        if om.buy_budget > 0:
            if eff_pos < -15:
                bid_p = 9999
            elif eff_pos < 25:
                bid_p = 9998
            elif eff_pos < 45:
                bid_p = 9997
            else:
                bid_p = None
            if bid_p is not None:
                om.buy(bid_p, om.buy_budget)

        # Passive Ask
        if om.sell_budget > 0:
            if eff_pos > 15:
                ask_p = 10001
            elif eff_pos > -25:
                ask_p = 10002
            elif eff_pos > -45:
                ask_p = 10003
            else:
                ask_p = None
            if ask_p is not None:
                om.sell(ask_p, om.sell_budget)

        return om.get_orders()

    def trade_kelp(self, order_depth: OrderDepth, pos: int, memory: dict) -> List[Order]:
        om = OrderManager("KELP", 50, pos)

        sorted_asks = sorted(order_depth.sell_orders.items(), key=lambda x: x[0])
        sorted_bids = sorted(order_depth.buy_orders.items(), key=lambda x: x[0], reverse=True)

        if not sorted_asks and not sorted_bids:
            return []

        best_ask = sorted_asks[0][0] if sorted_asks else 2032
        ask_vol = -sorted_asks[0][1] if sorted_asks else 1
        best_bid = sorted_bids[0][0] if sorted_bids else 2028
        bid_vol = sorted_bids[0][1] if sorted_bids else 1

        mid = (best_bid + best_ask) / 2.0
        micro = (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)

        kelp_mem = memory.get("KELP", {})
        ema = kelp_mem.get("ema", mid)
        ema = 0.3 * micro + 0.7 * ema
        kelp_mem["ema"] = ema

        mid_history = kelp_mem.get("mid_history", [])
        mid_history.append(mid)
        kelp_mem["mid_history"] = mid_history[-30:]
        memory["KELP"] = kelp_mem

        fair_value = 0.6 * micro + 0.4 * ema

        # 1. Take mispriced orders
        for ask_p, ask_v in sorted_asks:
            avail = -ask_v
            if ask_p <= fair_value - 1.0:
                om.buy(ask_p, avail)
            elif ask_p < fair_value - 0.2 and om.effective_pos < 0:
                cover_qty = min(avail, -om.effective_pos)
                om.buy(ask_p, cover_qty)

        for bid_p, bid_v in sorted_bids:
            avail = bid_v
            if bid_p >= fair_value + 1.0:
                om.sell(bid_p, avail)
            elif bid_p > fair_value + 0.2 and om.effective_pos > 0:
                dump_qty = min(avail, om.effective_pos)
                om.sell(bid_p, dump_qty)

        # 2. Market Making with Inventory Skew
        eff_pos = om.effective_pos
        inv_skew = 1.5 * (eff_pos / 50.0)
        res_price = fair_value - inv_skew

        # Passive Bid
        if om.buy_budget > 0:
            target_bid = int(res_price - 0.5)
            if best_ask - best_bid >= 2:
                penny_bid = best_bid + 1
                if penny_bid <= target_bid:
                    my_bid = penny_bid
                else:
                    my_bid = min(best_bid, target_bid)
            else:
                my_bid = min(best_bid, target_bid)
            my_bid = min(my_bid, best_ask - 1)
            if my_bid > 0:
                om.buy(my_bid, om.buy_budget)

        # Passive Ask
        if om.sell_budget > 0:
            target_ask = int(res_price + 0.5)
            if target_ask <= res_price:
                target_ask += 1
            if best_ask - best_bid >= 2:
                penny_ask = best_ask - 1
                if penny_ask >= target_ask:
                    my_ask = penny_ask
                else:
                    my_ask = max(best_ask, target_ask)
            else:
                my_ask = max(best_ask, target_ask)
            my_ask = max(my_ask, best_bid + 1)
            if my_ask > 0:
                om.sell(my_ask, om.sell_budget)

        return om.get_orders()

    def trade_squid_ink(self, order_depth: OrderDepth, pos: int, memory: dict) -> List[Order]:
        om = OrderManager("SQUID_INK", 50, pos)

        sorted_asks = sorted(order_depth.sell_orders.items(), key=lambda x: x[0])
        sorted_bids = sorted(order_depth.buy_orders.items(), key=lambda x: x[0], reverse=True)

        if not sorted_asks and not sorted_bids:
            return []

        best_ask = sorted_asks[0][0] if sorted_asks else 1971
        ask_vol = -sorted_asks[0][1] if sorted_asks else 1
        best_bid = sorted_bids[0][0] if sorted_bids else 1968
        bid_vol = sorted_bids[0][1] if sorted_bids else 1

        mid = (best_bid + best_ask) / 2.0
        micro = (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)

        tot_bid_vol = sum(order_depth.buy_orders.values())
        tot_ask_vol = sum(-v for v in order_depth.sell_orders.values())
        obi = (tot_bid_vol - tot_ask_vol) / (tot_bid_vol + tot_ask_vol) if (tot_bid_vol + tot_ask_vol) > 0 else 0.0

        squid_mem = memory.get("SQUID_INK", {})
        ema_fast = squid_mem.get("ema_fast", mid)
        ema_slow = squid_mem.get("ema_slow", mid)

        ema_fast = 0.333 * mid + 0.667 * ema_fast
        ema_slow = 0.095 * mid + 0.905 * ema_slow
        squid_mem["ema_fast"] = ema_fast
        squid_mem["ema_slow"] = ema_slow

        mid_history = squid_mem.get("mid_history", [])
        mid_history.append(mid)
        if len(mid_history) >= 4:
            short_roc = mid - mid_history[-3]
        else:
            short_roc = 0.0
        squid_mem["mid_history"] = mid_history[-40:]
        memory["SQUID_INK"] = squid_mem

        ema_diff = ema_fast - ema_slow
        signal = ema_diff + 0.6 * short_roc + 0.6 * obi

        # Target position based on swing signal
        if signal > 2.0:
            target_pos = 45
        elif signal > 0.8:
            target_pos = 28
        elif signal > 0.2:
            target_pos = 12
        elif signal < -2.0:
            target_pos = -45
        elif signal < -0.8:
            target_pos = -28
        elif signal < -0.2:
            target_pos = -12
        else:
            target_pos = 0

        # Execute towards target_pos
        eff_pos = om.effective_pos
        if eff_pos < target_pos:
            needed = target_pos - eff_pos
            if signal > 1.2:
                # Strong trend up: cross spread to enter
                for ask_p, ask_v in sorted_asks:
                    if needed <= 0:
                        break
                    avail = -ask_v
                    take_qty = min(avail, needed)
                    bought = om.buy(ask_p, take_qty)
                    needed -= bought
            else:
                # Moderate trend up: take asks at or below mid
                for ask_p, ask_v in sorted_asks:
                    if needed <= 0 or ask_p > mid:
                        break
                    avail = -ask_v
                    take_qty = min(avail, needed)
                    bought = om.buy(ask_p, take_qty)
                    needed -= bought

            # Place passive bid for remainder of needed or market making
            if om.buy_budget > 0:
                if best_ask - best_bid >= 2:
                    bid_p = min(best_bid + 1, best_ask - 1)
                else:
                    bid_p = best_bid
                om.buy(bid_p, om.buy_budget)

            # Passive ask for remaining sell budget (if any room and not in strong upswing)
            if om.sell_budget > 0 and signal < 1.5:
                ask_p = max(best_ask, best_bid + 1)
                om.sell(ask_p, om.sell_budget)

        elif eff_pos > target_pos:
            needed = eff_pos - target_pos
            if signal < -1.2:
                # Strong trend down: cross spread to exit/short
                for bid_p, bid_v in sorted_bids:
                    if needed <= 0:
                        break
                    avail = bid_v
                    take_qty = min(avail, needed)
                    sold = om.sell(bid_p, take_qty)
                    needed -= sold
            else:
                # Moderate trend down: take bids at or above mid
                for bid_p, bid_v in sorted_bids:
                    if needed <= 0 or bid_p < mid:
                        break
                    avail = bid_v
                    take_qty = min(avail, needed)
                    sold = om.sell(bid_p, take_qty)
                    needed -= sold

            # Place passive ask for remainder of needed or market making
            if om.sell_budget > 0:
                if best_ask - best_bid >= 2:
                    ask_p = max(best_ask - 1, best_bid + 1)
                else:
                    ask_p = best_ask
                om.sell(ask_p, om.sell_budget)

            # Passive bid for remaining buy budget (if any room and not in strong downswing)
            if om.buy_budget > 0 and signal > -1.5:
                bid_p = min(best_bid, best_ask - 1)
                om.buy(bid_p, om.buy_budget)

        else:
            # Neutral position: classic market making
            if om.buy_budget > 0:
                bid_p = best_bid + 1 if (best_ask - best_bid >= 2) else best_bid
                om.buy(min(bid_p, best_ask - 1), om.buy_budget)
            if om.sell_budget > 0:
                ask_p = best_ask - 1 if (best_ask - best_bid >= 2) else best_ask
                om.sell(max(ask_p, best_bid + 1), om.sell_budget)

        return om.get_orders()

    def run(self, state: TradingState):
        result = {}
        conversions = 0

        memory = {}
        if state.traderData:
            try:
                memory = json.loads(state.traderData)
            except Exception:
                memory = {}

        for product, order_depth in state.order_depths.items():
            pos = state.position.get(product, 0)
            if product == "RAINFOREST_RESIN":
                result[product] = self.trade_rainforest_resin(order_depth, pos, memory)
            elif product == "KELP":
                result[product] = self.trade_kelp(order_depth, pos, memory)
            elif product == "SQUID_INK":
                result[product] = self.trade_squid_ink(order_depth, pos, memory)
            else:
                result[product] = []

        traderData = json.dumps(memory)
        return result, conversions, traderData
