from abc import ABC, abstractmethod
from typing import Dict, Union, List

from src.exchanges.base.structures import Order
from src.exchanges.base.constants import (
    SideConverter,
    OrderTypeConverter,
    TimeInForceConverter,
    SymbolConverter
)


class Formats(ABC):
    recvWindow = 1000

    def __init__(
        self,
        convert_side: SideConverter | None,
        convert_order_type: OrderTypeConverter | None,
        convert_time_in_force: TimeInForceConverter | None,
        convert_symbol: SymbolConverter | None
    ) -> None:
        self.convert_side = convert_side
        self.convert_order_type = convert_order_type
        self.convert_tif = convert_time_in_force
        self.convert_symbol = convert_symbol
        self.MAX_CANDLES = 5000

    @abstractmethod
    def create_order(self, order: Order) -> Dict:
        """
        Abstract method to create an order.

        Parameters
        ----------
        order: Order
            The order to be sent to the exchange.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    def amend_order(self, order: Order) -> Dict:
        """
        Abstract method to amend an existing order.

        Parameters
        ----------
        order: Order
            The order to be sent to the exchange.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    def cancel_order(self, order: Order) -> Dict:
        """
        Abstract method to cancel an existing order.

        Parameters
        ----------
        order: Order
            The order to amend.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    def cancel_all_orders(self, symbol: str) -> Dict:
        """
        Abstract method to cancel all existing orders for a symbol.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    def bulk_amend_order(self, orders: List[Order]) -> List[Dict] | None:
        pass

    def bulk_cancel_order(self, orders: List[Order]) -> List[Dict] | None:
        pass
    
    def bulk_create_order(self, orders: List[Order]) -> List[Dict] | None:
        pass