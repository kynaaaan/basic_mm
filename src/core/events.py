from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Event:
    seq_id: int
    event_type: str
    data: Any
    ts_ms: int