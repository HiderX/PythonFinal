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
from database import DatabaseManager

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
        self.ticker_cache = {"CN": [], "US": []}
        self.db = DatabaseManager()

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
    
    def _ensure_cache(self):
        """
        Populate cache if empty. 
        """
        if not self.ticker_cache["CN"]:
            # print("Caching CN tickers...") # Let UI handle status
            self.ticker_cache["CN"] = self.get_market_tickers("CN")
            
        if not self.ticker_cache["US"]:
            # print("Caching US tickers...")
            self.ticker_cache["US"] = self.get_market_tickers("US")

    def search_stocks(self, keyword: str) -> List[Dict]:
        """
        Search for stocks by symbol or name across all cached markets.
        Case insensitive.
        """
        self._ensure_cache()
        
        kw = keyword.lower()
        matches = []
        
        # Search CN
        for t in self.ticker_cache["CN"]:
            if kw in t['symbol'].lower() or kw in t['name'].lower():
                matches.append(t)
                
        # Search US
        for t in self.ticker_cache["US"]:
             if kw in t['symbol'].lower() or kw in t['name'].lower():
                matches.append(t)
        
        # Limit to 20 results for UX
        return matches[:20]

    def get_price(self, symbol: str, market: str, force_web: bool = False) -> Optional[Dict]:
        """
        Get current price for a single stock.
        """
        if not force_web:
             # Check DB first
             date_str = datetime.datetime.now().strftime("%Y-%m-%d")
             
             # If market list is stale, refresh it first?
             # User Req: "Check individual stock detail from market list database... if stale, refresh list"
             if not self.db.check_market_data_freshness(market, date_str):
                 self.get_market_tickers(market) # This refreshes DB
             
             if not self.db.check_market_data_freshness(market, date_str):
                 self.get_market_tickers(market) # This refreshes DB
             
             # Now check DB (Relational lookup)
             row = self.db.get_stock_data(symbol, market, date_str)
             if row:
                 # Check if price is valid (CN might be 0)
                 if row.get('price', 0) != 0:
                     # Calculate change from price and percent
                     price = row.get('price', 0)
                     cp = row.get('change_percent')
                     if cp is None:
                         cp = 0
                     change = 0
                     if price != 0:
                         # price = prev * (1 + cp/100) => prev = price / (1 + cp/100)
                         # change = price - prev
                         try:
                             prev = price / (1 + cp/100)
                             change = price - prev
                         except:
                             change = 0
                     
                     return {**row, "change": change, "currency": "CNY" if market == "CN" else "USD", "volume": row.get('volume', 0)}
            
             # If row missing or price 0, fall through to web fetch
             
        try:
            with suppress_stdout():
                yf_symbol = self._get_yf_ticker(symbol, market)
                # ... (Web fetch logic remains same) ...
    
                ticker = yf.Ticker(yf_symbol)
                
                # Fast info check
                try:
                    info = ticker.fast_info
                    price = info.last_price
                    prev_close = info.previous_close
                except:
                    price = None
                    prev_close = None
                
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
                try:
                    name = ticker.info.get('shortName', symbol)
                except:
                    name = symbol
    
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
            # Silence specific yfinance errors
            return {
                 "symbol": symbol,
                 "market": market,
                 "error": "Stock not found" if "404" in str(e) or "Not Found" in str(e) else str(e),
                 "price": 0, "change": 0, "change_percent": 0
            }

    def get_prices_batch(self, stocks: List[Dict[str, str]]) -> List[Dict]:
        """
        Fetch prices for multiple stocks.
        """
        if not stocks:
            return []

        results = []
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 1. Ensure Market DB is fresh for relevant markets
        markets = set(s['market'] for s in stocks)
        for m in markets:
            if not self.db.check_market_data_freshness(m, date_str):
                self.get_market_tickers(m) # Update global list

        # 2. Try to fetch from DB (Efficiently iterate JSON lists)
        # Load market caches once
        market_caches = {}
        for m in markets:
             lst = self.db.get_market_tickers_list(m, date_str)
             if lst:
                 # Convert to dict for fast lookup: symbol -> item
                 market_caches[m] = {item['symbol']: item for item in lst}
             else:
                 market_caches[m] = {}

        missing_stocks = []
        for s in stocks:
            m = s['market']
            sym = s['symbol']
            
            row = market_caches.get(m, {}).get(sym)
            
            if row and row.get('price', 0) != 0:
                # Calculate change safely
                price = row.get('price', 0)
                cp = row.get('change_percent')
                if cp is None:
                    cp = 0
                
                change = 0
                if price != 0:
                    try:
                        prev = price / (1 + cp/100)
                        change = price - prev
                    except:
                        change = 0

                results.append({
                    "symbol": row['symbol'],
                    "market": row['market'],
                    "name": row['name'],
                    "price": price,
                    # Cached list might not have volume/change, assume 0 or stored
                    "change": change,
                    "change_percent": cp,
                    "volume": row.get('volume', 0)
                })
            else:
                missing_stocks.append(s)
                
        if not missing_stocks:
            return results

        # 3. Fetch missing individually (update DB along the way)
        # We reuse the logic: get_price(force_web=True) will fetch and we can save it.
        # But get_price(force_web=False) logic above falls through to web if DB missing.
        # So we can just call self.get_price(..., force_web=True) for missing.
        # Batch fetching is better for US though.
        
        # Original batch split logic
        yf_map = {} 
        yf_tickers = []
        to_fetch_batch = []
        
        for s in missing_stocks:
             # reuse batch logic below
             # Use explicit yf_symbol if provided by get_market_tickers
            if 'yf_symbol' in s:
                yf_sym = s['yf_symbol']
            else:
                sym = s['symbol']
                mkt = s['market']
                yf_sym = self._get_yf_ticker(sym, mkt)
            
            yf_map[yf_sym] = s
            yf_tickers.append(yf_sym)
            to_fetch_batch.append(s)

        if not to_fetch_batch:
            return results



        
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
                        # Drop rows where Close is NaN (e.g. current day before market open)
                        df = df.dropna(subset=['Close'])
                        
                        if df.empty:
                             results.append({**orig, "error": "No price data"})
                             continue
                             
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

                        # Cache the result 
                        # Use one dict for both cache update and return
                        res_data = {
                            "symbol": orig['symbol'],
                            "market": orig['market'],
                            "price": price,
                            "change_percent": cp,
                            "change": change,
                            "volume": int(vol),
                            "name": orig.get('name', orig['symbol']),
                            "date": date_str
                        }
                        
                        results.append(res_data)
                        
                        # Update cache in JSON List?
                        # This is a bit expensive to read-modify-write the whole list for every item in batch
                        # But since we are likely updating many items, maybe we should update the DB once at end?
                        # For simplicity in this requirement, we can update individual items via helper or assume the Global Refresh above handled most.
                        # If we are here, it means Global Refresh didn't have it.
                        self._update_single_stock_in_db(res_data['symbol'], res_data['market'], res_data)
                    else:
                         results.append({**orig, "error": "No data returned"})

                except Exception as e:
                     results.append({**orig, "error": f"Parse error: {str(e)}"})
                     
        except Exception as e:
            # print(f"Batch fetch failed: {e}")
            for s in missing_stocks:
                results.append(self.get_price(s['symbol'], s['market']))

        return results

    def _update_single_stock_in_db(self, symbol: str, market: str, data: Dict = None):
        """
        Fetch (or use provided) data and update one row in the DB.
        """
        if data is None:
             data = self.get_price(symbol, market, force_web=True)
             
        if "error" in data:
            return data

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Construct item for save
        item = {
             "symbol": symbol,
             "name": data.get('name', symbol),
             "market": market,
             "price": data['price'],
             "change_percent": data['change_percent'],
             "volume": data.get('volume', 0)
        }
             
        self.db.save_market_tickers_list(market, date_str, [item])
        return data

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
        Fetch Global Market List.
        If DB fresh -> Return from DB.
        If DB stale -> Fetch Web -> Update DB -> Return.
        For US: Also fetches prices.
        """
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 1. Check DB Freshness
        if self.db.check_market_data_freshness(market, date_str):
             return self.db.get_market_tickers_list(market, date_str)
             
        # 2. Fetch from Web
        tickers = []
        try:
            if market == "CN":
                with suppress_stdout():
                    # Use Akshare for Spot Data (includes Price/Volume)
                    # stock_zh_a_spot_em returns: code, name, latest_price, change_rate, volume, amount, ...
                    try:
                        df = ak.stock_zh_a_spot_em()
                        # Columns: 序号, 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, ...
                        # Rename for consistency
                        
                        # Data processing
                        for _, row in df.iterrows():
                            code = str(row['代码'])
                            name = str(row['名称'])
                            price = row['最新价']
                            change_percent = row['涨跌幅']
                            volume = row['成交量']
                            
                            # Clean invalid data
                            try:
                                if pd.isna(price):
                                    price = float(row.get('昨收', 0))
                                else:
                                    price = float(price)
                            except: price = 0
                            
                            try:
                                if pd.isna(change_percent):
                                    change_percent = 0
                                else:
                                    change_percent = float(change_percent)
                            except: change_percent = 0
                                
                            try:
                                volume = int(volume)
                            except: volume = 0

                            yf_suffix = ""
                            if code.startswith('6'): yf_suffix = ".SS"
                            elif code.startswith('9') and len(code) == 6 and code[1] == '0': yf_suffix = ".SS" # 900xxx B-shares?
                            # 920 is Beijing
                            elif code.startswith('9') and code.startswith('92'): yf_suffix = ".BJ"
                            elif code.startswith('0') or code.startswith('3'): yf_suffix = ".SZ"
                            elif code.startswith('8') or code.startswith('4'): yf_suffix = ".BJ"
                            
                            tickers.append({
                                "symbol": code,
                                "name": name,
                                "market": "CN",
                                "yf_symbol": code + yf_suffix,
                                "price": price,
                                "change_percent": change_percent,
                                "volume": volume
                            })
                            
                    except Exception as e:
                         print(f"Akshare fetch failed: {e}")
                         return []
            
            elif market == "US":
                 # Use Wikipedia + Batch Price Fetch
                 try:
                    with suppress_stdout():
                        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        r = requests.get(url, headers=headers, timeout=15)
                        tables = pd.read_html(io.StringIO(r.text))
                        df = tables[0]
                    
                    us_tickers_list = []
                    for _, row in df.iterrows():
                        sym = row['Symbol']
                        yf_sym = sym.replace('.', '-')
                        us_tickers_list.append({
                            "symbol": sym,
                            "name": row['Security'],
                            "market": "US",
                            "yf_symbol": yf_sym
                        })
                        
                    # Batch Fetch Prices for US
                    # We can pass into get_prices_batch logic or manual
                    # Let's do a manual efficient batch fetch
                    all_yf = [t['yf_symbol'] for t in us_tickers_list]
                    with suppress_stdout():
                        data = yf.download(all_yf, period="1d", group_by='ticker', threads=True, progress=False)
                        
                    is_multi = isinstance(data.columns, pd.MultiIndex)
                    
                    for item in us_tickers_list:
                        sym = item['yf_symbol']
                        price = 0
                        cp = 0
                        vol = 0
                        
                        # Extract price
                        try:
                            if is_multi:
                                if sym in data.columns:
                                     idf = data[sym]
                            else:
                                idf = data
                                
                            if idf is not None and not idf.empty:
                                 close = idf['Close'].dropna().iloc[-1]
                                 if not pd.isna(close):
                                     price = close
                                     prev = idf['Open'].iloc[0]
                                     if prev != 0:
                                         cp = (price - prev)/prev * 100
                                     
                                     vol = idf['Volume'].iloc[-1]
                                     if pd.isna(vol): vol = 0
                        except:
                            pass
                            
                            
                        tickers.append({
                            **item,
                            "price": price,
                            "change_percent": cp,
                            "volume": int(vol) if vol else 0
                        })

                 except Exception as e:
                    print(f"US Fetch Error: {e}")
                    # Fallback logic if needed
                    pass

        except Exception as e:
            traceback.print_exc()
            return []
            
        # Save to DB
        if tickers:
            self.db.save_market_tickers_list(market, date_str, tickers)
            
        return tickers

    def get_market_indices(self) -> List[Dict]:
        """
        Fetch data for major market indices.
        CN: 上证指数, 深证成指, 创业板指
        US: S&P 500, Dow Jones, NASDAQ
        """
        # Hardcoded indices
        # Note: yfinance symbols for indices usually start with ^
        indices = [
            # CN Indices (Using 000001.SS for SH Comp, 399001.SZ for SZ Comp, 399006.SZ for ChiNext)
            {"symbol": "000001.SS", "name": "上证指数", "market": "CN", "yf_symbol": "000001.SS"},
            {"symbol": "399001.SZ", "name": "深证成指", "market": "CN", "yf_symbol": "399001.SZ"},
            {"symbol": "399006.SZ", "name": "创业板指", "market": "CN", "yf_symbol": "399006.SZ"},
             # US Indices
            {"symbol": "^GSPC", "name": "标普500", "market": "US", "yf_symbol": "^GSPC"},
            {"symbol": "^DJI", "name": "道琼斯", "market": "US", "yf_symbol": "^DJI"},
            {"symbol": "^IXIC", "name": "纳斯达克", "market": "US", "yf_symbol": "^IXIC"},
        ]
        
        return self.get_prices_batch(indices)

