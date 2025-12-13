import akshare as ak
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union
from proxy_manager import ProxyManager
import warnings
import os
import contextlib

# Suppress pandas future warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

@contextlib.contextmanager
def no_proxy_context():
    """
    Temporarily remove proxy from environment variables.
    """
    proxies = {}
    keys = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]
    for k in keys:
        if k in os.environ:
            proxies[k] = os.environ.pop(k)
    try:
        yield
    finally:
        # Restore
        os.environ.update(proxies)

class StockDataProvider:
    def __init__(self, use_proxy: bool = False):
        self.proxy_manager = ProxyManager() if use_proxy else None
        self.executor = ThreadPoolExecutor(max_workers=10)

    def _get_proxy(self) -> Optional[Dict]:
        if self.proxy_manager:
            return self.proxy_manager.get_proxy()
        return None

    def get_price(self, symbol: str, market: str) -> Optional[Dict]:
        """
        Get current price and change for a single stock.
        """
        try:
            if market == "US":
                return self._get_us_stock_price(symbol)
            elif market == "CN":
                return self._get_cn_stock_price(symbol)
            else:
                print(f"Unknown market: {market}")
                return None
        except Exception as e:
            # print(f"Error fetching {symbol}: {e}") # Silent error for UI cleanliness, maybe log it
            return {
                 "symbol": symbol,
                 "market": market,
                 "error": str(e),
                 "price": 0,
                 "change": 0,
                 "change_percent": 0
            }

    def _get_us_stock_price(self, symbol: str) -> Dict:
        """
        Fetch US stock data using yfinance.
        """
        try:
            ticker = yf.Ticker(symbol)
            # yfinance info is sometimes slow or unreliable, use fast history if possible
            # But we need Name.
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
            
            if current_price is None:
                 hist = ticker.history(period="1d")
                 if not hist.empty:
                     current_price = hist['Close'].iloc[-1]
                     previous_close = hist['Open'].iloc[0]
            
            change = 0
            change_percent = 0
            if current_price is not None and previous_close:
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100

            return {
                "symbol": symbol,
                "market": "US",
                "name": info.get('shortName', symbol),
                "price": current_price if current_price else 0,
                "change": change,
                "change_percent": change_percent,
                "volume": info.get('volume', 0),
                "currency": info.get('currency', 'USD')
            }
        except Exception as e:
            raise e

    def _get_cn_stock_price(self, symbol: str) -> Dict:
        """
        Fetch CN stock data using akshare.
        Symbol should be like '600519'.
        """
        try:
            # optimized: stock_zh_a_spot_em() is slow (fetches all).
            # If we are doing batch, we should fetch once and cache? 
            # For now, let's assume we maintain a cached global dataframe if called frequently?
            # Or just fetch for now.
            # Ideally akshare has single stock spot. 'stock_individual_info_em' gives info but not real time price.
            # 'stock_zh_a_hist_df' gives daily history.
            # Let's try to get quote from a lighter API if possible.
            # Actually stock_zh_a_spot_em is the main real-time one. 
            # We will use it but we should be careful about rate limits if we call it per stock.
            # BETTER STRATEGY: 
            # If get_prices_batch is called, we fetch the whole table ONCE and filter.
            # If get_price is called single, we also fetch whole table? That's heavy (5000 rows).
            # SEARCH: check if there is a specific quote api.
            # Found: stock_bid_ask_em might work for snapshots
            
            with no_proxy_context():
                df = ak.stock_zh_a_spot_em()
            stock_info = df[df['代码'] == symbol]
            
            if stock_info.empty:
                return {
                     "symbol": symbol,
                     "market": "CN",
                     "error": "Stock not found"
                }
            
            row = stock_info.iloc[0]
            price = row['最新价']
            change_percent = row['涨跌幅']
            change = row['涨跌额']
            name = row['名称']
            volume = row['成交量']
            
            return {
                "symbol": symbol,
                "market": "CN",
                "name": name,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "volume": volume,
                "currency": "CNY"
            }
        except Exception as e:
            raise e

    def get_prices_batch(self, stocks: List[Dict[str, str]]) -> List[Dict]:
        """
        Fetch prices for multiple stocks.
        Optimization for CN: Fetch ALL A-shares once if there are many CN stocks requested.
        """
        cn_stocks = [s['symbol'] for s in stocks if s['market'] == 'CN']
        us_stocks = [s for s in stocks if s['market'] == 'US']
        
        results = []
        
        # Optimize CN fetching
        if cn_stocks:
            try:
                # Fetch all CN stocks once
                df_cn = ak.stock_zh_a_spot_em()
                for symbol in cn_stocks:
                    row = df_cn[df_cn['代码'] == symbol]
                    if not row.empty:
                        r = row.iloc[0]
                        results.append({
                            "symbol": symbol,
                            "market": "CN",
                            "name": r['名称'],
                            "price": r['最新价'],
                            "change": r['涨跌额'],
                            "change_percent": r['涨跌幅'],
                            "volume": r['成交量'],
                            "currency": "CNY"
                        })
                    else:
                        results.append({"symbol": symbol, "market": "CN", "error": "Not found"})
            except Exception as e:
                 # Fallback to individual or error
                 for symbol in cn_stocks:
                      results.append({"symbol": symbol, "market": "CN", "error": str(e)})

        # Multi-thread US fetching
        if us_stocks:
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_stock = {
                    executor.submit(self.get_price, stock['symbol'], stock['market']): stock 
                    for stock in us_stocks
                }
                for future in as_completed(future_to_stock):
                    stock = future_to_stock[future]
                    try:
                        data = future.result()
                        if data:
                            results.append(data)
                    except Exception as e:
                        results.append({
                            "symbol": stock['symbol'],
                            "market": stock['market'],
                            "error": str(e)
                        })
                        
        return results

    def get_history(self, symbol: str, market: str, period: str = "1mo") -> Optional[pd.DataFrame]:
        """
        Fetch historical data.
        """
        try:
            if market == "US":
                ticker = yf.Ticker(symbol)
                return ticker.history(period=period)
            elif market == "CN":
                import datetime
                end_date = datetime.datetime.now()
                # Map period to days roughly
                days_map = {'1mo': 30, '3mo': 90, '6mo': 180, '1y': 365, 'ytd': 365, 'max': 3650}
                days = days_map.get(period, 30)
                
                start_date = end_date - datetime.timedelta(days=days)
                start_str = start_date.strftime("%Y%m%d")
                end_str = end_date.strftime("%Y%m%d")
                
                # akshare stock_zh_a_hist
                with no_proxy_context():
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_str, end_date=end_str, adjust="qfq")
                if df.empty:
                    return None
                    
                df = df.rename(columns={
                    "日期": "Date",
                    "开盘": "Open",
                    "收盘": "Close",
                    "最高": "High",
                    "最低": "Low",
                    "成交量": "Volume"
                })
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index("Date", inplace=True)
                return df
        except Exception as e:
            print(f"Error fetching history: {e}")
            return None
        return None

    def get_stock_list(self, market: str) -> List[Dict]:
        """
        Fetch the full list of stocks for the given market.
        Returns a customized list of dicts.
        """
        try:
            if market == "CN":
                with no_proxy_context():
                    # stock_zh_a_spot_em returns a dataframe of all A-shares
                    df = ak.stock_zh_a_spot_em()
                # Rename columns matches for UI
                # Need: symbol, name, price, change, change_percent, volume
                # akshare columns: 序号, 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, ...
                
                needed = df[['代码', '名称', '最新价', '涨跌幅', '成交量']].copy()
                needed.columns = ['symbol', 'name', 'price', 'change_percent', 'volume']
                
                # Convert to records
                return needed.to_dict('records')
            
            elif market == "US":
                # stock_us_spot_em() -> might fail or differ by version
                try:
                    df = ak.stock_us_spot_em()
                except AttributeError:
                    return []
                
                # Check columns. usually: 名称, 最新价, 涨跌幅, 代码 ...
                rename_map = {
                    '名称': 'name', '最新价': 'price', '涨跌幅': 'change_percent', '代码': 'symbol', '成交量': 'volume'
                }
                
                # Filter available columns
                available = [c for c in rename_map.keys() if c in df.columns]
                needed = df[available].copy()
                needed.rename(columns=rename_map, inplace=True)
                
                # Fill missing
                for k in ['symbol', 'name', 'price', 'change_percent', 'volume']:
                    if k not in needed.columns:
                        needed[k] = 0 if k in ['price', 'change_percent', 'volume'] else "?"
                
                return needed.to_dict('records')

        except Exception as e:
            # print(f"Error fetching stock list: {e}") 
            return []
        return []
