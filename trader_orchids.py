from datamodel import OrderDepth, TradingState, Order
from typing import List
import numpy as np
import collections
import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders),
            conversions,
            "",
            "",
        ]))

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing["symbol"], listing["product"], listing["denomination"]])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append([
                    trade.symbol,
                    trade.price,
                    trade.quantity,
                    trade.buyer,
                    trade.seller,
                    trade.timestamp,
                ])

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sunlight,
                observation.humidity,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[:max_length - 3] + "..."

logger = Logger()


class Trader:

    STARFRUIT_COEF = [0.33554709188723075,
 0.26036696194151493,
 0.20454692911372097,
 0.19720337509805655]
    STARFRUIT_INT = 11.802383435338925
    starfruit_cache = []
    POSITION_LIMITS = {'AMETHYSTS': 20, 'STARFRUIT': 20, 'CHOCOLATE': 250, 'STRAWBERRIES': 350, 'ROSES': 60, 'GIFT_BASKET': 60, 'ORCHIDS':100} 
    POSITIONS = {'AMETHYSTS': 0, 'STARFRUIT': 0, 'CHOCOLATE': 0, 'STRAWBERRIES': 0, 'ROSES': 0, 'GIFT_BASKET': 0, 'ORCHIDS': 0}
    curr_starfruit_price = 0
    differences_cache = []


    def values_extract(self, order_dict, buy=0):
        tot_vol = 0
        best_val = -1
        mxvol = -1

        for ask, vol in order_dict.items():
            if(buy==0):
                vol *= -1
            tot_vol += vol
            if tot_vol > mxvol:
                mxvol = vol
                best_val = ask
        
        return tot_vol, best_val
    
    def calc_starfruit_price(self):
        if len(self.starfruit_cache) < 4:
            return None
        next_price = self.STARFRUIT_INT
        for i, price in enumerate(reversed(self.starfruit_cache)):
            next_price += price * self.STARFRUIT_COEF[i]
        return next_price

    def compute_orders_amethysts(self, state):
        orders = []
        order_depth: OrderDepth = state.order_depths['AMETHYSTS']
        current_position = self.POSITIONS['AMETHYSTS']
        position_limit = self.POSITION_LIMITS['AMETHYSTS']
        amethysts_lb = 10000
        amethysts_ub = 10000

        for ask, qty in order_depth.sell_orders.items():
            if ask < amethysts_lb and current_position < position_limit:
                quantity = min(-qty, position_limit - current_position)
                orders.append(Order('AMETHYSTS', ask, quantity))
                current_position += quantity

        for bid, qty in order_depth.buy_orders.items():
            if bid > amethysts_ub and current_position > -position_limit:
                quantity = min(qty, current_position + position_limit)
                orders.append(Order('AMETHYSTS', bid, -quantity))
                current_position -= quantity

        self.POSITIONS['AMETHYSTS'] = current_position
        return orders

    def compute_orders_starfruit(self, state):
        orders = []
        order_depth: OrderDepth = state.order_depths['STARFRUIT']
        current_position = self.POSITIONS['STARFRUIT']
        position_limit = self.POSITION_LIMITS['STARFRUIT']
        next_price = self.calc_starfruit_price()

        if next_price:
            for ask, qty in order_depth.sell_orders.items():
                if ask < next_price + 0.75 and current_position < position_limit:
                    quantity = min(-qty, position_limit - current_position)
                    orders.append(Order('STARFRUIT', ask, quantity))
                    current_position += quantity

            for bid, qty in order_depth.buy_orders.items():
                if bid > next_price - 0.75 and current_position > -position_limit:
                    quantity = min(qty, current_position + position_limit)
                    orders.append(Order('STARFRUIT', bid, -quantity))
                    current_position -= quantity

        self.POSITIONS['STARFRUIT'] = current_position
        return orders
    
    def compute_orders_orchids(self, state):
        orders = []
        conv_obs = state.observations.conversionObservations
        order_depth = state.order_depths['ORCHIDS']
        south_bid = conv_obs["ORCHIDS"].bidPrice
        south_ask = conv_obs["ORCHIDS"].askPrice
        import_tariff = conv_obs["ORCHIDS"].importTariff
        export_tariff = conv_obs["ORCHIDS"].exportTariff
        transport_fees = conv_obs["ORCHIDS"].transportFees
        current_position = self.POSITIONS['ORCHIDS']
        position_limit = self.POSITION_LIMITS['ORCHIDS']
        virtual_south_ask = south_ask + import_tariff + transport_fees

        for ask, qty in order_depth.sell_orders.items():
            vol = position_limit - current_position
            if (ask+import_tariff+transport_fees) < south_bid:
                quantity = min(-qty, vol)
                orders.append(Order('ORCHIDS', ask, quantity))
                current_position += quantity
                logger.print(f'SUBMITTED BUY ORCHIDS WHEN ASK {ask} AND SOUTH BID {south_bid}')
            else: break
        
        for bid, qty in order_depth.buy_orders.items():
            vol = position_limit + current_position
            if bid >= virtual_south_ask:
                quantity = min(qty, vol)
                orders.append(Order('ORCHIDS', bid, -quantity))
                current_position -= quantity
                logger.print(f'SUBMITTED SELL ORCHIDS WHEN BID {bid} AND SOUTH ASK {south_ask}')
            else: break

        self.POSITIONS['ORCHIDS'] = current_position
        conversion_requests = -state.position.get('ORCHIDS', 0)
        return orders, conversion_requests
        

    def compute_orders_basket(self, state):
        orders = {'GIFT_BASKET': [], 'STRAWBERRIES': [], 'CHOCOLATE': [], 'ROSES': []}
        prods = ['ROSES', 'GIFT_BASKET', 'STRAWBERRIES', 'CHOCOLATE']

        order_depth = state.order_depths

        osell, obuy, best_sell, best_buy, mid_price, worst_buy, worst_sell = {}, {}, {}, {}, {}, {}, {}

        for p in list(orders.keys()):
            osell[p] = collections.OrderedDict(sorted(order_depth[p].sell_orders.items()))
            obuy[p] = collections.OrderedDict(sorted(order_depth[p].buy_orders.items(), reverse=True))

            best_sell[p] = next(iter(osell[p]))
            best_buy[p] = next(iter(obuy[p]))

            worst_sell[p] = next(reversed(osell[p]))
            worst_buy[p] = next(reversed(obuy[p]))

            mid_price[p] = (best_sell[p] + best_buy[p]) / 2

        theoretical_price = mid_price['STRAWBERRIES'] * 6 + mid_price['CHOCOLATE'] * 4 + mid_price['ROSES'] + 370
        actual_price = mid_price['GIFT_BASKET']
        price_difference = actual_price - theoretical_price

        self.differences_cache.append(price_difference)
        
        # Computing the rolling mean and standard deviation of the price differences
        window_size = 200
        if len(self.differences_cache) > window_size:
            windowed_data = self.differences_cache[-window_size:]
            mean_difference = np.mean(windowed_data)
            std_difference = np.std(windowed_data) # Only consider the last 'window_size' elements
        else:
            mean_difference = 9
            std_difference = 75

        threshold_u = mean_difference + std_difference
        threshold_d = mean_difference - (0.5*std_difference) 
        
        if price_difference > threshold_u: 
            for prod in prods:
                curr_position = self.POSITIONS[prod]
                position_limit = self.POSITION_LIMITS[prod]
                for bid, qty in order_depth[prod].buy_orders.items():
                    vol = position_limit+curr_position
                    if vol > 0:
                        quantity = min(qty, vol)
                        orders[prod].append(Order(prod, bid, -quantity))
                        curr_position -= quantity
                    else: break
                logger.print(f'SUBMITTED SHORT {prod}')
                self.POSITIONS[prod] = curr_position

        elif price_difference < threshold_d: 
            for prod in prods:
                curr_position = self.POSITIONS[prod]
                position_limit = self.POSITION_LIMITS[prod]
                for ask, qty in order_depth[prod].sell_orders.items():
                    vol = position_limit-curr_position
                    if vol > 0:
                        quantity = min(-qty, vol)
                        orders[prod].append(Order(prod, ask, quantity))
                        curr_position += quantity
                    else: break
                logger.print(f'SUBMITTED LONG {prod}')
                self.POSITIONS[prod] = curr_position
        
        logger.print(f'SUBMITTING THE FOLLOWING ORDERS: {orders}')
        return orders


    
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:

        result = {}

        for key, val in state.position.items():
            self.POSITIONS[key] = val

        if 'AMETHYSTS' in state.order_depths:
            result['AMETHYSTS'] = self.compute_orders_amethysts(state)
        if 'STARFRUIT' in state.order_depths:
            result['STARFRUIT'] = self.compute_orders_starfruit(state)
        if 'ORCHIDS' in state.order_depths:
            result['ORCHIDS'], conversions = self.compute_orders_orchids(state)

        orders = self.compute_orders_basket(state)
        for prod in ['GIFT_BASKET', 'STRAWBERRIES', 'CHOCOLATE', 'ROSES']:
            result[prod] = orders[prod]

        
        if 'STARFRUIT' in state.order_depths:
            mid_price = (list(state.order_depths['STARFRUIT'].sell_orders.keys())[0] +
                            list(state.order_depths['STARFRUIT'].buy_orders.keys())[0]) / 2
            self.starfruit_cache.append(mid_price)
            if len(self.starfruit_cache) > 4:
                self.starfruit_cache.pop(0)


        
        traderData = f"Current POSITIONS: {self.POSITIONS}"  # Format for better readability
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData