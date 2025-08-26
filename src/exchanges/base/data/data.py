from typing import Callable, Dict
from abc import ABC, abstractmethod
import websockets
import json
import asyncio

from src.utils.logging.logger import Logger

class Data(ABC):

    def __init__(self, api_key: str, api_secret: str):

        self.api_key = api_key
        self.api_secret = api_secret

        self.WS_URL = None
        self.callbacks = {}
        self.subscriptions = {}
        self.active_subscriptions = set()

    def load_required_refs(self, logging: Logger) -> None:
        """
        Loads required references such as logging.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.
        """
        self.logging = logging

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def subscribe_orderbook(self, symbol: str, callback: Callable) -> None:
        pass
    
    @abstractmethod
    async def subscribe_trades(self, symbol: str, callback: Callable) -> None:
        pass

    @abstractmethod 
    async def subscribe_account(self, callback: Callable) -> None:
        pass
    
class MultiStreamData(Data):
    
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.connections = {}
        self.managed_subscriptions = set()
        self._shutting_down = False
    
    async def subscribe_orderbook(self, symbol: str, callback: Callable) -> None:
        pass
    
    async def subscribe_trades(self, symbol: str, callback: Callable) -> None:
        pass

    async def subscribe_account(self, callback: Callable) -> None:
        pass

    async def close(self) -> None:
        """
        Close all WebSocket connections.
        """
        self._shutting_down = True
        # Prefer closing currently tracked subscriptions
        for subscription_key, ws_connection in self.subscriptions.items():
            try:
                await ws_connection.close()
            except Exception as e:
                self.logging.error(f"Error closing connection for {subscription_key}: {e}")
        # Close any legacy-tracked connections if present
        for subscription_key, ws_connection in self.connections.items():
            try:
                await ws_connection.close()
            except Exception as e:
                self.logging.error(f"Error closing legacy connection for {subscription_key}: {e}")
        
        # Clear subscriptions
        self.subscriptions.clear()
        self.active_subscriptions.clear()
        self.logging.info("All exchange connections closed")
    
    async def _handle_subscription_messages(self, ws_connection, callback_key: str):
        """
        Handle messages for a specific WebSocket subscription.
        """
        try:
            async for message in ws_connection:
                try:
                    data = json.loads(message)
                    await self._process_subscription_message(data, callback_key)
                except json.JSONDecodeError:
                    self.logging.warning(f"Invalid JSON received on {callback_key}: {message}")
                except Exception as e:
                    self.logging.error(f"Error processing message for {callback_key}: {e}")
        except websockets.exceptions.ConnectionClosed as e:
            self.logging.warning(
                f"WebSocket connection closed for {callback_key}: code={getattr(e, 'code', None)} reason={getattr(e, 'reason', '')}"
            )
            # Remove from active subscriptions
            subscription_key = callback_key.replace("orderbook_", "").replace("trades_", "")
            if subscription_key in self.active_subscriptions:
                self.active_subscriptions.remove(subscription_key)
        except Exception as e:
            self.logging.error(f"WebSocket handler error for {callback_key}: {e}")
    
    async def _process_subscription_message(self, data: Dict, callback_key: str) -> None:
        """
        Process messages from specific subscriptions and route to appropriate callbacks.
        """
        try:
            if callback_key in self.callbacks:
                # Call the registered callback with the data
                await self.callbacks[callback_key](data)
            else:
                self.logging.warning(f"No callback registered for {callback_key}")
        except Exception as e:
            self.logging.error(f"Error in callback for {callback_key}: {e}")

    async def _handle_subscription_messages_with_resilience(
        self,
        ws_url: str,
        callback_key: str,
        subscription_key: str,
        headers: Dict[str, str] | None = None,
        ping_interval: int | None = 20,
        ping_timeout: int | None = 20,
        backoff_initial_seconds: float = 1.0,
        backoff_max_seconds: float = 30.0,
    ) -> None:
        """
        Maintain a resilient websocket subscription that auto-reconnects with exponential backoff.

        - Stores the active connection in `self.subscriptions[subscription_key]`
        - Adds/removes `subscription_key` in `self.active_subscriptions`
        - Calls `_process_subscription_message` for each received message
        - Logs detailed close code and reason when the connection drops
        """
        backoff_seconds = backoff_initial_seconds

        while not self._shutting_down:
            ws_connection = None
            try:
                connect_kwargs = {}
                if headers is not None:
                    connect_kwargs["extra_headers"] = headers
                if ping_interval is not None:
                    connect_kwargs["ping_interval"] = ping_interval
                if ping_timeout is not None:
                    connect_kwargs["ping_timeout"] = ping_timeout

                ws_connection = await websockets.connect(ws_url, **connect_kwargs)

                # Mark active and store connection
                self.subscriptions[subscription_key] = ws_connection
                self.active_subscriptions.add(subscription_key)
                print(f"Connected websocket for {callback_key} ({subscription_key})")
                self.logging.info(f"Connected websocket for {callback_key} ({subscription_key})")

                # Reset backoff on successful connect
                backoff_seconds = backoff_initial_seconds

                async for message in ws_connection:
                    try:
                        data = json.loads(message)
                        await self._process_subscription_message(data, callback_key)
                    except json.JSONDecodeError:
                        self.logging.warning(f"Invalid JSON received on {callback_key}: {message}")
                    except Exception as e:
                        self.logging.error(f"Error processing message for {callback_key}: {e}")

            except websockets.exceptions.ConnectionClosed as e:
                self.logging.warning(
                    f"WebSocket connection closed for {callback_key} ({subscription_key}): code={getattr(e, 'code', None)} reason={getattr(e, 'reason', '')}"
                )
            except Exception as e:
                self.logging.error(f"WebSocket handler error for {callback_key} ({subscription_key}): {e}")
            finally:
                # Cleanup
                if subscription_key in self.active_subscriptions:
                    self.active_subscriptions.remove(subscription_key)
                try:
                    if ws_connection is not None:
                        await ws_connection.close()
                except Exception:
                    pass
                self.subscriptions.pop(subscription_key, None)

            if self._shutting_down:
                break

            # Backoff before attempting to reconnect
            await asyncio.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, backoff_max_seconds)


class SingleStreamData(Data):

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.ws = None
    
    async def connect(self) -> None:
        try:
            self.logging.info(f"Connecting to exchange websocket streams...")
            self.ws = await websockets.connect(self.WS_URL)
            asyncio.create_task(self.ws_message_handler())
        except:
            self.logging.error("Failed to connect to exchange websocket streams.")
    
    async def close(self) -> None:
        if self.ws:
            await self.ws.close()
        self.logging.info("Exchange connections closed")

    async def ws_message_handler(self):
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self._process_ws_message(data)
                except json.JSONDecodeError:
                    self.logging.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    self.logging.error(f"Error processing WebSocket message: {e}")
        except websockets.exceptions.ConnectionClosed as e:
            self.logging.warning(
                f"WebSocket connection closed: code={getattr(e, 'code', None)} reason={getattr(e, 'reason', '')}"
            )
            # Attempt reconnection
            await asyncio.sleep(5)
            await self.connect()
        except Exception as e:
            self.logging.error(f"WebSocket handler error: {e}")
    
    @abstractmethod
    async def _process_ws_message(self, data: Dict) -> None:
        # Handler logic chain here
        pass








