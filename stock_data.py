import akshare as ak
import yfinance as yf
import baostock as bs
import pandas as pd
import requests
import io
import datetime
import contextlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union
import warnings

# Suppress pandas future warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

class StockDataProvider:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)

    def _get_yf_ticker(self, symbol: str, market: str) -> str:
        """
        Convert symbol to yfinance format.
        CN: 600519 -> 600519.SS
        US: BRK.B -> BRK-B
        """
        if market == "CN":
            # If already has suffix, trust it
            if symbol.endswith('.SS') or symbol.endswith('.SZ') or symbol.endswith('.BJ'):
                return symbol
                
            if symbol.startswith('6') or symbol.startswith('9'):
                return f"{symbol}.SS"
            elif symbol.startswith('0') or symbol.startswith('3') or symbol.startswith('2'):
                 return f"{symbol}.SZ"
            elif symbol.startswith('8') or symbol.startswith('4'):
                 return f"{symbol}.BJ"
            return symbol
        elif market == "US":
            return symbol.replace('.', '-')
        return symbol

    def get_price(self, symbol: str, market: str) -> Optional[Dict]:
        """
        Get current price for a single stock.
        """
        try:
            yf_symbol = self._get_yf_ticker(symbol, market)

            ticker = yf.Ticker(yf_symbol)
            
            # Fast info check
            info = ticker.fast_info
            price = info.last_price
            prev_close = info.previous_close
            
            # Fallback to history if fast_info is missing (sometimes happens)
            if price is None:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    prev_close = hist['Open'].iloc[0] # Approx
            
            change = 0
            change_percent = 0
            if price is not None and prev_close:
                change = price - prev_close
                if prev_close != 0:
                    change_percent = (change / prev_close) * 100
            
            # Get Name? yfinance info is slow.
            # For CN, getting English name from Yahoo is okay? Or use cached?
            # We accept English name or whatever Yahoo gives.
            name = ticker.info.get('shortName', symbol) if hasattr(ticker, 'info') else symbol

            return {
                "symbol": symbol,
                "market": market,
                "name": name,
                "price": price if price else 0,
                "change": change,
                "change_percent": change_percent,
                "volume": 0, # Optimization: skip volume if fast_info doesn't have it easily
                "currency": "CNY" if market == "CN" else "USD"
            }
        except Exception as e:
            return {
                 "symbol": symbol,
                 "market": market,
                 "error": str(e),
                 "price": 0, "change": 0, "change_percent": 0
            }

    def get_prices_batch(self, stocks: List[Dict[str, str]]) -> List[Dict]:
        """
        Fetch prices for multiple stocks efficiently using yfinance batch.
        """
        if not stocks:
            return []

        # Group by yfinance tickers
        yf_map = {} # yf_symbol -> original stock dict
        yf_tickers = []
        
        for s in stocks:
            # Use explicit yf_symbol if provided by get_market_tickers
            if 'yf_symbol' in s:
                yf_sym = s['yf_symbol']
            else:
                sym = s['symbol']
                mkt = s['market']
                yf_sym = self._get_yf_ticker(sym, mkt)
            
            yf_map[yf_sym] = s
            yf_tickers.append(yf_sym)

        results = []
        
        try:
            # yfinance batch fetch
            # download is faster for many tickers than Tickers(list)
            # Fetch 1 day of data
            # group_by='ticker' returns MultiIndex (Price, Ticker)
            with suppress_stdout(): # Silence yfinance noise
                data = yf.download(yf_tickers, period="1d", group_by='ticker', threads=True, progress=False)
            
            is_multi = isinstance(data.columns, pd.MultiIndex)

            for yf_sym in yf_tickers:
                orig = yf_map[yf_sym]
                try:
                    df = None
                    if is_multi:
                        if yf_sym in data.columns:
                             df = data[yf_sym]
                    else:
                        df = data

                    if df is not None and not df.empty:
                        price = df['Close'].iloc[-1]
                        
                        if pd.isna(price):
                            results.append({**orig, "error": "No price data"})
                            continue

                        prev = df['Open'].iloc[0]
                        change = price - prev
                        cp = (change/prev)*100 if prev != 0 else 0
                        
                        vol = df['Volume'].iloc[-1] if 'Volume' in df.columns else 0
                        
                        # Handle NaN volume
                        if pd.isna(vol): vol = 0

                        results.append({
                            "symbol": orig['symbol'],
                            "market": orig['market'],
                            "name": orig.get('name', orig['symbol']),
                            "price": price,
                            "change": change,
                            "change_percent": cp,
                            "volume": int(vol)
                        })
                    else:
                         results.append({**orig, "error": "No data returned"})

                except Exception as e:
                     results.append({**orig, "error": f"Parse error: {str(e)}"})
                     
        except Exception as e:
            # print(f"Batch fetch failed: {e}")
            for s in stocks:
                results.append(self.get_price(s['symbol'], s['market']))

        return results

    def get_history(self, symbol: str, market: str, period: str = "1mo") -> Optional[pd.DataFrame]:
        """
        Fetch historical data using yfinance for both.
        """
        try:
            yf_symbol = self._get_yf_ticker(symbol, market)
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period)
            
            if df.empty:
                return None
            
            df = df.reset_index()
            df = df.rename(columns={"Date": "Date", "Open": "Open", "Close": "Close", "High": "High", "Low": "Low", "Volume": "Volume"})
            df.set_index("Date", inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching history: {e}")
            return None

    def get_market_tickers(self, market: str) -> List[Dict]:
        """
        Fetch ONLY the list of tickers (symbol + name) for the market.
        Prices will be 0/None.
        """
        tickers = []
        try:
            if market == "CN":
                with suppress_stdout():
                    lg = bs.login()
                
                if lg.error_code != '0':
                    return []
                
                # Query recent trading days
                target_date = datetime.datetime.now()
                found_data = False
                
                for i in range(10): 
                    query_date = (target_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                    with suppress_stdout():
                        rs = bs.query_all_stock(day=query_date)
                    
                    if rs.error_code != '0':
                        continue
                        
                    current_day_tickers = []
                    while rs.next():
                         row = rs.get_row_data()
                         current_day_tickers.append(row)
                    
                    if current_day_tickers:
                        for row in current_day_tickers:
                            # row: [code, tradeStatus, code_name]
                            raw_code = row[0] # sh.600519
                            name = row[2]
                            
                            yf_suffix = ""
                            clean_code = raw_code
                            
                            if '.' in raw_code:
                                parts = raw_code.split('.')
                                exchange = parts[0]
                                clean_code = parts[1]
                                
                                if exchange == 'sh':
                                    yf_suffix = ".SS"
                                elif exchange == 'sz':
                                    yf_suffix = ".SZ"
                                elif exchange == 'bj':
                                    yf_suffix = ".BJ"
                            else:
                                # Fallback logic
                                pass # clean_code already set
                            
                            # Construct exact yf_symbol
                            yf_symbol = clean_code + yf_suffix
                            
                            tickers.append({
                                "symbol": clean_code,
                                "name": name,
                                "market": "CN",
                                "yf_symbol": yf_symbol, # Explicit mapping
                                "price": 0, "change_percent": 0
                            })
                        found_data = True
                        break 
                
                with suppress_stdout():
                    bs.logout()
                
            elif market == "US":
                # Use Wikipedia for S&P 500
                with suppress_stdout():
                    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    r = requests.get(url, headers=headers)
                    tables = pd.read_html(io.StringIO(r.text))
                    df = tables[0]
                
                for _, row in df.iterrows():
                    sym = row['Symbol']
                    # S&P 500 list uses dot, yfinance uses dash
                    yf_sym = sym.replace('.', '-')
                    
                    tickers.append({
                        "symbol": sym,
                        "name": row['Security'],
                        "market": "US",
                        "yf_symbol": yf_sym,
                        "price": 0, "change_percent": 0
                    })
                    
        except Exception as e:
            print(f"Error fetching ticker list: {e}")
            import traceback
            traceback.print_exc()
            return []
            
        return tickers
