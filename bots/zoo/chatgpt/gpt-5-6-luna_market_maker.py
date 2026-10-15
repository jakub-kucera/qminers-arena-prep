import json
import math

from datamodel import Order, OrderDepth, TradingState


LIMITS = {
    "RAINFOREST_RESIN": 50,
    "KELP": 50,
    "SQUID_INK": 50,
}

ALPHA = {
    "KELP": 0.20,
    "SQUID_INK": 0.12,
}

QUOTE_HALF_SPREAD = {
    "RAINFOREST_RESIN": 2,
    "KELP": 1,
    "SQUID_INK": 2,
}

TAKE_EDGE = {
    "RAINFOREST_RESIN": 1,
    "KELP": 1,
    "SQUID_INK": 2,
}

QUOTE_SIZE = {
    "RAINFOREST_RESIN": 10,
    "KELP": 10,
    "SQUID_INK": 8,
}


class Trader:
    def run(self, state: TradingState):
        memory = self._load_memory(state.traderData)
        result = {}

        for product, depth in state.order_depths.items():
            if product not in LIMITS:
                result[product] = []
                continue

            mid = self._midpoint(depth)
            if mid is None:
                result[product] = []
                continue

            fair = self._fair_value(product, mid, memory)
            position = state.position.get(product, 0)
            orders = []
            buy_used = 0
            sell_used = 0
            limit = LIMITS[product]
            edge = TAKE_EDGE[product]

            for price in sorted(depth.sell_orders):
                volume = -depth.sell_orders[price]
                if volume <= 0 or price > fair - edge:
                    break
                quantity = min(volume, limit - position - buy_used)
                if quantity > 0:
                    orders.append(Order(product, price, quantity))
                    buy_used += quantity

            for price in sorted(depth.buy_orders, reverse=True):
                volume = depth.buy_orders[price]
                if volume <= 0 or price < fair + edge:
                    break
                quantity = min(volume, limit + position - sell_used)
                if quantity > 0:
                    orders.append(Order(product, price, -quantity))
                    sell_used += quantity

            inventory_skew = self._inventory_skew(product, position, limit)
            quote_fair = fair - inventory_skew
            half_spread = QUOTE_HALF_SPREAD[product]
            desired_bid = math.floor(quote_fair - half_spread)
            desired_ask = math.ceil(quote_fair + half_spread)

            best_bid = max(depth.buy_orders) if depth.buy_orders else None
            best_ask = min(depth.sell_orders) if depth.sell_orders else None
            if best_ask is not None:
                desired_bid = min(desired_bid, best_ask - 1)
            if best_bid is not None:
                desired_ask = max(desired_ask, best_bid + 1)

            size = QUOTE_SIZE[product]
            buy_room = limit - position - buy_used
            sell_room = limit + position - sell_used
            if buy_room > 0:
                orders.append(Order(product, desired_bid, min(size, buy_room)))
            if sell_room > 0:
                orders.append(Order(product, desired_ask, -min(size, sell_room)))
            result[product] = orders

        return result, 0, json.dumps(memory, separators=(",", ":"))

    @staticmethod
    def _load_memory(raw):
        if not raw:
            return {"products": {}}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {"products": {}}
        if not isinstance(parsed, dict) or not isinstance(parsed.get("products"), dict):
            return {"products": {}}
        return parsed

    @staticmethod
    def _midpoint(depth: OrderDepth):
        if not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0

    def _fair_value(self, product, mid, memory):
        if product == "RAINFOREST_RESIN":
            return 10000.0

        previous = memory["products"].get(product, {})
        ema = previous.get("ema", mid)
        previous_ema = previous.get("previous_ema", ema)
        alpha = ALPHA[product]
        ema = alpha * mid + (1.0 - alpha) * ema
        memory["products"][product] = {
            "ema": ema,
            "previous_ema": previous.get("ema", ema),
            "mid": mid,
        }

        if product == "KELP":
            momentum = ema - previous_ema
            return ema + 0.25 * momentum

        momentum = ema - previous_ema
        return ema + 0.35 * momentum

    @staticmethod
    def _inventory_skew(product, position, limit):
        strength = {
            "RAINFOREST_RESIN": 2.0,
            "KELP": 1.5,
            "SQUID_INK": 2.0,
        }[product]
        return strength * position / limit
