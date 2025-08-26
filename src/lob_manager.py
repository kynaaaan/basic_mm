from typing import Dict, Any

from src.utils.logging.logger import Logger
from src.quoting_engines.volatility_estimator import VolatilityEstimator

class LOBManager:

    def __init__(self, config: Dict[str, Any], logger: Logger):
        self.config = config
        self.logger = logger

        self.mid = 0
        self.best_bid = 0
        self.best_ask = 0
        self.usdcusdt_rate = 1

        self.volatility_estimator = VolatilityEstimator(window_size=30)
        self.vol = 0

    def update_lob(self, data: Dict[str, Any]):
        self.mid = data["mid"]
        self.best_bid = data["best_bid"]["price"]
        self.best_ask = data["best_ask"]["price"] 
        self.vol = self.volatility_estimator.update(self.mid)/self.mid

    def update_usdcusdt_rate(self, data: Dict[str, Any]):
        self.usdcusdt_rate = data["mid"]

    def get_lob(self) -> Dict[str, Any]:
        return {
            "mid": self.mid,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "vol": self.vol
        }