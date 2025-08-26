from typing import Dict, Any, List, Tuple
import numpy as np

from src.utils.logging.logger import Logger
from src.exchanges.base.structures import Order
from src.exchanges.base.constants import Side, OrderType
from src.utils.rounding_utils import round_step
from src.utils.calc_utils import nbabs, nblinspace, geometric_weights
from src.quoting_engines.volatility_estimator import VolatilityEstimator

class SimpleQuoter:
    
    def __init__(self, config: Dict[str, Any], logger: Logger):
        self.logger = logger
        self.symbol = config["mm"]["symbol"]
        self.num_orders = config["mm"]["num_orders"]
        self.lot_size = config["mm"]["lot_size"]
        self.tick_size = config["mm"]["tick_size"]
        self.spread_bps = config["mm"]["spread_bps"]
        self.gross_exposure_dollars = config["mm"]["gross_exposure_dollars"]
        self.epsilon = config["mm"]["epsilon"]
        self.inventory_max_dollars = config["mm"]["inventory_max_dollars"]

        self.last_mid = 0
        self.prev_bid_skew = 0 
        self.prev_ask_skew = 0
        self.prev_vol = 0
        
        self.volatility_estimator = VolatilityEstimator(window_size=30)

    def _skew(self, position_value: float, max_skew_pct: float = 0.01) -> Tuple[float, float]:
        bid_skew, ask_skew = 0, 0
        inventory_delta = (position_value/self.inventory_max_dollars)

        bid_skew += inventory_delta if inventory_delta < 0 else 0
        ask_skew -= inventory_delta if inventory_delta > 0 else 0

        bid_skew = bid_skew if position_value > -self.inventory_max_dollars else 1
        ask_skew = ask_skew if position_value < self.inventory_max_dollars else 1

        return nbabs(bid_skew), nbabs(ask_skew)

    def _volatility(self, mid: float) -> float:
        return self.volatility_estimator.update(mid)

    def _prices(self,
    mid: float,
    best_bid: float,
    best_ask: float,
    bid_skew: float,
    ask_skew: float,
    vol: float):

        base_range = ((self.spread_bps * mid)/10000) + vol

        best_bid = mid - base_range/2
        best_ask = mid + base_range/2

        if bid_skew >= 1:
            bid_lower = mid - (base_range/2 * self.num_orders/2)
            bid_prices = nblinspace(best_bid, bid_lower, self.num_orders/2)
            return bid_prices, None
        
        elif ask_skew >= 1:
            ask_upper = mid + (base_range/2 * self.num_orders/2)
            ask_prices = nblinspace(best_ask, ask_upper, self.num_orders/2)
            return None, ask_prices

        bid_lower = best_bid - (base_range/2 * (1-bid_skew) * (1+ask_skew) * self.num_orders/2)
        ask_upper = best_ask + (base_range/2 * (1-ask_skew) * (1+bid_skew) * self.num_orders/2)

        bid_prices = nblinspace(best_bid, bid_lower, self.num_orders/2)
        ask_prices = nblinspace(best_ask, ask_upper, self.num_orders/2)

        return bid_prices, ask_prices

    def _sizes(self, mid: float):
        sizes = (self.gross_exposure_dollars * geometric_weights(self.num_orders/2, 0.6) / mid)[::-1]
        return sizes, sizes
    
    def generate_quote_v2(self, lob: Dict[str, Any], position: float, forced_requote: bool) -> List[Order]:
        mid = lob["mid"]
        best_bid = lob["best_bid"]
        best_ask = lob["best_ask"]

        bids, asks = [], []

        bid_skew, ask_skew = self._skew(position)
        vol = self._volatility(mid)
        bid_prices, ask_prices = self._prices(mid, best_bid, best_ask, bid_skew, ask_skew, vol)
        bid_sizes, ask_sizes = self._sizes(mid)

        condition1 = (self.last_mid - mid) > (self.epsilon * mid)/10000
        condition2 = False#(self.prev_vol - vol) > (self.epsilon * vol)/10000
        condition3 = (self.prev_bid_skew - bid_skew) > (self.epsilon * bid_skew)/10000
        condition4 = (self.prev_ask_skew - ask_skew) > (self.epsilon * ask_skew)/10000

        if condition1 or condition2 or condition3 or condition4 or forced_requote:

            if isinstance(bid_prices, np.ndarray):
                for bid_price, bid_size in zip(bid_prices, bid_sizes):
                    bids.append(
                        Order(
                            symbol=self.symbol,
                            side=Side.BUY,
                            amount=round_step(bid_size, self.lot_size),
                            price=round_step(bid_price, self.tick_size),    
                            order_type=OrderType.LIMIT
                        )
                    )
            if isinstance(ask_prices, np.ndarray):
                for ask_price, ask_size in zip(ask_prices, ask_sizes):
                    asks.append(
                        Order(
                            symbol=self.symbol,
                            side=Side.SELL,
                            amount=round_step(ask_size, self.lot_size),
                            price=round_step(ask_price, self.tick_size),
                            order_type=OrderType.LIMIT  
                        )
                    )

        self.prev_vol = vol
        self.prev_bid_skew = bid_skew
        self.prev_ask_skew = ask_skew
        self.last_mid = mid

        return bids + asks

    def generate_quote(self, update: Dict[str, Any], position_value: float) -> List[Order]:
        mid = update["mid"]
        best_bid = update["best_bid"]["price"]
        best_ask = update["best_ask"]["price"]

        quotes = []

        if (self.last_mid - mid) > (self.epsilon * mid)/10000:
            bid_skew, ask_skew = self._skew(position_value)
            vol = self._volatility(mid)
            bid_prices, ask_prices = self._prices(mid, best_bid, best_ask, bid_skew, ask_skew, vol)
            bid_sizes, ask_sizes = self._sizes(mid)
            #print(f"vol: {vol}, bid_skew: {bid_skew * mid}, ask_skew: {ask_skew * mid}")

            for bid_price, bid_size, ask_price, ask_size in zip(bid_prices, bid_sizes, ask_prices, ask_sizes):
                quotes.append(
                    Order(
                        symbol=self.symbol,
                        side=Side.BUY,
                        amount=round_step(bid_size, self.lot_size),
                        price=round_step(bid_price, self.tick_size),    
                        order_type=OrderType.LIMIT
                    )
                )
                quotes.append(
                    Order(
                        symbol=self.symbol,
                        side=Side.SELL,
                        amount=round_step(ask_size, self.lot_size),
                        price=round_step(ask_price, self.tick_size),
                        order_type=OrderType.LIMIT  
                    )
                )

        self.last_mid = mid

        return quotes