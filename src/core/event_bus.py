from typing import Any, List, Dict
import asyncio

from src.utils.misc_utils import time_ms
from src.core.events import Event

class EventBus:
    def __init__(self, maxsize: int = 0) -> None:
        self._queue = asyncio.Queue(maxsize=maxsize)
        self._last_id = 0
        self._closed = False

    def _next_id(self) -> int:
        self._last_id += 1
        return self._last_id

    async def put(self, event_type: str, data: Any) -> int:
        if self._closed:
            raise RuntimeError("Queue is closed")
        seq_id = self._next_id()
        evt = Event(seq_id=seq_id, event_type=event_type, data=data, ts_ms=time_ms())
        await self._queue.put(evt)
        return seq_id

    async def get(self) -> Event:
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()

    def close(self) -> None:
        self._closed = True

class UnknownStreamKeyError(KeyError):
    pass

class MultiEventBus:
    def __init__(self, stream_keys: List[str], maxsize: int = 0) -> None:
        self._queues: Dict[str, EventBus] = {}
    
        for key in stream_keys:
            self._queues[key] = EventBus(maxsize=maxsize)
    
    async def put(self, stream_key: str, event_type: str, data: Any) -> int:
        if stream_key not in self._queues:
            raise UnknownStreamKeyError(f"Unknown stream key: {stream_key}")
        return await self._queues[stream_key].put(event_type, data)
    
    async def get(self, stream_key: str) -> Event:
        if stream_key not in self._queues:
            raise UnknownStreamKeyError(f"Unknown stream key: {stream_key}")
        return await self._queues[stream_key].get()
    
    def empty(self, stream_key: str) -> bool:
        if stream_key not in self._queues:
            raise UnknownStreamKeyError(f"Unknown stream key: {stream_key}")
        return self._queues[stream_key].empty()

    def close(self, stream_key: str) -> None:
        if stream_key not in self._queues:
            raise UnknownStreamKeyError(f"Unknown stream key: {stream_key}")
        self._queues[stream_key]._closed = True

    def keys(self) -> List[str]:
        return list(self._queues.keys())