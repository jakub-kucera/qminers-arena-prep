import json
import numpy as np
from datamodel import OrderDepth, TradingState, Order
from typing import List

class Trader:
    def run(self, state: TradingState):
        """
        Market-making algorithm that estimates fair value using EMA, manages 
        inventory via price skewing, and provides liquidity by quoting 
        around the estimated fair value with spreads proportional to volatility.
        """
        # 1. Load historical state from traderData
        history = {}
        if state.traderData:
            try:
                data = json.loads(state.traderData)
                history = data.get('history', {})
            except Exception:
                history = {}

        results = {}
        symbols = ['RAINFOREST_RESIN', 'KELP', 'SQUID_INK']
        
        for symbol in symbols:
            # 2. Determine current mid price from order book or history
            depth = state.order_depths.get(symbol)
            mid = None
            
            if depth:
                bids = depth.buy_orders
                asks = depth.sell_orders
                best_bid = max(bids.keys()) if bids else None
                best_ask = min(asks.keys()) if asks else None
                
                if best_bid is not None and best_ask is not None:
                    mid = (best_bid + best_ask) / 2.0
                elif best_bid is not None:
                    mid = float(best_bid + 1)
                elif best_ask is not None:
                    mid = float(best_ask - 1)
            
            if mid is None:
                if symbol in history and len(history[symbol]) > 0:
                    mid = float(history[symbol][-1])
                else:
                    # Fallback for the very first iteration based on provided data
                    if symbol == 'RAINFOREST_RESIN': mid = 10000.0
                    elif symbol == 'KELP': mid = 2030.0
                    else: mid = 1970.0
            
            # 3. Update price history (keep last 100 observations)
            if symbol not in history:
                history[symbol] = []
            history[symbol].append(mid)
            if len(history[symbol]) > 100:
                history[symbol].pop(0)
            
            # 4. Statistical analysis of price history
            prices = np.array(history[symbol])
            
            # Calculate EMA (Exponential Moving Average) for fair value estimation
            # We adjust alpha to make the algorithm more/less reactive to recent moves
            alpha = 0.05
            if symbol == 'SQUID_INK': 
                alpha = 0.3  # More reactive to volatility and patterns
            elif symbol == 'KELP': 
                alpha = 0.15 # Balanced for mean reversion
            
            ema = prices[0]
            for p in prices[1:]:
                ema = alpha * p + (1 - alpha) * ema
            
            # Calculate volatility (standard deviation) for spread calculation
            vol = np.std(prices) if len(prices) > 1 else 1.0
            
            # 5. Inventory Management and Skewing
            pos = state.position.get(symbol, 0)
            limit = 50
            
            # Skew the fair value to manage inventory.
            # If we are long (pos > 0), we lower our bid and ask prices to encourage selling.
            # If we are short (pos < 0), we raise our bid and ask prices to encourage buying.
            # skew_factor determines how aggressively we react to inventory.
            skew_factor = 0.001 
            skew = pos * (mid * skew_factor)
            effective_fair = ema - skew
            
            # 6. Spread Calculation
            # The spread widens during higher volatility to protect against adverse selection.
            if symbol == 'RAINFOREST_RESIN':
                vol_mult = 0.5  # Very stable, tight spread
            elif symbol == 'KELP':
                vol_mult = 1.2  # Moderate volatility
            else: # SQUID_INK
                vol_mult = 2.5  # High volatility, wider spread
            
            spread = max(2.0, vol * vol_mult)
            
            bid_price = int(round(effective_fair - (spread / 2.0)))
            ask_price = int(round(effective_fair + (spread / 2.0)))
            
            # 7. Order Generation with Position Limit Constraints
            # Note: If any order for a product violates the limit, all orders for that product are rejected.
            max_buy_qty = limit - pos
            max_sell_qty = limit + pos
            
            orders = []
            
            # We limit our order sizes to stay well within position limits and reduce risk.
            if pos > 0:
                # Already long: prioritize selling, limit or eliminate buying
                buy_qty = 0
                sell_qty = min(max_sell_qty, 10)
            elif pos < 0:
                # Already short: prioritize buying, limit or eliminate selling
                buy_qty = min(max_buy_qty, 10)
                sell_qty = 0
            else:
                # Neutral position: provide liquidity on both sides
                buy_qty = min(max_buy_qty, 5)
                sell_qty = min(max_sell_qty, 5)
            
            if buy_qty > 0:
                orders.append(Order(symbol, bid_price, buy_qty))
            if sell_qty > 0:
                orders.append(Order(symbol, ask_price, -sell_qty))
            
            results[symbol] = orders

        # 8. Prepare state for next iteration
        new_trader_data = json.dumps({'history': history})
        return results, 0, new_trader_data

