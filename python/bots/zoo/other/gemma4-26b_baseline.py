import json
import numpy as np
from datamodel import Order, OrderDepth, TradingState
from typing import List

class Trader:
    def run(self, state: TradingState):
        """
        Trading algorithm for the competition round.
        
        Strategies:
        - RAINFOREST_RESIN: Market making/Position Neutrality (aiming for 0 position).
        - KELP: Mean reversion using Bollinger Bands (Mid-price vs Moving Average + StdDev).
        - SQUID_INK: Momentum using Exponential Moving Average (EMA).
        """
        # 1. Load persistent state from traderData
        try:
            if not state.traderData:
                data = {
                    "history": {"RAINFOREST_RESIN": [], "KELP": [], "SQUID_INK": []},
                    "ema_squid": 0.0
                }
            else:
                data = json.loads(state.traderData)
        except Exception:
            data = {
                "history": {"RAINFOREST_RESIN": [], "KELP": [], "SQUID_INK": []},
                "ema_squid": 0.0
            }

        result = {}

        def get_prices(depth: OrderDepth):
            """Returns (best_bid, best_ask, mid_price)."""
            buys = depth.buy_orders
            sells = depth.sell_orders
            best_bid = max(buys.keys()) if buys else None
            best_ask = min(sells.keys()) if sells else None
            
            if best_bid is not None and best_ask is not None:
                mid = (best_bid + best_ask) / 2.0
            elif best_bid is not None:
                mid = float(best_bid)
            elif best_ask is not None:
                mid = float(best_ask)
            else:
                mid = None
            return best_bid, best_ask, mid

        # Process each product
        for symbol in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
            if symbol not in state.order_depths:
                result[symbol] = []
                continue
            
            depth = state.order_depths[symbol]
            best_bid, best_ask, mid = get_prices(depth)
            
            # If no price information is available, we cannot trade this product
            if mid is None:
                result[symbol] = []
                continue

            # Update price history for statistical calculations
            if symbol not in data["history"]:
                data["history"][symbol] = []
            data["history"][symbol].append(mid)
            # Limit history size to maintain performance within 900ms
            if len(data["history"][symbol]) > 500:
                data["history"][symbol].pop(0)

            pos = state.position.get(symbol, 0)
            orders: List[Order] = []

            if symbol == "RAINFOREST_RESIN":
                # Stable product: Aim for a net-zero position to avoid exposure.
                if pos < 0:
                    # Buy back to zero
                    price = best_bid if best_bid is not None else int(mid)
                    orders.append(Order(symbol, price, -pos))
                elif pos > 0:
                    # Sell back to zero
                    price = best_ask if best_ask is not None else int(mid)
                    orders.append(Order(symbol, price, -pos))

            elif symbol == "KELP":
                # Oscillating product: Mean reversion strategy.
                hist = data["history"][symbol]
                if len(hist) > 10:
                    ma = np.mean(hist)
                    std = np.std(hist)
                    # Buy when price is significantly below the mean
                    if mid < ma - 1.5 * std:
                        if pos < 50:
                            price = best_bid if best_bid is not None else int(mid)
                            orders.append(Order(symbol, price, 50 - pos))
                    # Sell when price is significantly above the mean
                    elif mid > ma + 1.5 * std:
                        if pos > -50:
                            price = best_ask if best_ask is not None else int(mid)
                            orders.append(Order(symbol, price, -(50 + pos)))

            elif symbol == "SQUID_INK":
                # Volatile/Patterned product: Momentum strategy using EMA.
                ema = data["ema_squid"]
                if ema == 0:
                    ema = mid
                else:
                    alpha = 0.1  # Smoothing factor
                    ema = alpha * mid + (1 - alpha) * ema
                data["ema_squid"] = ema

                # Trend following: If mid price is above EMA, momentum is up.
                if mid > ema and pos < 50:
                    price = best_bid if best_bid is not None else int(mid)
                    orders.append(Order(symbol, price, 50 - pos))
                # If mid price is below EMA, momentum is down.
                elif mid < ema and pos > -50:
                    price = best_ask if best_ask is not None else int(mid)
                    orders.append(Order(symbol, price, -(50 + pos)))
            
            result[symbol] = orders

        conversions = 0
        # Serialize updated state for next iteration
        traderData = json.dumps(data)
        return result, conversions, traderData

