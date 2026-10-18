import json
from datamodel import Order, OrderDepth, TradingState, Trade

class Trader:
    def run(self, state: TradingState):
        # Parse the traderData to get the stored mid_prices
        trader_data = json.loads(state.traderData) if state.traderData else {}
        mid_prices = trader_data.get('mid_prices', {})
        
        result = {}  # symbol -> list of Order
        orders_by_product = {}
        
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            
            # Get best bid and ask prices
            buy_orders = order_depth.buy_orders
            sell_orders = order_depth.sell_orders
            
            best_bid = max(buy_orders.keys()) if buy_orders else None
            best_ask = min(sell_orders.keys()) if sell_orders else None
            
            if best_bid is None or best_ask is None:
                continue  # No orders to consider
            
            # Calculate mid price
            mid_price = (best_bid + best_ask) / 2
            
            # Update mid_prices history for this product
            if product not in mid_prices:
                mid_prices[product] = []
            mid_prices[product].insert(0, mid_price)
            if len(mid_prices[product]) > 3:
                mid_prices[product] = mid_prices[product][:3]
            
            # Check if we have enough data to compute moving average
            if len(mid_prices[product]) >= 3:
                ma = sum(mid_prices[product]) / 3
                current_ma = mid_prices[product][0]
                
                # Get current position
                current_pos = state.position.get(product, 0)
                
                if current_ma > ma:
                    # Buy signal
                    max_buy = 50 - current_pos
                    if max_buy > 0:
                        # Calculate available volume at best_ask
                        volume_ask = abs(sell_orders.get(best_ask, 0))
                        quantity = min(max_buy, volume_ask)
                        if quantity > 0:
                            orders = result.setdefault(product, [])
                            orders.append(Order(product, best_ask, quantity))
                elif current_ma < ma:
                    # Sell signal
                    max_sell = current_pos
                    if max_sell > 0:
                        # Calculate available volume at best_bid
                        volume_bid = buy_orders.get(best_bid, 0)
                        quantity = min(max_sell, volume_bid)
                        if quantity > 0:
                            orders = result.setdefault(product, [])
                            orders.append(Order(product, best_bid, -quantity))
        
        # Serialize the updated mid_prices into traderData
        new_trader_data = json.dumps({'mid_prices': mid_prices})
        
        return result, 0, new_trader_data
