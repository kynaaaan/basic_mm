from typing import List, Dict, Any
from src.utils.logging.logger import Logger

class PositionManager:

    def __init__(self, symbol: str, config: Dict[str, Any], logger: Logger):
        self.config = config
        self.symbol = symbol
        self.inventory_max_dollars = config["inventory_max_dollars"]
        self.logger = logger

        self.positions: Dict[str, float] = {}

    def update_positions(self, data: List[Dict]) -> None:
        for pos in data:
            symbol = pos["symbol"]
            status = pos.get("status", "")
            size = pos["position"]["value"]
            side = pos["position"]["side"]
            net_position = size * side
            if size >= self.inventory_max_dollars:
                    self.logger.warning(f"POSITION MANAGER {self.symbol} - {self.symbol} - ${size} - Over max inventory!")
            if status == "CLOSED":
                self.positions.pop(symbol, None)
            else:
                self.positions[symbol] = net_position
                    
    def get_position(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0)
    
    def get_all_positions(self) -> Dict[str, float]:
        return self.positions