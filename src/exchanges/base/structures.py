from src.exchanges.base.constants import Side, OrderType

from typing import Optional, Dict, List
from dataclasses import dataclass


class Orderbook:
    def __init__(self, size: int = 100):
        self.size = size
        self.bids = {}  # price -> quantity
        self.asks = {}  # price -> quantity  
        self.seq_id = 0

    def update_snapshot(self, bids_data: List[Dict], asks_data: List[Dict], seq: int):
        """Update with snapshot data (absolute quantities)"""
        self.seq_id = seq
        self.bids = {float(item['p']): float(item['q']) for item in bids_data}
        self.asks = {float(item['p']): float(item['q']) for item in asks_data}

    def update_delta(self, bids_data: List[Dict], asks_data: List[Dict], seq: int):
        """Update with delta data (quantity changes)"""
        if seq <= self.seq_id:
            return
            
        self.seq_id = seq
        
        # Apply bid changes
        for item in bids_data:
            price, qty_change = float(item['p']), float(item['q'])
            if price in self.bids:
                new_qty = self.bids[price] + qty_change
                if new_qty <= 0:
                    del self.bids[price]
                else:
                    self.bids[price] = new_qty
            elif qty_change > 0:
                self.bids[price] = qty_change
        
        # Apply ask changes
        for item in asks_data:
            price, qty_change = float(item['p']), float(item['q'])
            if price in self.asks:
                new_qty = self.asks[price] + qty_change
                if new_qty <= 0:
                    del self.asks[price]
                else:
                    self.asks[price] = new_qty
            elif qty_change > 0:
                self.asks[price] = qty_change

    def get_bba(self):
        """Get best bid and ask [bid_price, bid_qty, ask_price, ask_qty]"""
        best_bid_price = max(self.bids.keys()) if self.bids else 0
        best_bid_qty = self.bids.get(best_bid_price, 0) if best_bid_price else 0
        
        best_ask_price = min(self.asks.keys()) if self.asks else 0
        best_ask_qty = self.asks.get(best_ask_price, 0) if best_ask_price else 0
        
        return [best_bid_price, best_bid_qty, best_ask_price, best_ask_qty]

    def get_mid(self):
        """Get mid price"""
        bba = self.get_bba()
        if bba[0] > 0 and bba[2] > 0:
            return (bba[0] + bba[2]) / 2.0
        return 0.0


@dataclass
class Order:
    symbol: str
    side: Side
    amount: float #contracts 
    price: float
    order_type: OrderType
    cloid: Optional[str] = None
    oid: Optional[str] = None
    tp: Optional[float] = None