import json
import numpy as np
from datamodel import OrderDepth, TradingState, Order
from typing import List

class Trader:
    def run(self, state: TradingState):
        result = {}

        # Load persistent state from traderData
        try:
            data = json.loads(state.traderData) if state.traderData else {}
        except (json.JSONDecodeError, TypeError):
            data = {}

        # Extract and store mid prices
        for product in state.order_depths:
            od = state.order_depths[product]
            if not od.buy_orders or not od.sell_orders:
                continue
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            mid = (best_bid + best_ask) / 2.0

            if product not in data:
                data[product] = []
            data[product].append(mid)
            # Keep last 400 prices for analysis
            if len(data[product]) > 400:
                data[product] = data[product][-400:]

        # Decide trades for each product
        for product in state.order_depths:
            result[product] = self._trade(product, state, data)

        return result, 0, json.dumps(data)

    def _trade(self, product, state, data):
        od = state.order_depths[product]
        if not od.buy_orders or not od.sell_orders:
            return []

        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2.0

        # Available volume at best levels
        bid_volume = od.buy_orders[best_bid]
        ask_volume = abs(od.sell_orders[best_ask])

        position = state.position.get(product, 0)
        limit = 50
        prices = data.get(product, [])

        if len(prices) < 20:
            return []

        prices_arr = np.array(prices, dtype=float)

        # Compute target position based on signals
        target = self._target_position(product, prices_arr, mid, spread, state.timestamp)
        target = max(-limit, min(limit, target))

        # Determine trade
        diff = target - position

        if diff > 0:
            max_buy = limit - position
            qty = min(int(diff), max_buy, ask_volume)
            if qty >= 1:
                return [Order(product, best_ask, qty)]
        elif diff < 0:
            max_sell = position + limit
            qty = min(int(-diff), max_sell, bid_volume)
            if qty >= 1:
                return [Order(product, best_bid, -qty)]

        return []

    def _target_position(self, product, prices_arr, mid, spread, timestamp):
        n = len(prices_arr)
        if n < 20:
            return 0

        # --- Compute signals ---

        # Mean reversion: deviation from rolling mean
        avg_win = min(60, n)
        rolling_avg = np.mean(prices_arr[-avg_win:])
        deviation = mid - rolling_avg

        # Momentum: rate of change over recent window
        mom_win = min(15, n - 1)
        momentum = (prices_arr[-1] - prices_arr[-1 - mom_win]) / max(mom_win, 1)

        # Volatility: std of price changes
        if n >= 30:
            changes = np.diff(prices_arr[-30:])
            vol = float(np.std(changes)) + 1e-6
        else:
            vol = float(np.std(prices_arr)) / max(n - 1, 1) + 1e-6

        # Normalize signals (in units of volatility)
        norm = vol * 3.0 + 1e-6
        dev_norm = deviation / norm
        mom_norm = (momentum * 10.0) / norm  # 10-iteration forward momentum

        # --- Product-specific signal blending ---
        if product == "RAINFOREST_RESIN":
            # Stable: primarily mean-reversion, slight momentum
            signal = -1.8 * dev_norm + 0.3 * mom_norm
        elif product == "KELP":
            # Oscillating: balanced mean-reversion and momentum
            signal = -1.4 * dev_norm + 0.6 * mom_norm
        elif product == "SQUID_INK":
            # Volatile with pattern: stronger momentum component
            signal = -1.0 * dev_norm + 1.0 * mom_norm
        else:
            signal = -1.0 * dev_norm + 0.5 * mom_norm

        # --- Threshold filter: expected move must exceed spread ---
        # Estimate expected absolute move from our signals
        expected_move = abs(signal) * norm * 0.6
        if expected_move < spread * 0.8:
            return 0

        # --- Scale target position by signal strength ---
        # Map signal to a target in [-50, 50]
        scale = 25.0
        target = signal * scale

        # --- End-of-day de-risking ---
        if timestamp >= 999000:
            target *= 0.2
        elif timestamp >= 995000:
            target *= 0.5
        elif timestamp >= 990000:
            target *= 0.75

        # Clamp
        target = max(-50.0, min(50.0, target))

        # Round to integer, require minimum conviction
        target = int(round(target))
        if abs(target) < 2:
            return 0

        return target
