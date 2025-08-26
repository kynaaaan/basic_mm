import asyncio
import json
from symtable import Symbol
from typing import Dict, Any
from collections import defaultdict

from src.utils.logging.logger import Logger
from src.utils.misc_utils import time_ms, time_us
from src.exchanges.base.exchange import Exchange
from src.quoting_engines.simple import SimpleQuoter
from src.OMS import OMS
from src.position_manager import PositionManager
from src.lob_manager import LOBManager
from src.core.event_bus import MultiEventBus
from src.core.events import Event
from src.exchanges.base.constants import SymbolConverter

class MarketMaker:

    def __init__(self, symbol: str, config: Dict[str, Any], exchange: Exchange, logger: Logger, queue: MultiEventBus):

        self.logger = logger
        self.exchange = exchange
        self.queue = queue
        self.symbol = symbol
        self.exch_symbol = SymbolConverter().to_exch(self.symbol)
        self.config = config

        self.has_orderbook = False
        self.has_position = False
        self.has_usdcusdt = False
        
        # Add rate limiting for requotes
        self.last_requote_time = 0
        self.min_requote_interval = self.config["min_requote_interval"]  * 1000

        self.event_handlers = \
            {
                "orderbook": self._on_orderbook_updates,
                "position": self._on_position_updates,
                "order": self._on_order_updates,
                "USDCUSDT": self._on_usdcusdt_updates,
            }
        
        self.quoting_engine = SimpleQuoter(config, logger)
        self.oms = OMS(self.symbol, config, exchange, logger)
        self.position_manager = PositionManager(self.symbol, config, logger)
        self.lob_manager = LOBManager(config, logger)

        self.measure_t2t = True
        self.t2t_log_every = 100
        self._t2t_stats = defaultdict(lambda: {"count": 0, "sum": 0.0, "max": 0.0})

        self.measure_requote_latency = True
        self.requote_log_every = 100
        self._requote_stats = {
            "quote_gen": {"count": 0, "sum": 0.0, "max": 0.0},
            "oms_update": {"count": 0, "sum": 0.0, "max": 0.0},
            "total": {"count": 0, "sum": 0.0, "max": 0.0}
        }

    async def start(self):

        try:
            await self._process_events()
        except Exception as e:
            self.logger.error(f"MAKER {self.symbol} - Error starting market maker: {e}")
            raise

    def stop(self):
        pass

    async def _process_events(self):
        while True:
            try:
                event = await self.queue.get(self.symbol)
                await self._process_event(event)
            except asyncio.CancelledError:
                self.logger.info(f"MAKER {self.symbol} - Event processing cancelled")
                break
            except Exception as e:
                self.logger.error(f"MAKER {self.symbol} - Error processing event: {e}")
                await asyncio.sleep(0.5)

    async def _process_event(self, event: Event) -> None:
        if self.measure_t2t:
            try:
                t2t_ms = time_ms() - event.ts_ms
                self._record_t2t(event.event_type, t2t_ms)
            except Exception:
                pass

        handler = self.event_handlers.get(event.event_type)
        if handler:
            payload = json.loads(event.data) if isinstance(event.data, str) else event.data
            await handler(payload)
        else:
            self.logger.debug(f"MAKER {self.symbol} - No handler for event type: {event.event_type}")

    def _record_t2t(self, event_type: str, t2t_ms: float) -> None:
        stats = self._t2t_stats[event_type]
        stats["count"] += 1
        stats["sum"] += t2t_ms
        if t2t_ms > stats["max"]:
            stats["max"] = t2t_ms

        if stats["count"] % self.t2t_log_every == 0:
            avg = stats["sum"] / stats["count"] if stats["count"] else 0.0
            print(f"MAKER {self.symbol} - T2T {event_type}: last={t2t_ms:.1f}ms avg={avg:.1f}ms max={stats['max']:.1f}ms over {stats['count']} events")
            self.logger.info(
                f"MAKER {self.symbol} - T2T {event_type}: last={t2t_ms:.1f}ms avg={avg:.1f}ms max={stats['max']:.1f}ms over {stats['count']} events"
            )

    def _record_requote_latency(self, component: str, latency_ms: float) -> None:
        """Record requote component latency similar to T2T tracking"""
        stats = self._requote_stats[component]
        stats["count"] += 1
        stats["sum"] += latency_ms
        if latency_ms > stats["max"]:
            stats["max"] = latency_ms

        if component == "total" and stats["count"] % self.requote_log_every == 0:
            self._log_requote_stats(stats["count"])

    def _log_requote_stats(self, count: int) -> None:
        """Log comprehensive requote latency statistics"""
        print("-"*20)
        output_lines = [f"MAKER {self.symbol} - REQUOTE LATENCY STATS (over {count} requotes):"]
        
        for component, stats in self._requote_stats.items():
            if stats["count"] > 0:
                avg = stats["sum"] / stats["count"]
                output_lines.append(
                    f"  {component.upper()}: avg={avg:.1f}us max={stats['max']:.1f}us"
                )
        
        for line in output_lines:
            print(line)
        print("-"*20)
        
        self.logger.info("\n".join(output_lines))

    async def _on_usdcusdt_updates(self, data):
        self.has_usdcusdt = True
        self.lob_manager.update_usdcusdt_rate(data)
        await self.requote()

    async def _on_orderbook_updates(self, data):
        self.lob_manager.update_lob(data)
        self.has_orderbook = True
        await self.requote()

    async def _on_position_updates(self, data):
        self.position_manager.update_positions(data)
        self.has_position = True
        await self.requote()
        
    async def _on_order_updates(self, data):
        requote_on_filled = self.oms.update_orders_state(data)
        if requote_on_filled:
            await self.requote(forced_requote = False)

    async def requote(self, forced_requote = False):
        current_time = time_ms()
        
        if not forced_requote and (current_time - self.last_requote_time) < self.min_requote_interval:
            return
        self.last_requote_time = current_time
    
        t1 = time_us()
        lob = self.lob_manager.get_lob()
        pos = self.position_manager.get_position(self.exch_symbol)
        quotes = self.quoting_engine.generate_quote_v2(lob, pos, forced_requote)
        t2 = time_us()
        if quotes != []:
            await self.oms.update(quotes, lob)
            t3 = time_us()
            if self.measure_requote_latency:
                quote_gen_latency = (t2 - t1)
                oms_latency = (t3 - t2) 
                total_latency = (t3 - t1)
                self._record_requote_latency("quote_gen", quote_gen_latency)
                self._record_requote_latency("oms_update", oms_latency)
                self._record_requote_latency("total", total_latency)
    