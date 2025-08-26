import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Union, List

from src.utils.logging.logger import Logger
from src.exchanges.base.client import Client
from src.exchanges.base.formats import Formats
from src.exchanges.base.endpoints import Endpoints
from src.exchanges.base.constants import Side, OrderType, TIF
from src.exchanges.base.structures import Order


class Exchange(ABC):
    def __init__(
        self,
        client: Client,
        formats: Formats,
        endpoints: Endpoints,
    ) -> None:
        """
        Initializes the Exchange class with the necessary components.

        Parameters
        ----------
        client : Client
            The client instance to interact with the exchange.

        formats : Formats
            The formats instance used to format various exchange-related data.

        endpoints : Endpoints
            The endpoints instance containing the URLs for the exchange's API endpoints.
        """
        self.client = client
        self.formats = formats
        self.endpoints = endpoints
        self.base_endpoint = self.endpoints.rest

    def load_required_refs(self, logging: Logger) -> None:
        """
        Loads required references such as logging, symbol, and data.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.

        symbol : str
            The trading symbol.

        data : Dict
            A Dictionary holding various shared state data.
        """
        self.logging = logging
        self.client.load_required_refs(logging=logging)

    @abstractmethod
    async def create_order(self, order: Order) -> Dict:
        """
        Abstract method to create an order.

        Parameters
        ----------
        order: Order
            The order to send to the exchange.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def amend_order(self, order: Order) -> Dict:
        """
        Abstract method to amend an existing order.

        Parameters
        ----------
        order: Order
            The order to modify/amend.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def cancel_order(self, order: Order) -> Dict:
        """
        Abstract method to cancel an existing order.

        Parameters
        ----------
        order: Order
            The order to cancel.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def cancel_all_orders(self, symbol: str) -> Dict:
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

    async def shutdown(self) -> None:
            await self.logging.info(topic="EXCH", msg=f"Shutting down...")
            await self.client.shutdown()