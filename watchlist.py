from typing import List, Dict
from database import DatabaseManager

class WatchlistManager:
    def __init__(self):
        self.db = DatabaseManager()

    def get_watchlist(self) -> List[Dict[str, str]]:
        return self.db.get_watchlist()

    def add_stock(self, symbol: str, market: str):
        self.db.add_to_watchlist(symbol, market)

    def remove_stock(self, symbol: str):
        self.db.remove_from_watchlist(symbol)

