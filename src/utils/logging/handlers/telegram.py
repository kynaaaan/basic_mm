
import asyncio
import aiohttp
import msgspec
from typing import List, Coroutine
from dataclasses import dataclass


@dataclass
class TelegramLogConfig:
    bot_token: str = None
    chat_id: str = None

    def validate(self) -> None:
        """
        Validates the Telegram configuration.
        """
        if not self.bot_token:
            raise ValueError("Missing bot token.")

        if not self.chat_id.isnumeric():
            raise ValueError(f"Invalid chat ID: {self.chat_id}")

class TelegramLogHandler:
    json_encoder = msgspec.json.Encoder()

    def __init__(self, config: TelegramLogConfig) -> None:
        self.chat_id = config.chat_id

        self.url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
        self.headers = {"Content-Type": "application/json"}

        self.client = aiohttp.ClientSession()

    async def flush(self, buffer) -> None:
        try:
            tasks: List[Coroutine] = []
            for log in buffer:
                payload = {
                    "chat_id": self.chat_id,
                    "text": log,
                    "disable_web_page_preview": True,
                }
                tasks.append(
                    self.client.post(
                        url=self.url,
                        headers=self.headers,
                        json=payload#self.json_encoder.encode(payload),
                    )
                )

            ext = await asyncio.gather(*tasks)
            return ext

        except Exception as e:
            print(f"Failed to send message to Telegram: {e}")

    async def close(self) -> None:
        await self.client.close()