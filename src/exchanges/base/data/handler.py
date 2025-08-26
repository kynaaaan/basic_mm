from abc import ABC, abstractmethod
from typing import Any, Optional, Dict

from src.core.event_bus import MultiEventBus


class Handler(ABC):
    def __init__(self, queue: MultiEventBus, stream_key: str, event_type: Optional[str] = None):
        self._queue = queue
        self.event_type = event_type
        self.stream_key = stream_key
    
    @abstractmethod
    def _process(self, data: Any) -> Any:
        """
        Process the incoming data and return the object to publish.
        Return None to skip publishing.
        """
        pass
    
    async def _publish(self, data: Any) -> None:
        if self.event_type is not None:
            await self._queue.put(self.stream_key, self.event_type, data)

    async def on_update(self, data: Any) -> None:
        processed_data = self._process(data)
        if processed_data is not None:
            await self._publish(processed_data)

class DuplexHandler(ABC):
    def __init__(self, queue: MultiEventBus, event_type: Optional[str] = None):
        self._queue = queue
        self.event_type = event_type
    
    @abstractmethod
    def _process(self, data: Any) -> Dict[str, Any]:
        """
        Process the incoming data and return the object to publish.
        Return a dict keyed by stream keys.
        """
        pass
    
    async def _publish(self, data: Dict[str, Any]) -> None:
        if self.event_type is not None:
            for key, key_data in data.items():
                await self._queue.put(key, self.event_type, key_data)

    async def on_update(self, data: Any) -> None:
        processed_data = self._process(data)
        if processed_data is not None:
            await self._publish(processed_data)