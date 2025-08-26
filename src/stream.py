import asyncio
from typing import Dict, Any
from src.utils.logging.logger import Logger

from src.exchanges.base.data.data import Data
from src.exchanges.base.data.handler import Handler
from src.core.event_bus import MultiEventBus

class StreamProvider:

    def __init__(self, config: Dict[str, Any], queue: MultiEventBus, logging: Logger):
        self.symbols = config["mm"]["symbols"]
        self.api_key = config["api_key"]

        self.logger = logging
        self._queue = queue

        self.data: Data = None

        self.x10_lob = {}
        for symbol in self.symbols:
            self.x10_lob[symbol]: Handler = None
        
        self.x10_account: Handler = None
    
    async def start(self):
        self.data.load_required_refs(self.logger)
    
        tasks = []
        for symbol in self.symbols:
            tasks.append(
                self.data.subscribe_orderbook(symbol, self.x10_lob[symbol].on_update, "1")
            )
        tasks.append(
            self.data.subscribe_account(self.x10_account.on_update)
        )
        await asyncio.gather(*tasks)

