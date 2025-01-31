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
    POSITION_LIMITS = {'AMETHYSTS': 20, 'STARFRUIT': 20, 'CHOCOLATE': 250, 'STRAWBERRIES': 350, 'ROSES': 60, 'GIFT_BASKET': 60} 
    POSITIONS = {'AMETHYSTS': 0, 'STARFRUIT': 0, 'CHOCOLATE': 0, 'STRAWBERRIES': 0, 'ROSES': 0, 'GIFT_BASKET': 0}
    curr_starfruit_price = 0

    basket_std = 162

    def calc_starfruit_price(self):
        if len(self.starfruit_cache) < 4:
            return None
        next_price = self.STARFRUIT_INT
        for i, price in enumerate(reversed(self.starfruit_cache)):
            next_price += price * self.STARFRUIT_COEF[i]
        return next_price

    def handle_amethysts_orders(self, state):
        orders = []
        order_depth: OrderDepth = state.order_depths['AMETHYSTS']
        current_position = self.POSITIONS['AMETHYSTS']
        position_limit = self.POSITION_LIMITS['AMETHYSTS']
        amethysts_lb = 9999
        amethysts_ub = 10001

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

    def handle_starfruit_orders(self, state):
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
    
    def compute_orders_basket(self, state):
        orders = {'GIFT_BASKET': [], 'STRAWBERRIES': [], 'CHOCOLATE': [], 'ROSES': []}
        prods = ['STRAWBERRIES', 'CHOCOLATE', 'ROSES']
        order_depth = state.order_depths

        osell, obuy, best_sell, best_buy, mid_price = {}, {}, {}, {}, {}
        for p in list(orders.keys()):
            osell[p] = collections.OrderedDict(sorted(order_depth[p].sell_orders.items()))
            obuy[p] = collections.OrderedDict(sorted(order_depth[p].buy_orders.items(), reverse=True))

            best_sell[p] = next(iter(osell[p]))
            best_buy[p] = next(iter(obuy[p]))

            mid_price[p] = (best_sell[p] + best_buy[p]) / 2

        theoretical_price = mid_price['STRAWBERRIES'] * 6 + mid_price['CHOCOLATE'] * 4 + mid_price['ROSES'] + 370
        actual_price = mid_price['GIFT_BASKET']
        price_difference = actual_price - theoretical_price

        threshold = 162*0.4  
        current_position_gb = self.POSITIONS['GIFT_BASKET']
        position_limit_gb = self.POSITION_LIMITS['GIFT_BASKET']

        # Determine actions based on the price difference
        if price_difference > threshold:
            # Actual basket price is higher than theoretical, sell the basket and buy the assets
            for ask, qty in state.order_depths['GIFT_BASKET'].sell_orders.items():
                if current_position_gb > -position_limit_gb:
                    quantity = min(qty, current_position_gb + position_limit_gb)
                    orders['GIFT_BASKET'].append(Order('GIFT_BASKET', ask, -quantity))
                    current_position_gb -= quantity

            for p in prods:
                order_depth: OrderDepth = state.order_depths[p]
                curr_position = self.POSITIONS[p]
                pos_lim = self.POSITION_LIMITS[p]
                for bid, qty in order_depth.buy_orders.items():
                    if pos_lim > curr_position:
                        quantity = min(qty, pos_lim-curr_position)
                        orders[p].append(Order(p, bid, quantity))
                        self.POSITIONS[p] += quantity
                logger.print(f'SUBMITTING NEW LONG on {p} from QUANTITY {curr_position} TO MAKE POSITION {self.POSITIONS[p]} WHILE SHORTING BASKET')

        elif price_difference < -threshold:
            # Actual basket price is lower than theoretical, consider buying the basket
            for bid, qty in state.order_depths['GIFT_BASKET'].buy_orders.items():
                if position_limit_gb > current_position_gb:
                    quantity = min(qty, position_limit_gb - current_position_gb)
                    orders['GIFT_BASKET'].append(Order('GIFT_BASKET', bid, quantity))
                    current_position_gb += quantity
            
            for p in prods:
                order_depth: OrderDepth = state.order_depths[p]
                curr_position = self.POSITIONS[p]
                pos_lim = -self.POSITION_LIMITS[p]
                for ask, qty in order_depth.sell_orders.items():
                    if curr_position > -pos_lim:
                        quantity = min(qty, pos_lim+curr_position)
                        orders[p].append(Order(p, ask, -quantity))
                        self.POSITIONS[p] -= quantity   
                logger.print(f'SUBMITTING NEW SHORT on {p} from QUANTITY {curr_position} TO MAKE POSITION {self.POSITIONS[p]} WHILE LONGING BASKET')

        if 0 < price_difference <= 10 and current_position_gb > 0:
            logger.print('EXITING LONG BASKET AND SHORT PRODS POSITION')
            for ask, qty in state.order_depths['GIFT_BASKET'].sell_orders.items():
                quantity = min(qty, current_position_gb)
                orders['GIFT_BASKET'].append(Order('GIFT_BASKET', ask, -quantity))
                current_position_gb -= quantity

            for p in prods:
                order_depth: OrderDepth = state.order_depths[p]
                curr_position = self.POSITIONS[p]
                pos_lim = self.POSITION_LIMITS[p]
                for bid, qty in order_depth.buy_orders.items():
                    if curr_position > - pos_lim:
                        quantity = min(qty, -curr_position)
                        orders[p].append(Order(p, bid, quantity))
                        self.POSITIONS[p] += quantity
                    logger.print(f'COVERING SHORTS ON {p} from QUANTITY {curr_position} to {self.POSITIONS[p]} AFTER CLOSING LONG BASKET')


        elif -30 <= price_difference < 0 and current_position_gb < 0:
            logger.print('EXITING SHORT BASKET AND LONG PRODS POSITION')
            for bid, qty in state.order_depths['GIFT_BASKET'].buy_orders.items():
                quantity = min(qty, -current_position_gb)
                orders['GIFT_BASKET'].append(Order('GIFT_BASKET', bid, quantity))
                current_position_gb += quantity

            for p in prods:
                order_depth: OrderDepth = state.order_depths[p]
                curr_position = self.POSITIONS[p]
                pos_lim = self.POSITION_LIMITS[p]
                for ask, qty in order_depth.sell_orders.items():
                    if 0 < curr_position <= pos_lim:
                        quantity = min(qty, -curr_position)
                        orders[p].append(Order(p, ask, -quantity))
                        self.POSITIONS[p] -= quantity
                        logger.print(f'SELLING LONG {p} from QUANTITY {curr_position} to {self.POSITIONS[p]} AFTER COVERING SHORT BASKET')
        
        self.POSITIONS['GIFT_BASKET'] = current_position_gb
        return orders

    
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result = {}
        if 'AMETHYSTS' in state.order_depths:
            result['AMETHYSTS'] = self.handle_amethysts_orders(state)
        if 'STARFRUIT' in state.order_depths:
            result['STARFRUIT'] = self.handle_starfruit_orders(state)
        for prod in ['GIFT_BASKET', 'STRAWBERRIES', 'CHOCOLATE', 'ROSES']:
            result[prod] = self.compute_orders_basket(state)[prod]

        
        if 'STARFRUIT' in state.order_depths:
            mid_price = (list(state.order_depths['STARFRUIT'].sell_orders.keys())[0] +
                            list(state.order_depths['STARFRUIT'].buy_orders.keys())[0]) / 2
            self.starfruit_cache.append(mid_price)
            if len(self.starfruit_cache) > 4:
                self.starfruit_cache.pop(0)


        
        traderData = f"Current POSITIONS: {self.POSITIONS}"  # Format for better readability
        conversions = 1  # Placeholder for conversion logic
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData