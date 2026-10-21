import json
from typing import List
from datamodel import OrderDepth, TradingState, Order

class Trader:
    def run(self, state: TradingState):
        # Load persistent state
        if state.traderData:
            try:
                data = json.loads(state.traderData)
            except (json.JSONDecodeError, TypeError, ValueError):
                data = {}
        else:
            data = {}

        result = {}
        LIMIT = 50

        for product in state.order_depths:
            od: OrderDepth = state.order_depths[product]

            # Initialize product tracking
            if product not in data:
                data[product] = {'mids': []}
            pd = data[product]

            # Get best bid/ask
            if not od.buy_orders or not od.sell_orders:
                result[product] = []
                continue

            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            mid = (best_bid + best_ask) / 2.0
            spread = best_ask - best_bid

            # Book imbalance
            bid_vol = sum(od.buy_orders.values())
            ask_vol = abs(sum(od.sell_orders.values()))
            total_vol = bid_vol + ask_vol
            imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0.0

            # Deeper book: sum of top 3 levels each side
            bid_prices_sorted = sorted(od.buy_orders.keys(), reverse=True)[:3]
            ask_prices_sorted = sorted(od.sell_orders.keys())[:3]
            bid_depth = sum(od.buy_orders.get(p, 0) for p in bid_prices_sorted)
            ask_depth = sum(abs(od.sell_orders.get(p, 0)) for p in ask_prices_sorted)
            depth_imb = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0.0

            # Update price history
            pd['mids'].append(mid)
            if len(pd['mids']) > 300:
                pd['mids'] = pd['mids'][-300:]
            mids = pd['mids']
            n = len(mids)

            # Position
            pos = state.position.get(product, 0)

            # Market trade flow this tick
            mtrades = state.market_trades.get(product, [])
            net_flow = sum(t.quantity for t in mtrades)

            # --- Signals ---
            # Short momentum
            if n >= 2:
                mom1 = mids[-1] - mids[-2]
            else:
                mom1 = 0.0
            if n >= 4:
                mom3 = mids[-1] - mids[-4]
            elif n >= 2:
                mom3 = mids[-1] - mids[0]
            else:
                mom3 = 0.0

            # Medium trend
            if n >= 15:
                trend = mids[-1] - mids[-15]
            elif n >= 5:
                trend = mids[-1] - mids[0]
            else:
                trend = 0.0

            # Statistics
            if n >= 10:
                window = mids[-min(60, n):]
                mean = sum(window) / len(window)
                var = sum((x - mean) ** 2 for x in window) / len(window)
                std = var ** 0.5 if var > 0 else 1.0
            else:
                mean = mid
                std = 1.0

            z = (mid - mean) / std if std > 0.5 else 0.0

            # --- Product-specific signal ---
            signal = 0.0

            if product == 'RAINFOREST_RESIN':
                # Stable: mean reversion dominant
                signal = -z * 2.0
                signal += -mom3 * 0.3
                signal += imbalance * 0.8
                signal += depth_imb * 0.5
                signal += net_flow * 0.05
                base_size = 6

            elif product == 'KELP':
                # Cyclical: blend momentum and mean reversion
                signal = mom3 * 0.6 + trend * 0.3
                signal += imbalance * 1.2
                signal += depth_imb * 0.8
                signal += net_flow * 0.08
                signal -= z * 0.6  # mean reversion pull
                base_size = 8

            elif product == 'SQUID_INK':
                # Volatile with pattern: stronger momentum, watch for reversals
                signal = mom3 * 0.8 + trend * 0.5
                signal += imbalance * 1.5
                signal += depth_imb * 1.0
                signal += net_flow * 0.1
                signal -= z * 0.4
                # Check for consecutive same-direction moves (pattern)
                if n >= 4:
                    moves = [mids[-1] - mids[-2], mids[-2] - mids[-3], mids[-3] - mids[-4]]
                    if all(m > 0 for m in moves):
                        signal += 1.0  # trend confirmed
                    elif all(m < 0 for m in moves):
                        signal -= 1.0
                base_size = 10

            else:
                signal = mom3 * 0.5 + imbalance * 1.0
                base_size = 5

            # --- Position management ---
            # Force reduce if near limit
            if pos >= 42:
                signal = min(signal, -0.8)
            elif pos <= -42:
                signal = max(signal, 0.8)
            # Amplify signal if it opposes our position (closing is free)
            if pos > 10 and signal < 0:
                signal *= 1.4
            elif pos < -10 and signal > 0:
                signal *= 1.4

            # --- Execute ---
            orders: List[Order] = []

            if abs(signal) < 0.4:
                result[product] = []
                continue

            size = min(base_size, max(2, int(abs(signal) * 2.5) + 1))

            if signal > 0:
                # BUY at ask
                allowed = LIMIT - pos
                if allowed <= 0:
                    result[product] = []
                    continue
                size = min(size, allowed)
                if size > 0:
                    orders.append(Order(product, best_ask, size))
            else:
                # SELL at bid
                allowed = LIMIT + pos  # pos - size >= -LIMIT => size <= pos + LIMIT
                if allowed <= 0:
                    result[product] = []
                    continue
                size = min(size, allowed)
                if size > 0:
                    orders.append(Order(product, best_bid, -size))

            result[product] = orders

        return result, 0, json.dumps(data)
