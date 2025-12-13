import json
import os
from typing import List, Dict

class WatchlistManager:
    def __init__(self, filepath: str = "watchlist.json"):
        self.filepath = filepath
        self.watchlist = self._load_watchlist()

    def _load_watchlist(self) -> List[Dict[str, str]]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def save_watchlist(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.watchlist, f, indent=4, ensure_ascii=False)

    def add_stock(self, symbol: str, market: str):
        # Check if already exists
        for stock in self.watchlist:
            if stock['symbol'] == symbol and stock['market'] == market:
                return
        self.watchlist.append({"symbol": symbol, "market": market})
        self.save_watchlist()

    def remove_stock(self, symbol: str):
        self.watchlist = [s for s in self.watchlist if s['symbol'] != symbol]
        self.save_watchlist()

    def get_watchlist(self) -> List[Dict[str, str]]:
        return self.watchlist
