from multiprocessing import current_process
from typing import Dict, Any, List, Union, Set
import asyncio

from src.exchanges.base.constants import OrderType
from src.utils.logging.logger import Logger
from src.exchanges.base.structures import Order, Side, OrderType
from src.exchanges.base.exchange import Exchange
from src.utils.misc_utils import time_ms
from src.utils.calc_utils import nbabs
from src.utils.rounding_utils import round_step

class OMS:

    def __init__(self, symbol: str, config: Dict[str, Any], exchange: Exchange, logger: Logger):
        self.exch = exchange
        self.symbol = symbol
        self.num_orders = config["num_orders"]
        self.tp_distance = config["tp_distance"]
        self.tick_size = config["tick_size"]
        self.logger = logger

        self._overwrite = {"NEW", "PARTIALLY_FILLED"}
        self._remove = {"FILLED", "CANCELLED"}
        self._rejected = {"REJECTED"}
        self.orders_state: Dict[str, Order] = {}

        self.pending_levels: Dict[str, float] = {}
        self.timeout = 10.0 * 1000
        self.order_count = 0

    def _add_pending_level(self, level: str):
        """Add a level to pending with current timestamp"""
        self.pending_levels[level] = time_ms()
    
    def _remove_pending_level(self, level: str):
        """Remove a level from pending"""
        try:
            del self.pending_levels[level]
        except KeyError:
            pass

    def _cleanup_stale_pending(self, level: str):
        """Remove pending levels that have exceeded timeout"""
        if level not in self.pending_levels:
            return 
        curr = time_ms()
        if curr - self.pending_levels[level] > self.timeout:
            self.logger.warning(f"OMS {self.symbol} - Cleaning up stale pending level: {level}")
            del self.pending_levels[level]

    
    def _is_level_pending(self, level: str) -> bool:
        """Check if level is pending (with automatic cleanup)"""
        self._cleanup_stale_pending(level)
        return level in self.pending_levels

    def update_orders_state(self, data: List[Dict]) -> bool:

        filled = []

        for order in data:
            cloid = order["order"]["cloid"]
            level = cloid[-3:]

            if order['status'] in self._overwrite:
                parsed_order = Order(**order["order"])
                if parsed_order.oid is not None:
                    new = {parsed_order.oid: parsed_order} 
                    self.orders_state.update(new)
                    if level != "_tp":
                        self.order_count += 1
                        self._remove_pending_level(level)
                else:
                    self.logger.error(f"Order {parsed_order} has no oid")
                    if level and level != '_tp':
                        self._remove_pending_level(level)
                    continue

            elif order['status'] in self._remove:
                oid = order["order"]["oid"]
                is_tp = cloid[-3:] == "_tp"
                if oid in self.orders_state:
                    if order['status'] == "FILLED" and not is_tp:
                        self.logger.info(f"FILL {self.symbol} - {order['order']['symbol']} - {order['order']['amount']} contracts @ {order['order']['price']}")
                        filled.append(self.orders_state[oid])
                    del self.orders_state[oid]
                    if not is_tp:
                        self.order_count -= 1
                        self._remove_pending_level(level)
            
            elif order['status'] in self._rejected:
                self.logger.info(f"OMS {self.symbol} - Order rejected! {order}")
                self._remove_pending_level(level)

        if filled:
            asyncio.create_task(self._place_take_profits(filled))
            self.logger.info(   f"OMS {self.symbol} - PLACING TPS FOR: {filled}")

    async def cancel_all(self):
        response = await self.exch.cancel_all_orders(self.symbol)
        if isinstance(response, dict) and response.get("status") == "ERROR":
            self.logger.warning(f"OMS {self.symbol} - {response.get('error')}")
        else:
            self.pending_levels.clear()

    async def cancel_orders(self, orders: List[Order]):
        response = await self.exch.bulk_cancel_order(orders)
        if isinstance(response, list):
            for i in response:
                if isinstance(i, dict) and i.get("status") == "ERROR":
                    self.logger.warning(f"OMS {self.symbol} - {i.get('error')}")

    async def place_orders(self, orders: List[Order]):
        tasks = [
            self.exch.create_order(order) for order in orders
        ]
        try:
            response = await asyncio.gather(*tasks, return_exceptions=True)
            for i, res in enumerate(response):
                if isinstance(res, Exception):
                    self.logger.error(f"OMS {self.symbol} - Order placement failed: {res}")
                elif isinstance(res, dict) and res.get("status") == "ERROR":
                    self.logger.warning(f"OMS {self.symbol} - {res.get('error')}")
                    
            return response
        except Exception as e:
            self.logger.error(f"OMS {self.symbol} - asyncio.gather failed: {e}")
            return []
    
    async def amend_orders(self, orders: List[Order]):
        tasks = [
            self.exch.amend_order(order) for order in orders
        ]
        try:
            response = await asyncio.gather(*tasks, return_exceptions=True)
            for res in response:
                if isinstance(res, Exception):
                    self.logger.error(f"OMS {self.symbol} - Order amend failed: {res}")
                elif isinstance(res, dict) and res.get("status") == "ERROR":
                    self.logger.warning(f"OMS {self.symbol} - {res.get('error')}")
            return response
        except Exception as e:
            self.logger.error(f"OMS {self.symbol} - asyncio.gather failed (amend): {e}")
            return []
    
    async def _place_take_profits(self, filled_orders: List[Order]):
        try:
            tp_orders = []
            for order in filled_orders:
                tp_order = Order(
                    symbol=self.symbol,
                    side=Side.SELL if order.side == Side.BUY else Side.BUY,
                    amount=order.amount,
                    price=round_step(order.price * (1 + self.tp_distance/10000) if order.side == Side.BUY 
                        else order.price * (1 - self.tp_distance/10000), self.tick_size),
                    order_type=OrderType.LIMIT,
                    cloid=order.cloid + "_tp"
                )
                tp_orders.append(tp_order)
            
            res = await self.place_orders(tp_orders)
            print(f'TP RESPONSE {self.symbol}: {res}')
            self.logger.info(f"OMS {self.symbol} - Placed {len(tp_orders)} take profit orders")
        
        except Exception as e:
            self.logger.error(f"OMS {self.symbol} - Failed to place take profits: {e}")

    def is_out_of_bounds(self, old_order: Order, new_order: Order, mid: float, sensitivity: float=0.1) -> bool:
        """
        Check if the new order's price is out of bounds compared to the old order's price.

        Steps
        -----
        1. Calculate the distance from the mid price using the old order's price.
        2. Determine the acceptable price range using the sensitivity factor.
        3. Check if the new order's price is within the acceptable range.
        4. Return True if the price is out of bounds, otherwise return False.

        Parameters
        ----------
        old_order : Order
            The old order.

        new_order : Order
            The new order.

        sensitivity : float, optional
            The sensitivity factor for determining out-of-bounds (default is 0.1 or 10%).

        Returns
        -------
        bool
            True if the new order's price is out of bounds, False otherwise.
        """
        if old_order == None:
            return False

        distance_from_mid = nbabs(old_order.price - mid)
        buffer = distance_from_mid * sensitivity
        
        if new_order.price > (old_order.price + buffer):
            return True
        
        elif new_order.price < (old_order.price - buffer):
            return True

        else:
            return False

    def find_matched_order(self, new_order: Order) -> Union[Order, None]:
        """
        Attempt to find the order with a matching level number.

        Steps
        -----
        1. Extract the level number from the `cloid` of the `new_order`.
        2. Iterate through the current orders in `self.data["orders"]`.
        3. Compare the level number of each current order with the `new_order` level number.
        4. Return the first matching order found, or an empty Order if no match is found.

        Parameters
        ----------
        new_order : Order
            The new order from the quote generator.  
        
        Returns
        -------
        Order
            The order with the closest price to the target price and matching side.
        """
        new_order_level = new_order.cloid[-3:]

        for oid, current_order in self.orders_state.items():
            if current_order.cloid[-3:] == new_order_level:
                return current_order
        return None

    async def update(self, new_orders: List[Order], lob: Dict):
        mid = lob["mid"]

        limits = []
        markets = []
        cancels = []
        amends = []
            
        for order in new_orders:
            match order.order_type:
                case OrderType.MARKET:
                    markets.append(order)
                case OrderType.LIMIT:
                    level = order.cloid[-3:]

                    if self._is_level_pending(level):
                        self.logger.warning(f"OMS {self.symbol} - Skipping level {level} - already pending")
                        continue

                    matched_old_order = self.find_matched_order(order)
                    if matched_old_order != None:
                        out_of_bounds = self.is_out_of_bounds(matched_old_order, order, mid)
                        if out_of_bounds:
                            self._add_pending_level(level)
                            order.oid = matched_old_order.cloid
                            amends.append(order)
                    else:
                        self._add_pending_level(level)
                        limits.append(order) 
        if markets:
            await self.place_orders(markets)
            await self.cancel_all()
        
        tasks = []
        if cancels:
            tasks.append(self.cancel_orders(cancels))
        if limits:
            tasks.append(self.place_orders(limits))
        if amends:
            tasks.append(self.amend_orders(amends))

        await asyncio.gather(*tasks)

        if self.order_count > self.num_orders:
            self.logger.warning(F"OMS {self.symbol} - {self.order_count} > {self.num_orders}, Exceeding max orders! Cancelling all...")
            await self.cancel_all()
    
    async def simple_update(self, new_orders: List[Order]): 
        try:
            await self.cancel_all()
            await self.place_orders(new_orders)
        except Exception as e:
            self.logger.error(f"OMS {self.symbol} - Simple Update Error - {e}")


        


