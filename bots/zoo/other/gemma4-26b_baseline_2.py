import json
import numpy as np
from datamodel import OrderDepth, TradingState, Order
from typing import List

class Trader:
    def run(self, state: TradingState):
        """
        Trading algorithm for one round of the competition.
        Strategies:
        - RAINFOREST_RESIN: Market making (passive) to capture the spread.
        - KELP: Trend following (aggressive) using SMA crossover.
        - SQUID_INK: Mean reversion (aggressive) using Z-score.
        """
        # 1. Load historical data from traderData
        if state.traderData:
            try:
                history = json.loads(state.traderData)
            except:
                history = {"prices": {"RAINFOREST_RESIN": [], "KELP": [], "SQUID_INK": []}}
        else:
            history = {"prices": {"RAINFOREST_RESIN": [], "KELP": [], "SQUID_INK": []}}

        # 2. Update history with current mid-prices
        for symbol in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
            depth = state.order_depths[symbol]
            bids = list(depth.buy_orders.keys())
            asks = list(depth.sell_orders.keys())
            
            if bids and asks:
                best_bid = max(bids)
                best_ask = min(asks)
                mid_price = (best_bid + best_ask) / 2.0
                history["prices"][symbol].append(mid_price)
                # Keep history manageable (last 200 points)
                if len(history["prices"][symbol]) > 200:
                    history["prices"][symbol].pop(0)

        results = {}
        for symbol in ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]:
            prices = history["prices"][symbol]
            if not prices:
                results[symbol] = []
                continue
            
            depth = state.order_depths[symbol]
            bids = sorted(depth.buy_orders.keys(), reverse=True)
            asks = sorted(depth.sell_orders.keys())
            current_pos = state.position.get(symbol, 0)
            orders = []

            if symbol == "RAINFOREST_RESIN":
                # Strategy: Market Maker (Passive)
                # Aim for position 0, placing orders at the top of the book.
                if current_pos > 0:
                    if bids:
                        qty = min(current_pos, 50)
                        orders.append(Order(symbol, bids[0], -qty))
                elif current_pos < 0:
                    if asks:
                        qty = min(abs(current_pos), 50)
                        orders.append(Order(symbol, asks[0], qty))
                else:
                    if bids and asks:
                        # Place small limit orders to capture spread
                        orders.append(Order(symbol, bids[0], 5))
                        orders.append(Order(symbol, asks[0], -5))

            elif symbol == "KELP":
                # Strategy: Trend Follower (Aggressive)
                # Use SMA crossover to detect momentum.
                if len(prices) >= 30:
                    sma_short = np.mean(prices[-10:])
                    sma_long = np.mean(prices[-30:])
                    target_pos = 0
                    if sma_short > sma_long:
                        target_pos = 50
                    elif sma_short < sma_long:
                        target_pos = -50
                    
                    diff = target_pos - current_pos
                    if diff > 0:
                        # Target position is higher: Buy aggressively at ask
                        if asks:
                            qty = min(diff, 50 - current_pos)
                            if qty > 0:
                                orders.append(Order(symbol, asks[0], qty))
                    elif diff < 0:
                        # Target position is lower: Sell aggressively at bid
                        if bids:
                            qty = max(diff, -50 - current_pos)
                            if qty < 0:
                                orders.append(Order(symbol, bids[0], qty))

            elif symbol == "SQUID_INK":
                # Strategy: Mean Reversion (Aggressive)
                # Use Z-score to detect overextended swings.
                if len(prices) >= 20:
                    avg = np.mean(prices[-20:])
                    std = np.std(prices[-20:])
                    if std > 0:
                        z = (prices[-1] - avg) / std
                        target_pos = 0
                        if z > 1.5:
                            target_pos = -50  # Price high, sell
                        elif z < -1.5:
                            target_pos = 50   # Price low, buy
                        
                        diff = target_pos - current_pos
                        if diff > 0:
                            # Aggressive buy at ask
                            if asks:
                                qty = min(diff, 50 - current_pos)
                                if qty > 0:
                                    orders.append(Order(symbol, asks[0], qty))
                        elif diff < 0:
                            # Aggressive sell at bid
                            if bids:
                                qty = max(diff, -50 - current_pos)
                                if qty < 0:
                                    orders.append(Order(symbol, bids[0], qty))
                elif len(prices) > 0:
                    # Fallback to market making if not enough history
                    if bids and asks:
                        orders.append(Order(symbol, bids[0], 5))
                        orders.append(Order(symbol, asks[0], -5))

            results[symbol] = orders

        # 3. Return results and serialize state
        new_trader_data = json.dumps(history)
        return results, 0, new_trader_data

