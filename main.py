from src.stream import StreamProvider
from src.market_maker import MarketMaker
from src.utils.logging.logger import Logger
from src.utils.logging.handlers.file import FileLogConfig
from src.utils.logging.handlers.telegram import TelegramLogConfig
from config.config import load_config
from src.core.event_bus import MultiEventBus
from src.exchanges.base.exchange import Exchange

import asyncio

config = load_config("config/base_config.yaml")


async def main():
    logging = Logger(
            file_config=FileLogConfig(filepath='file_log.txt'),
            telegram_config=TelegramLogConfig()
            )
    exch: Exchange = None
    
    exch.load_required_refs(logging)
    await exch.load_markets()

    symbols = config["mm"]["symbols"]
    queue = MultiEventBus(symbols)
    stream = StreamProvider(config, queue, logging)

    traders = \
        [
            MarketMaker(s, config["mm"]["symbol_params"][s], exch, logging, queue) for s in symbols
        ]
    tasks = \
        [
            *[t.start() for t in traders],
            stream.start()
        ]

    await asyncio.gather(*tasks)

asyncio.run(main())