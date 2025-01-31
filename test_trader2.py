from typing import List, Dict
import numpy as np

class Trader:
    POSITION_LIMITS = {'AMETHYSTS': 20, 'STARFRUIT': 20}
    POSITIONS = {'AMETHYSTS': 0, 'STARFRUIT': 0}
    starfruit_cache = []
    STARFRUIT_COEF = [-0.6875135892542726, -0.4602404386137076, -0.2840509702833329, -0.13946125412947463]
    STARFRUIT_INT = 2.2567213536783118e-07
    curr_starfruit_price = 0

    def calc_starfruit_price(self) -> float:
        if len(self.starfruit_cache) < 4:
            return None
        next_ret = self.STARFRUIT_INT
        for i, ret in enumerate(reversed(self.starfruit_cache)):
            next_ret += ret * self.STARFRUIT_COEF[i]
        return self.curr_starfruit_price * np.exp(next_ret)

    def compute_starfruit_orders(self, order_depth):
        orders = []
        next_price = self.calc_starfruit_price()
        if next_price:
            for ask, qty in order_depth.sell_orders.items():
                if ask < next_price - 1 and self.POSITIONS['STARFRUIT'] < self.POSITION_LIMITS['STARFRUIT']:
                    quantity = min(-qty, self.POSITION_LIMITS['STARFRUIT'] - self.POSITIONS['STARFRUIT'])
                    orders.append(('STARFRUIT', ask, quantity))
                    self.POSITIONS['STARFRUIT'] += quantity
            for bid, qty in order_depth.buy_orders.items():
                if bid > next_price + 1 and self.POSITIONS['STARFRUIT'] > -self.POSITION_LIMITS['STARFRUIT']:
                    quantity = min(qty, self.POSITIONS['STARFRUIT'] + self.POSITION_LIMITS['STARFRUIT'])
                    orders.append(('STARFRUIT', bid, -quantity))
                    self.POSITIONS['STARFRUIT'] -= quantity
        return orders

    def compute_amethysts_orders(self, order_depth):
        orders = []
        for ask, qty in order_depth.sell_orders.items():
            if ask < 10000 and self.POSITIONS['AMETHYSTS'] < self.POSITION_LIMITS['AMETHYSTS']:
                quantity = min(-qty, self.POSITION_LIMITS['AMETHYSTS'] - self.POSITIONS['AMETHYSTS'])
                orders.append(('AMETHYSTS', ask, quantity))
                self.POSITIONS['AMETHYSTS'] += quantity
        for bid, qty in order_depth.buy_orders.items():
            if bid > 10000 and self.POSITIONS['AMETHYSTS'] > -self.POSITION_LIMITS['AMETHYSTS']:
                quantity = min(qty, self.POSITIONS['AMETHYSTS'] + self.POSITION_LIMITS['AMETHYSTS'])
                orders.append(('AMETHYSTS', bid, -quantity))
                self.POSITIONS['AMETHYSTS'] -= quantity
        return orders

    def run(self, state):
        # Update current price from market data
        if 'STARFRUIT' in state.order_depths:
            mid_price = (list(state.order_depths['STARFRUIT'].sell_orders.keys())[0] +
                         list(state.order_depths['STARFRUIT'].buy_orders.keys())[0]) / 2
            if self.curr_starfruit_price:
                self.starfruit_cache.append(np.log(mid_price / self.curr_starfruit_price))
            self.curr_starfruit_price = mid_price
            if len(self.starfruit_cache) > 4:
                self.starfruit_cache.pop(0)

        # Process orders for each product
        result = {}
        for product, order_depth in state.order_depths.items():
            if product == 'AMETHYSTS':
                result[product] = self.compute_amethysts_orders(order_depth)
            elif product == 'STARFRUIT':
                result[product] = self.compute_starfruit_orders(order_depth)

        # Any additional processing needed for state update

        return result

# This is just an outline. Additional details, such as error handling or dynamic order thresholds, would depend on further specifications and requirements.
