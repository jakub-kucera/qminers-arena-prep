import json
from typing import List
from datamodel import OrderDepth, TradingState, Order
import numpy as np
import pandas as pd

class Trader:
    def run(self, state: TradingState):
        # 1. Initialize or load state from traderData
        # The exchange may create a new Trader object for any iteration, 
        # so we must use traderData to persist history.
        data = {}
        if state.traderData:
            try:
                data = json.loads(state.traderData)
            except Exception:
                data = {}
        
        if 'history' not in data:
            data['history'] = {}
        
        history = data['history']
        result = {}

        # 2. Define product-specific market making configurations
        # RAINFOREST_RESIN: Stable, small spread, low inventory risk weight.
        # KELP: Moderate volatility, medium spread, medium weight.
        # SQUID_INK: High volatility, large spread, high weight.
        configs = {
            'RAINFOREST_RESIN': {'spread': 2, 'k': 0.1, 'window': 100},
            'KELP': {'spread': 6, 'k': 0.5, 'window': 30},
            'SQUID_INK': {'spread': 20, 'k': 1.5, 'window': 10}
        }

        # 3. Process every product in the current state
        for symbol in state.order_depths:
            order_depth: OrderDepth = state.order_depths[symbol]
            config = configs.get(symbol, {'spread': 10, 'k': 1.0, 'window': 20})
            
            # Get current position (default to 0 if not in dict)
            pos = state.position.get(symbol, 0)
            
            # Calculate current mid price from the order book
            # buy_orders: price -> volume (positive)
            # sell_orders: price -> volume (negative)
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
            
            current_mid = None
            if best_bid is not None and best_ask is not None:
                current_mid = (best_bid + best_ask) / 2.0
            elif best_bid is not None:
                current_mid = float(best_bid)
            elif best_ask is not None:
                current_mid = float(best_ask)
            
            # 4. Update historical mid-prices for fair value estimation (EMA proxy)
            if current_mid is not None:
                if symbol not in history:
                    history[symbol] = []
                history[symbol].append(current_mid)
                # Keep only enough history to cover the window
                history[symbol] = history[symbol][-config['window']:]
            
            # 5. Estimate Fair Value (V)
            # We use the mean of historical mid-prices as a simple, stable estimator.
            if symbol in history and len(history[symbol]) > 0:
                fair_value = sum(history[symbol]) / len(history[symbol])
            else:
                if current_mid is not None:
                    fair_value = current_mid
                else:
                    # If no book or history, skip trading this product this iteration
                    continue
            
            orders = []
            
            # 6. Calculate Order Quantities (q) and Prices (p)
            # Respect position limits: |pos + sum(buys)| <= 50 and |pos + sum(sells)| <= 50.
            # The rule states if ALL orders for a product could breach the limit, ALL are rejected.
            
            max_buy_qty = 50 - pos
            max_sell_qty = -50 - pos  # This is a negative number (e.g., -50 - 40 = -90)
            
            base_size = 5
            q_bid = 0
            q_ask = 0
            
            # Inventory management: Adjust direction based on current position.
            # If pos < 0 (short), we want to buy (q_bid > 0).
            # If pos > 0 (long), we want to sell (q_ask < 0).
            # If pos == 0, we want to provide both sides to earn the spread.
            
            if pos <= 0:
                q_bid = min(base_size, max_buy_qty)
            if pos >= 0:
                q_ask = max(-base_size, max_sell_qty)
                
            # If we are in a neutral position, we can place both a bid and an ask.
            # If we are near a limit, the logic above ensures we only trade in the safe direction.

            # 7. Determine prices using the Avellaneda-Stoikov style adjustment:
            # p_bid = FairValue - Spread/2 - (k * position)
            # p_ask = FairValue + Spread/2 - (k * position)
            # This shifts the quotes down when long and up when short, encouraging mean reversion.
            
            p_bid = int(round(fair_value - (config['spread'] / 2.0) - (config['k'] * pos)))
            p_ask = int(round(fair_value + (config['spread'] / 2.0) - (config['k'] * pos)))
            
            if q_bid > 0:
                orders.append(Order(symbol, p_bid, q_bid))
            if q_ask < 0:
                orders.append(Order(symbol, p_ask, q_ask))
            
            result[symbol] = orders

        # 8. Return results and serialized state
        # We return the updated history to be retrieved via state.traderData in the next iteration.
        new_trader_data = json.dumps({'history': history})
        return result, 0, new_trader_data

