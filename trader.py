from datamodel import OrderDepth, TradingState, Order
from typing import List
import collections
import numpy as np

class Trader:
    
    STARFRUIT_COEF = [-0.703591491407734, -0.4918330007028236, -0.3442257990494724, -0.23474182959132742, -0.13766592122288243, -0.06159321908371221]
    STARFRUIT_INT = 1.0285830994358876e-06
    starfruit_cache = []
    POSITION_LIMITS = {
            'AMETHYSTS': 20,  # Maximum units of Amethysts that can be held
            'STARFRUIT': 20,  # Maximum units of Starfruit that can be held
            'ORCHIDS': 100
        }
    
    POSITIONS = {
            'AMETHYSTS': 0, 
            'STARFRUIT': 0,  
            'ORCHIDS': 0
        }
    
    curr_starfruit_price = 0

    def calc_starfruit_price(self):

        if len(self.starfruit_cache) < 6:
            return None
        next_ret = self.STARFRUIT_INT
        for i, ret in enumerate(reversed(self.starfruit_cache)):
            next_ret += ret * self.STARFRUIT_COEF[i]
        return self.curr_starfruit_price * np.exp(next_ret)

    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))

        result = {}
        for product in state.order_depths:
            if product not in self.POSITIONS:
                self.POSITIONS[product] = 0

            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            current_position = self.POSITIONS[product]
            position_limit = self.POSITION_LIMITS.get(product, 0)

            if product == 'AMETHYSTS':
                amethysts_lb = 10000
                amethysts_ub = 10000

                for ask, qty in order_depth.sell_orders.items():
                  if ask < amethysts_lb and current_position < position_limit:
                        quantity = min(-qty, position_limit - current_position)
                        orders.append(Order(product, ask, quantity))
                        current_position += quantity
                
                for bid, qty in order_depth.buy_orders.items():
                    if bid > amethysts_ub and current_position > -position_limit:
                        quantity = min(qty, current_position + position_limit)
                        orders.append(Order(product, bid, -quantity))
                        current_position -= quantity
            
            elif product == 'STARFRUIT':
                next_price = self.calc_starfruit_price()
                if next_price:
                    for ask, qty in order_depth.sell_orders.items():
                        if ask < next_price - 2 and current_position < position_limit:
                            quantity = min(-qty, position_limit - current_position)
                            orders.append(Order(product, ask, quantity))
                            current_position += quantity
                    
                    for bid, qty in order_depth.buy_orders.items():
                        if bid > next_price + 2 and current_position > -position_limit:
                            quantity = min(qty, current_position + position_limit)
                            orders.append(Order(product, bid, -quantity))
                            current_position -= quantity
            
            if 'STARFRUIT' in state.order_depths:
                mid_price = (list(state.order_depths['STARFRUIT'].sell_orders.keys())[0] +
                             list(state.order_depths['STARFRUIT'].buy_orders.keys())[0]) / 2
                if self.curr_starfruit_price !=0:
                    self.starfruit_cache.append(np.log(mid_price/self.curr_starfruit_price))
                self.curr_starfruit_price = mid_price
                if len(self.starfruit_cache) > 6:
                    self.starfruit_cache.pop(0)

            self.POSITIONS[product] = current_position
            result[product] = orders
    
        traderData = "Current POSITIONS: " + str(self.POSITIONS)  # Adjust this as needed based on what you want to monitor
        conversions = 1  # Assuming a sample conversion logic
        
        return result, conversions, traderData  # Ensure to return all expected outputs