import asyncio
import aiohttp
import json
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Union, Any, Literal

from src.utils.misc_utils import time_ms
from src.utils.logging.logger import Logger

class Client(ABC):
    """
    Client is an abstract base class for interfacing with various APIs.

    This class provides a template for API clients, handling common functionality
    such as session management, payload signing, error handling, and request sending
    with retry logic.
    """

    max_retries = 3

    # [https://github.com/ccxt/ccxt/blob/9ab59963f780c4ded7cd76ffa9e58b7f3fdd6e79/python/ccxt/base/exchange.py#L229]
    http_exceptions = {
        422: "ExchangeError",
        418: "DDoSProtection",
        429: "RateLimitExceeded",
        404: "ExchangeNotAvailable",
        409: "ExchangeNotAvailable",
        410: "ExchangeNotAvailable",
        451: "ExchangeNotAvailable",
        500: "ExchangeNotAvailable",
        501: "ExchangeNotAvailable",
        502: "ExchangeNotAvailable",
        520: "ExchangeNotAvailable",
        521: "ExchangeNotAvailable",
        522: "ExchangeNotAvailable",
        525: "ExchangeNotAvailable",
        526: "ExchangeNotAvailable",
        400: "ExchangeNotAvailable",
        403: "ExchangeNotAvailable",
        405: "ExchangeNotAvailable",
        503: "ExchangeNotAvailable",
        530: "ExchangeNotAvailable",
        408: "RequestTimeout",
        504: "RequestTimeout",
        401: "AuthenticationError",
        407: "AuthenticationError",
        511: "AuthenticationError",
    }

    def __init__(self, api_key: str, api_secret: str) -> None:
        """
        Initializes the Client class with API key and secret.

        Parameters
        ----------
        api_key : str
            The API key for authentication.

        api_secret : str
            The API secret for authentication.
        """
        self.api_key, self.api_secret = api_key, api_secret
        self.session = aiohttp.ClientSession()
        self.timestamp = time_ms()

        self.default_headers = {"Accept": "application/json"}
    
    def load_required_refs(self, logging: Logger) -> None:
        """
        Loads required references such as logging.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.
        """
        self.logging = logging

    def update_timestamp(self) -> int:
        """
        Updates and returns the current timestamp.

        This method updates the internal timestamp to the current time in milliseconds.

        Returns
        -------
        int
            The updated timestamp.
        """
        self.timestamp = time_ms()
        return self.timestamp

    async def response_code_checker(self, code: int) -> bool:
        """
        Check the status code and raise exceptions for errors.

        This method checks if the given HTTP status code is a known error code.
        It raises an exception with the reason for known error codes and for unknown status codes.

        Parameters
        ----------
        code : int
            The HTTP status code to check.

        Returns
        -------
        bool
            True if the status code is between 200 and 299 (inclusive).

        Raises
        ------
        Exception
            If the status code is known, the exception message includes the reason.
            If the status code is unknown, the exception message indicates it is unknown.
        """
        match code:
            case code if 200 <= code <= 299:
                return True

            case code if code in self.http_exceptions:
                reason = self.http_exceptions[code]
                self.logging.error(Exception(f"Known status code - {code} - {reason}"))

            case _:
                self.logging.error(Exception(f"Known status code - {code}"))

    @abstractmethod
    def sign_headers(self, method: str, header: Dict) -> Dict[str, Any]:
        """
        Sign & encrypt the header inline the appropriate exchange's needs.

        Parameters
        ----------
        method : str
            The header to be signed.

        header : Dict
            The header to be signed.
        Returns
        -------
        Dict[str, Any]
            The updated dictionary with the required signed/encrypted data.
        """
        pass

    async def request(
            self,
            url: str,
            method: Literal["GET", "PUT", "POST", "DELETE"],
            headers: Union[Dict[str, str], str] = None,
            params: Dict[str, str] = None,
            data: Dict[str, Any] = None,
            signed: bool = False,
        ) -> Union[Dict, Exception]:

        try:
            if headers and not signed:
                headers = self.sign_headers(method, headers)

            if data:
                data = json.dumps(data)

            response = await self.session.request(
                url=url,
                method=method,
                headers=headers,
                params=params,
                data=data,
            )

            if await self.response_code_checker(response.status) == False:
                response_json = await response.json()
                self.logging.error(f"CLIENT - Failed request: {response_json}")

            else:
                response_json = await response.json()

            return response_json

        except json.JSONDecodeError as e:
            self.logging.error(f"CLIENT - Failed to decode JSON: {e}")
            
        except Exception as e:
            self.logging.error(f"CLIENT - {e}")

    async def shutdown(self) -> None:
        """
        Close the client's HTTP session, if existing.

        Returns
        -------
        None
        """
        if self.session:
            await self.logging.info(topic="CLIENT", msg="Shutting down...")
            await self.session.close()
            del self.session