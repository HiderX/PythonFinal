import sqlite3
import os
import datetime
import json
from enum import Enum

DATABASE_NAME = "stock_tracker.db"

class DatabaseManager:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Watchlist Table (Strictly symbol/market)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT,
                market TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, market)
            )
        ''')

        # Market Summary Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_summary (
                date TEXT PRIMARY KEY,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Market Tickers List Cache (Relational)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_tickers (
                symbol TEXT,
                market TEXT,
                name TEXT,
                price REAL,
                change_percent REAL,
                volume INTEGER,
                date TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, market, date)
            )
        ''')
        
        conn.commit()
        conn.close()

    # --- Watchlist Methods ---
    def add_to_watchlist(self, symbol: str, market: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT OR IGNORE INTO watchlist (symbol, market) VALUES (?, ?)', (symbol, market))
            conn.commit()
        finally:
            conn.close()

    def remove_from_watchlist(self, symbol: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # We remove by symbol regardless of market usually, or we should be specific.
            # The current app mostly refers to symbol. Let's delete all matches of symbol.
            cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
            conn.commit()
        finally:
            conn.close()

    def get_watchlist(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT symbol, market FROM watchlist ORDER BY added_at ASC')
            rows = cursor.fetchall()
            return [{"symbol": row[0], "market": row[1]} for row in rows]
        finally:
            conn.close()

    # --- Daily Market Data Methods (Relational) ---
    
    def check_market_data_freshness(self, market: str, date_str: str) -> bool:
        """
        Check if we have data for this market and date.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT 1 FROM market_tickers WHERE market = ? AND date = ? LIMIT 1', (market, date_str))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_market_tickers_list(self, market: str, date_str: str):
        """
        Get all stocks for a market and date.
        Returns list of dicts.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT symbol, name, market, price, change_percent, volume
                FROM market_tickers 
                WHERE market = ? AND date = ?
            ''', (market, date_str))
            rows = cursor.fetchall()
            return [{
                "symbol": r[0], "name": r[1], "market": r[2], 
                "price": r[3], "change_percent": r[4], "volume": r[5]
            } for r in rows]
        except:
            return []
        finally:
            conn.close()
            
    def save_market_tickers_list(self, market: str, date_str: str, tickers: list):
        """
        Bulk save tickers.
        tickers: list of dicts.
        """
        if not tickers:
            return

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Prepare data
            data = []
            now = datetime.datetime.now()
            for t in tickers:
                data.append((
                    t['symbol'], market, t.get('name', ''), 
                    t.get('price', 0), t.get('change_percent', 0), t.get('volume', 0),
                    date_str, now
                ))
            
            cursor.executemany('''
                INSERT OR REPLACE INTO market_tickers 
                (symbol, market, name, price, change_percent, volume, date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()
        finally:
            conn.close()

    def get_stock_data(self, symbol: str, market: str, date_str: str):
        """
        Get single stock data from DB.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT symbol, name, market, price, change_percent, volume
                FROM market_tickers
                WHERE symbol = ? AND market = ? AND date = ?
            ''', (symbol, market, date_str))
            row = cursor.fetchone()
            if row:
                return {
                    "symbol": row[0], "name": row[1], "market": row[2],
                    "price": row[3], "change_percent": row[4], "volume": row[5]
                }
            return None
        finally:
            conn.close()

    # --- Market Summary Methods ---
    def get_market_summary(self, date_str: str):
        """
        Get market summary for a specific date (YYYY-MM-DD).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT summary FROM market_summary WHERE date = ?', (date_str,))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def save_market_summary(self, date_str: str, summary: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT OR REPLACE INTO market_summary (date, summary) VALUES (?, ?)', (date_str, summary))
            conn.commit()
        finally:
            conn.close()

