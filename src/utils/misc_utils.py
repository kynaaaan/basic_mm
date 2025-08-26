from time import (
    strftime,
    gmtime,
    time_ns,
    time as time_sec,
)
from datetime import datetime, timezone

def time_s() -> float:
    return time_sec()

def datetime_now() -> str:
    return strftime("%Y-%m-%d %H:%M:%S") + f".{(time_ns()//1000) % 1000000:05d}"

def time_ms() -> int:
    return time_ns()//1_000_000

def time_us() -> int:
    return time_ns()//1_000

def time_iso8601() -> str:

    millis = str((time_ns() % 1_000_000_000) // 1_000_000).zfill(3)
    return f"{strftime('%Y-%m-%dT%H:%M:%S', gmtime())}.{millis}Z"

def to_epoch_millis(value: datetime):
    assert value.tzinfo == timezone.utc, "`value` must be in UTC"

    return int(value.timestamp() * 1000)