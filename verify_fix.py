
import sys
import pandas as pd
# Ensure we can import from current directory
sys.path.append('.')
from stock_data import StockDataProvider

def verify_fix():
    print("--- Verifying Fix with StockDataProvider ---")
    provider = StockDataProvider()
    
    # Test stocks that were failing
    stocks = [
        {"symbol": "AMZN", "market": "US"},
        {"symbol": "TSLA", "market": "US"},
        {"symbol": "600519", "market": "CN"}
    ]
    
    print(f"Fetching batch: {stocks}")
    results = provider.get_prices_batch(stocks)
    
    for res in results:
        print(f"Symbol: {res['symbol']}")
        if "error" in res:
            print(f"  Error: {res['error']}")
        else:
            print(f"  Price: {res['price']}")
            print(f"  Change: {res['change']}")
            print(f"  Pct: {res['change_percent']}%")

if __name__ == "__main__":
    verify_fix()
