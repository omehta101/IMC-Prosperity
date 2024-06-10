from datamodel import OrderDepth, TradingState, Order
from typing import List
import collections
import numpy as np

class Trader:
    
    STARFRUIT_COEF = [-0.703591491407734, -0.4918330007028236, -0.3442257990494724, -0.23474182959132742, -0.13766592122288243, -0.06159321908371221]
    STARFRUIT_INT = 1.0285830994358876e-06
    starfruit_cache = []

    ORCHIDS_COEF = [-0.00222597542860434, -0.0001782550473343116, -0.06775987455596787, -0.0034279249954251075]
    ORCHIDS_INT =  -0.11628586488710894

    curr_import = 0
    curr_export = 0
    curr_production = 0
    curr_transport = 0

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
    curr_orchids_price = 0
    
    def total_production_change(self, H, s):
        if 60 <= H <= 80:
            humidity_change = 0
        elif H < 60:
            num_fives = (60 - H) // 5
            humidity_change = num_fives * -0.02
        else:  # H > 80
            num_fives = (H - 80) // 5
            humidity_change = num_fives * -0.02
        
        minutes = s * 60  # Converts hours to minutes
        rounded_minutes = (minutes // 10) * 10  # Rounds down to the nearest 10 minutes
        rounded_hours = rounded_minutes / 60  # Converts back to hours
        
        if rounded_hours < 7:
            ten_minute_intervals = (7 - rounded_hours) * 6
            sunlight_change = -0.04 * ten_minute_intervals
        else:
            sunlight_change = 0

        production_change = humidity_change + sunlight_change
    
        return production_change
    
    def calc_orchids_price(self):
        next_ret = self.ORCHIDS_INT
        next_ret += self.curr_import*self.ORCHIDS_COEF[0] 
        next_ret += self.curr_export*self.ORCHIDS_COEF[1] 
        next_ret += self.curr_production*self.ORCHIDS_COEF[2] 
        next_ret += self.curr_transport*self.ORCHIDS_COEF[3]
        return self.curr_orchids_price * np.exp(next_ret)

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

            
            elif product == 'ORCHIDS':

                orchid_bid = state.observations.conversionObservations["ORCHIDS"].bidPrice
                orchid_ask = state.observations.conversionObservations["ORCHIDS"].askPrice
                sunlight = state.observations.conversionObservations["ORCHIDS"].sunlight
                humidity = state.observations.conversionObservations["ORCHIDS"].humidity
                import_tariff = state.observations.conversionObservations["ORCHIDS"].importTariff
                export_tariff = state.observations.conversionObservations["ORCHIDS"].exportTariff

                next_price = self.calc_orchids_price()

                if orchid_ask < next_price and current_position < position_limit:
                    orders.append(Order(product, orchid_ask, 5))
                    current_position += 5
                
                if orchid_bid > next_price and current_position > -position_limit:
                    orders.append(Order(product, orchid_bid, 5))
                    current_position -=5
                
            
            if 'ORCHIDS' in state.observations.conversionObservations:
                orchid_bid = state.observations.conversionObservations["ORCHIDS"].bidPrice
                orchid_ask = state.observations.conversionObservations["ORCHIDS"].askPrice
                sunlight = state.observations.conversionObservations["ORCHIDS"].sunlight
                humidity = state.observations.conversionObservations["ORCHIDS"].humidity
                import_tariff = state.observations.conversionObservations["ORCHIDS"].importTariff
                export_tariff = state.observations.conversionObservations["ORCHIDS"].exportTariff
                transport_fees = state.observations.conversionObservations["ORCHIDS"].transportFees

                self.curr_production = self.total_production_change(humidity/365, sunlight)
                self.curr_export = export_tariff
                self.curr_import = import_tariff
                self.curr_transport = transport_fees

                self.curr_orchids_price = (orchid_ask + orchid_bid)/2

            self.POSITIONS[product] = current_position
            result[product] = orders
    
        traderData = "Current POSITIONS: " + str(self.POSITIONS)  # Adjust this as needed based on what you want to monitor
        conversions = 1  # Assuming a sample conversion logic
        
        return result, conversions, traderData  # Ensure to return all expected outputs